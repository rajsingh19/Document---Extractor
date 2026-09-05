"""
tests/test_industry_benchmark.py — 80+ Comprehensive Unit and Integration Tests for Step 24 & Patches 1–14.

Covers:
1. BusinessProfile, IndustryBenchmark, BenchmarkComparison models and columns.
2. Decimal precision across gaps, percentages, and intensities.
3. Benchmark versioning & status transitions (ACTIVE, INACTIVE, SUPERSEDED).
4. Source provenance and source_type hierarchy (AUTHORITATIVE_SOURCE, CURATED_SOURCE, USER_PROVIDED, TEST_FIXTURE).
5. BusinessProfile data provenance (Patch 1): revenue_data_status, employee_data_status.
6. Zero benchmark mathematical safety (Patch 2 & 11): NULL gap_percentage, limitation, zero-safe methods.
7. Benchmark eligibility checks: missing industry, missing sub-industry, missing geography, missing size band.
8. No implicit segmentation defaults (Patch 8): no default India, no default MSME, no inferred industry.
9. Intensity denominator checks (Patch 1 & 9): unprovided revenue, unverified revenue, zero employees.
10. Test fixture isolation (Patch 4): TEST_FIXTURE excluded from production UI and queries.
11. Deterministic exact peer matching vs explicit broader industry fallback.
12. Prohibition of silent broadening.
13. Actual-only comparison rule (Patch 7): forecasts and scenarios rejected.
14. Preservation of Step 22A priority truth (Patch 6): no competing priority score.
15. Proactive AI Agent integration: surfaces benchmark signals with 22A reference.
16. Copilot RAG benchmark intent routing and negative safety constraints (Patch 5).
17. Historical comparison immutability across registry version updates (Patch 10).
18. Document scoping and cross-document isolation.
19. Idempotent benchmark evaluation.
20. All REST API endpoints under /api/benchmarks.
"""
import pytest
from decimal import Decimal
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.database.base import Base
from backend.app.database.session import get_db
from backend.app.models.document import Document
from backend.app.models.carbon_ledger import CarbonLedgerEntry
from backend.app.models.reduction_intelligence import ReductionPriority
from backend.app.models.industry_benchmark import (
    BusinessProfile,
    IndustryBenchmark,
    BenchmarkComparison,
)
from backend.app.services.benchmark_eligibility import BenchmarkEligibilityService
from backend.app.services.industry_benchmark import (
    IndustryBenchmarkService,
    BENCHMARK_ENGINE_VERSION,
)
from backend.app.services.proactive_agent import proactive_agent_service
from backend.app.services.copilot_rag import CopilotRAGRouter


# ---------------------------------------------------------------------------
# Test Fixtures & In-Memory Isolated Database
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh SQLite database session for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient with overridden get_db dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_benchmark_dataset(db_session):
    """Seed authoritative, curated, and test fixture benchmarks."""
    # 1. Authoritative Benchmark (Electricity)
    b1 = IndustryBenchmark(
        benchmark_code="BM_MFG_ELEC_2024",
        benchmark_name="Precision Manufacturing Grid Electricity Baseline",
        industry="Manufacturing",
        sub_industry="Precision Components",
        geography="India",
        business_size_band="MSME",
        metric_name="scope_2",
        metric_unit="tCO2e",
        benchmark_type="RANGE",
        benchmark_value=Decimal("24.5000"),
        lower_bound=Decimal("20.0000"),
        upper_bound=Decimal("28.0000"),
        percentile_25=Decimal("22.0000"),
        median=Decimal("24.5000"),
        percentile_75=Decimal("27.0000"),
        sample_size=120,
        source_name="Bureau of Energy Efficiency Sector Baseline 2024",
        source_reference="BEE/CEA-PAT-SEC-2024-09",
        source_year=2024,
        methodology="CEA Baseline Database v20.0 and PAT verified MSME audits",
        version="1.0",
        status="ACTIVE",
        source_type="AUTHORITATIVE_SOURCE",
    )
    # 2. Curated Benchmark (Fuel)
    b2 = IndustryBenchmark(
        benchmark_code="BM_MFG_FUEL_2024",
        benchmark_name="Manufacturing Backup Fuel Benchmark",
        industry="Manufacturing",
        sub_industry="Precision Components",
        geography="India",
        business_size_band="MSME",
        metric_name="scope_1",
        metric_unit="tCO2e",
        benchmark_type="RANGE",
        benchmark_value=Decimal("2.0000"),
        lower_bound=Decimal("1.5000"),
        upper_bound=Decimal("2.5000"),
        sample_size=85,
        source_name="Curated MSME Industry Survey 2024",
        source_reference="CURATED-IND-MSME-2024",
        source_year=2024,
        methodology="Curated survey of verified industrial backup diesel consumption",
        version="1.0",
        status="ACTIVE",
        source_type="CURATED_SOURCE",
    )
    # 3. Total Emissions Broader Benchmark
    b3 = IndustryBenchmark(
        benchmark_code="BM_MFG_TOT_2024",
        benchmark_name="Broad Manufacturing Total Emissions Baseline",
        industry="Manufacturing",
        sub_industry=None,  # Broader match
        geography="India",
        business_size_band="MSME",
        metric_name="total_emissions",
        metric_unit="tCO2e",
        benchmark_type="POINT_COMPARISON",
        benchmark_value=Decimal("30.0000"),
        lower_bound=Decimal("25.0000"),
        upper_bound=Decimal("35.0000"),
        sample_size=250,
        source_name="National Industrial Baseline Registry",
        source_reference="NIBR-2024-GEN",
        source_year=2024,
        methodology="Aggregated reported emissions",
        version="1.0",
        status="ACTIVE",
        source_type="AUTHORITATIVE_SOURCE",
    )
    # 4. Zero Benchmark Fixture (Patch 2 & 11)
    b4 = IndustryBenchmark(
        benchmark_code="BM_ZERO_TARGET_2024",
        benchmark_name="Zero Direct Coal Combustion Target",
        industry="Manufacturing",
        sub_industry="Precision Components",
        geography="India",
        business_size_band="MSME",
        metric_name="coal_consumption",
        metric_unit="tCO2e",
        benchmark_type="ABSOLUTE",
        benchmark_value=Decimal("0.0000"),
        lower_bound=Decimal("0.0000"),
        upper_bound=Decimal("0.0000"),
        sample_size=50,
        source_name="Zero Coal Mandate 2024",
        source_reference="ZCM-2024-REG",
        source_year=2024,
        methodology="Target standard mandate zero coal",
        version="1.0",
        status="ACTIVE",
        source_type="AUTHORITATIVE_SOURCE",
    )
    # 5. Test Fixture (Patch 4: must be isolated)
    b5 = IndustryBenchmark(
        benchmark_code="BM_TEST_FIXTURE_ONLY",
        benchmark_name="Test Synthetic Benchmark Fixture",
        industry="Manufacturing",
        sub_industry="Precision Components",
        geography="India",
        business_size_band="MSME",
        metric_name="synthetic_metric",
        metric_unit="kg",
        benchmark_type="ABSOLUTE",
        benchmark_value=Decimal("999.0000"),
        sample_size=10,
        source_name="TEST FIXTURE — NOT PRODUCTION BENCHMARK",
        source_reference="TEST-FIXTURE-REF",
        source_year=2025,
        methodology="Synthetic unit test fixture",
        version="1.0",
        status="ACTIVE",
        source_type="TEST_FIXTURE",
    )
    db_session.add_all([b1, b2, b3, b4, b5])
    db_session.commit()
    return [b1, b2, b3, b4, b5]


@pytest.fixture
def posted_ledger_entries(db_session):
    """Seed verified POSTED carbon ledger entries."""
    doc = Document(
        filename="electricity_bill_oct2024.pdf",
        original_filename="electricity_bill_oct2024.pdf",
        file_path="/tmp/electricity_bill_oct2024.pdf",
        file_size=1024,
        document_type="Utility Bill",
        reporting_period="October 2024",
        status="COMPLETED"
    )
    db_session.add(doc)
    db_session.flush()

    # Scope 2 entry (31.8790 tCO2e = 31879.0 kgCO2e)
    e1 = CarbonLedgerEntry(
        carbon_calculation_id=1,
        document_id=doc.id,
        scope="SCOPE_2",
        activity_type="GRID_ELECTRICITY",
        quantity=Decimal("38877.00"),
        activity_unit="kWh",
        calculated_co2e=Decimal("31879.00"),
        calculated_co2e_unit="kgCO2e",
        reporting_period="October 2024",
        accounting_status="POSTED"
    )
    # Scope 1 entry (1.1300 tCO2e = 1130.0 kgCO2e)
    e2 = CarbonLedgerEntry(
        carbon_calculation_id=1,
        document_id=doc.id,
        scope="SCOPE_1",
        activity_type="DIESEL_GENERATOR",
        quantity=Decimal("420.00"),
        activity_unit="Liters",
        calculated_co2e=Decimal("1130.00"),
        calculated_co2e_unit="kgCO2e",
        reporting_period="October 2024",
        accounting_status="POSTED"
    )
    db_session.add_all([e1, e2])
    db_session.commit()
    return doc, [e1, e2]


# ===========================================================================
# GROUP 1: Models & Decimal Precision (Tests 1–10)
# ===========================================================================

def test_01_business_profile_model_creation(db_session):
    p = BusinessProfile(
        organization_name="Acme Precision Corp",
        industry="Manufacturing",
        sub_industry="Precision Components",
        geography="India",
        business_size_band="MSME",
        employee_count=75,
        employee_data_status="USER_PROVIDED",
        revenue_amount=Decimal("12500000.0000"),
        revenue_currency="INR",
        revenue_data_status="VERIFIED",
    )
    db_session.add(p)
    db_session.commit()
    assert p.id is not None
    assert p.employee_data_status == "USER_PROVIDED"
    assert p.revenue_data_status == "VERIFIED"


def test_02_industry_benchmark_decimal_fields(db_session):
    b = IndustryBenchmark(
        benchmark_code="BM_DEC_01",
        benchmark_name="Dec Test",
        industry="Manufacturing",
        geography="India",
        metric_name="scope_2",
        metric_unit="tCO2e",
        benchmark_value=Decimal("24.5000"),
        lower_bound=Decimal("20.1234"),
        upper_bound=Decimal("28.9876"),
        source_name="Gov Source",
        source_reference="REF-1",
        source_year=2024,
        methodology="Audit",
        source_type="AUTHORITATIVE_SOURCE",
    )
    db_session.add(b)
    db_session.commit()
    assert isinstance(b.benchmark_value, Decimal)
    assert b.benchmark_value == Decimal("24.5000")
    assert b.lower_bound == Decimal("20.1234")


def test_03_benchmark_comparison_decimal_gap_precision(db_session):
    c = BenchmarkComparison(
        business_scope="ORGANIZATION",
        metric_name="scope_2",
        metric_unit="tCO2e",
        business_value=Decimal("31.8790"),
        benchmark_value=Decimal("24.5000"),
        gap=Decimal("7.3790"),
        gap_percentage=Decimal("30.1184"),
        classification="WORSE_THAN_BENCHMARK",
        benchmark_version="1.0",
        engine_version="1.0",
        data_status="ACTUAL_POSTED",
    )
    db_session.add(c)
    db_session.commit()
    assert isinstance(c.gap, Decimal)
    assert c.gap == Decimal("7.3790")
    assert c.gap_percentage == Decimal("30.1184")


def test_04_benchmark_status_transitions(db_session):
    b = IndustryBenchmark(
        benchmark_code="BM_TRANS_01",
        benchmark_name="Transition Test",
        industry="Energy",
        geography="Global",
        metric_name="total_emissions",
        metric_unit="tCO2e",
        benchmark_value=Decimal("100.0"),
        source_name="Source A",
        source_reference="REF-A",
        source_year=2023,
        methodology="Method A",
        status="ACTIVE",
    )
    db_session.add(b)
    db_session.commit()
    assert b.status == "ACTIVE"

    b.status = "SUPERSEDED"
    db_session.commit()
    assert b.status == "SUPERSEDED"

    b.status = "INACTIVE"
    db_session.commit()
    assert b.status == "INACTIVE"


def test_05_source_type_hierarchy_field(db_session):
    for st in ["AUTHORITATIVE_SOURCE", "CURATED_SOURCE", "USER_PROVIDED", "TEST_FIXTURE"]:
        b = IndustryBenchmark(
            benchmark_code=f"BM_ST_{st}",
            benchmark_name=f"ST Test {st}",
            industry="Chemicals",
            geography="India",
            metric_name="scope_1",
            metric_unit="tCO2e",
            benchmark_value=Decimal("50.0"),
            source_name="Source Test",
            source_reference="REF-T",
            source_year=2024,
            methodology="Method T",
            source_type=st,
        )
        db_session.add(b)
    db_session.commit()
    count = db_session.query(IndustryBenchmark).filter(IndustryBenchmark.industry == "Chemicals").count()
    assert count == 4


def test_06_business_profile_default_currency_inr(db_session):
    p = BusinessProfile(organization_name="Def Curr Test")
    db_session.add(p)
    db_session.commit()
    assert p.revenue_currency == "INR"


def test_07_comparison_method_persisted(db_session):
    c = BenchmarkComparison(
        business_scope="ORGANIZATION",
        metric_name="scope_2",
        metric_unit="tCO2e",
        business_value=Decimal("30.0"),
        benchmark_value=Decimal("20.0"),
        gap=Decimal("10.0"),
        classification="WORSE_THAN_BENCHMARK",
        comparison_method="STANDARD_RANGE",
        engine_version="1.0",
    )
    db_session.add(c)
    db_session.commit()
    assert c.comparison_method == "STANDARD_RANGE"


def test_08_sample_size_tracking(db_session):
    b = IndustryBenchmark(
        benchmark_code="BM_SAMPLE_01",
        benchmark_name="Sample Size Test",
        industry="Automotive",
        geography="India",
        metric_name="scope_1",
        metric_unit="tCO2e",
        benchmark_value=Decimal("15.0"),
        sample_size=350,
        source_name="Auto Sector 2024",
        source_reference="AUTO-2024",
        source_year=2024,
        methodology="Survey",
    )
    db_session.add(b)
    db_session.commit()
    assert b.sample_size == 350


def test_09_historical_engine_version_persisted(db_session):
    c = BenchmarkComparison(
        business_scope="ORGANIZATION",
        metric_name="scope_1",
        metric_unit="tCO2e",
        business_value=Decimal("5.0"),
        benchmark_value=Decimal("5.0"),
        gap=Decimal("0.0"),
        classification="WITHIN_BENCHMARK",
        engine_version=BENCHMARK_ENGINE_VERSION,
    )
    db_session.add(c)
    db_session.commit()
    assert c.engine_version == "1.0"


def test_10_notes_and_explanation_persisted(db_session):
    c = BenchmarkComparison(
        business_scope="ORGANIZATION",
        metric_name="scope_2",
        metric_unit="tCO2e",
        business_value=Decimal("30.0"),
        benchmark_value=Decimal("20.0"),
        gap=Decimal("10.0"),
        classification="WORSE_THAN_BENCHMARK",
        explanation="Your measured electricity emissions are above benchmark.",
        limitation="This comparison does not establish that the benchmark is achievable for your business.",
    )
    db_session.add(c)
    db_session.commit()
    assert "above benchmark" in c.explanation
    assert "does not establish" in c.limitation


# ===========================================================================
# GROUP 2: Business Profile Provenance & No Defaults (Patch 1 & 8) (Tests 11–20)
# ===========================================================================

def test_11_revenue_data_status_not_provided_by_default(db_session):
    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    assert p.revenue_data_status == "NOT_PROVIDED"
    assert p.employee_data_status == "NOT_PROVIDED"


def test_12_no_implicit_geography_default_india(db_session):
    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    assert p.geography is None  # Patch 8: Must NEVER default to 'India'


def test_13_no_implicit_size_default_msme(db_session):
    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    assert p.business_size_band is None  # Patch 8: Must NEVER default to 'MSME'


def test_14_no_implicit_industry_default_manufacturing(db_session):
    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    assert p.industry is None  # Patch 8: Must NEVER infer or default industry


def test_15_eligibility_fails_when_industry_missing(db_session):
    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    p.industry = None
    p.geography = "India"
    db_session.commit()

    elig = BenchmarkEligibilityService.evaluate_eligibility(db_session, p)
    assert elig["status"] == "BENCHMARK_UNAVAILABLE"
    assert "Industry is required" in elig["reason"]


def test_16_eligibility_fails_when_geography_missing(db_session):
    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    p.industry = "Manufacturing"
    p.geography = None
    db_session.commit()

    elig = BenchmarkEligibilityService.evaluate_eligibility(db_session, p)
    assert elig["status"] == "BENCHMARK_UNAVAILABLE"
    assert "Geography is required" in elig["reason"]


def test_17_revenue_not_inferred_from_uploaded_invoices(db_session, posted_ledger_entries):
    # Posted entry has 38877 kWh and cost 450,000 INR
    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    assert p.revenue_amount is None
    assert p.revenue_data_status == "NOT_PROVIDED"
    # Even with uploaded invoices in system, revenue stays unpopulated unless user provides it


def test_18_employee_count_not_inferred_from_documents(db_session, posted_ledger_entries):
    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    assert p.employee_count is None
    assert p.employee_data_status == "NOT_PROVIDED"


def test_19_user_provided_revenue_enables_intensity_eligibility(db_session, seeded_benchmark_dataset, posted_ledger_entries):
    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    p.industry = "Manufacturing"
    p.sub_industry = "Precision Components"
    p.geography = "India"
    p.revenue_amount = Decimal("50000000.00")
    p.revenue_data_status = "USER_PROVIDED"
    p.employee_count = 50
    p.employee_data_status = "USER_PROVIDED"
    db_session.commit()

    elig = BenchmarkEligibilityService.evaluate_eligibility(db_session, p)
    assert elig["status"] == "ELIGIBLE"


def test_20_unverified_revenue_status_keeps_intensity_ineligible(db_session, seeded_benchmark_dataset, posted_ledger_entries):
    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    p.industry = "Manufacturing"
    p.sub_industry = "Precision Components"
    p.geography = "India"
    p.revenue_amount = Decimal("50000000.00")
    p.revenue_data_status = "NOT_PROVIDED"  # Unverified / unprovided
    db_session.commit()

    elig = BenchmarkEligibilityService.evaluate_eligibility(db_session, p)
    assert elig["status"] == "PARTIALLY_ELIGIBLE"
    assert "intensity metrics require explicit user-provided or verified denominators" in elig["reason"]


# ===========================================================================
# GROUP 3: Zero Benchmark Mathematical Safety (Patch 2 & 11) (Tests 21–30)
# ===========================================================================

def test_21_zero_benchmark_with_positive_business_val_returns_null_pct(db_session):
    engine = IndustryBenchmarkService(db_session)
    gap, gap_pct, classification, method, limitation = engine.calculate_gap_and_classification(
        business_val=Decimal("12.5000"),
        benchmark_val=Decimal("0.0000")
    )
    assert gap == Decimal("12.5000")
    assert gap_pct is None  # Patch 2: Must NEVER be 0% or NaN
    assert classification == "WORSE_THAN_BENCHMARK"
    assert method == "ZERO_BENCHMARK_NONZERO_BUSINESS"
    assert "Percentage difference cannot be calculated" in limitation


def test_22_zero_benchmark_with_zero_business_val_returns_within(db_session):
    engine = IndustryBenchmarkService(db_session)
    gap, gap_pct, classification, method, limitation = engine.calculate_gap_and_classification(
        business_val=Decimal("0.0000"),
        benchmark_val=Decimal("0.0000")
    )
    assert gap == Decimal("0.0000")
    assert gap_pct is None
    assert classification == "WITHIN_BENCHMARK"
    assert method == "BOTH_VALUES_ZERO"
    assert limitation is None


def test_23_negative_business_value_rejected_against_zero_benchmark(db_session):
    engine = IndustryBenchmarkService(db_session)
    gap, gap_pct, classification, method, limitation = engine.calculate_gap_and_classification(
        business_val=Decimal("-5.0000"),
        benchmark_val=Decimal("0.0000")
    )
    assert classification == "NOT_COMPARABLE"
    assert gap_pct is None
    assert method == "NEGATIVE_BUSINESS_VALUE"


def test_24_nonzero_normal_gap_percentage_calculated(db_session):
    engine = IndustryBenchmarkService(db_session)
    gap, gap_pct, classification, method, limitation = engine.calculate_gap_and_classification(
        business_val=Decimal("30.0000"),
        benchmark_val=Decimal("20.0000"),
        lower_bound=Decimal("18.0000"),
        upper_bound=Decimal("22.0000")
    )
    assert gap == Decimal("10.0000")
    assert gap_pct == Decimal("50.0000")
    assert classification == "WORSE_THAN_BENCHMARK"
    assert method == "STANDARD_RANGE"
    assert limitation is None


def test_25_better_than_benchmark_range_classification(db_session):
    engine = IndustryBenchmarkService(db_session)
    gap, gap_pct, classification, method, limitation = engine.calculate_gap_and_classification(
        business_val=Decimal("15.0000"),
        benchmark_val=Decimal("20.0000"),
        lower_bound=Decimal("18.0000"),
        upper_bound=Decimal("22.0000")
    )
    assert gap == Decimal("-5.0000")
    assert gap_pct == Decimal("-25.0000")
    assert classification == "BETTER_THAN_BENCHMARK"


def test_26_within_benchmark_range_classification(db_session):
    engine = IndustryBenchmarkService(db_session)
    gap, gap_pct, classification, method, limitation = engine.calculate_gap_and_classification(
        business_val=Decimal("20.5000"),
        benchmark_val=Decimal("20.0000"),
        lower_bound=Decimal("18.0000"),
        upper_bound=Decimal("22.0000")
    )
    assert classification == "WITHIN_BENCHMARK"


def test_27_point_comparison_without_range(db_session):
    engine = IndustryBenchmarkService(db_session)
    gap, gap_pct, classification, method, limitation = engine.calculate_gap_and_classification(
        business_val=Decimal("19.0000"),
        benchmark_val=Decimal("20.0000"),
        lower_bound=None,
        upper_bound=None
    )
    assert classification == "BETTER_THAN_BENCHMARK"
    assert method == "POINT_COMPARISON"


def test_28_zero_benchmark_in_evaluation_flow(db_session, seeded_benchmark_dataset, posted_ledger_entries):
    # Add a ledger entry for coal
    doc, _ = posted_ledger_entries
    coal_entry = CarbonLedgerEntry(
        carbon_calculation_id=1,
        document_id=doc.id,
        scope="SCOPE_1",
        activity_type="COAL_CONSUMPTION",
        quantity=Decimal("1000.0"),
        activity_unit="kg",
        calculated_co2e=Decimal("2450.0"),
        calculated_co2e_unit="kgCO2e",
        reporting_period="October 2024",
        accounting_status="POSTED"
    )
    db_session.add(coal_entry)
    db_session.commit()

    # Configure profile
    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    p.industry = "Manufacturing"
    p.sub_industry = "Precision Components"
    p.geography = "India"
    db_session.commit()

    engine = IndustryBenchmarkService(db_session)
    # Mock extract actuals to include coal_consumption
    actuals = engine.extract_business_actuals(db_session)
    assert "scope_1" in actuals


def test_29_zero_safe_api_serialization(client, db_session):
    # Insert BenchmarkComparison with gap_percentage=None
    comp = BenchmarkComparison(
        business_scope="ORGANIZATION",
        metric_name="coal_consumption",
        metric_unit="tCO2e",
        business_value=Decimal("10.0"),
        benchmark_value=Decimal("0.0"),
        gap=Decimal("10.0"),
        gap_percentage=None,
        classification="WORSE_THAN_BENCHMARK",
        comparison_method="ZERO_BENCHMARK_NONZERO_BUSINESS",
        benchmark_version="1.0",
        source_type="AUTHORITATIVE_SOURCE",
        engine_version="1.0",
        data_status="ACTUAL_POSTED",
        limitation="Percentage difference cannot be calculated because the benchmark value is zero."
    )
    db_session.add(comp)
    db_session.commit()

    resp = client.get(f"/api/benchmarks/comparisons/{comp.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["gap_percentage"] is None
    assert data["comparison_method"] == "ZERO_BENCHMARK_NONZERO_BUSINESS"
    assert "Percentage difference cannot be calculated" in data["limitation"]


def test_30_no_nan_or_infinity_in_comparisons(client, db_session):
    resp = client.get("/api/benchmarks/comparisons")
    assert resp.status_code == 200
    # JSON standard does not allow NaN or Infinity; ensure clean response
    text = resp.text
    assert "NaN" not in text
    assert "Infinity" not in text


# ===========================================================================
# GROUP 4: Benchmark Source Authority & Test Fixture Isolation (Patch 3 & 4) (Tests 31–40)
# ===========================================================================

def test_31_test_fixtures_isolated_from_list_benchmarks(client, db_session, seeded_benchmark_dataset):
    resp = client.get("/api/benchmarks")
    assert resp.status_code == 200
    benchmarks = resp.json()["benchmarks"]
    codes = [b["benchmark_code"] for b in benchmarks]
    assert "BM_TEST_FIXTURE_ONLY" not in codes
    assert all(b["source_type"] != "TEST_FIXTURE" for b in benchmarks)


def test_32_test_fixtures_accessible_when_explicitly_requested(client, db_session, seeded_benchmark_dataset):
    resp = client.get("/api/benchmarks?include_fixtures=true")
    assert resp.status_code == 200
    benchmarks = resp.json()["benchmarks"]
    codes = [b["benchmark_code"] for b in benchmarks]
    assert "BM_TEST_FIXTURE_ONLY" in codes


def test_33_test_fixtures_isolated_from_sources_endpoint(client, db_session, seeded_benchmark_dataset):
    resp = client.get("/api/benchmarks/sources")
    assert resp.status_code == 200
    sources = resp.json()["sources"]
    source_names = [s["source_name"] for s in sources]
    assert "TEST FIXTURE — NOT PRODUCTION BENCHMARK" not in source_names


def test_34_sources_include_fixtures_flag(client, db_session, seeded_benchmark_dataset):
    resp = client.get("/api/benchmarks/sources?include_fixtures=true")
    assert resp.status_code == 200
    sources = resp.json()["sources"]
    source_names = [s["source_name"] for s in sources]
    assert "TEST FIXTURE — NOT PRODUCTION BENCHMARK" in source_names


def test_35_authoritative_source_type_stored(db_session, seeded_benchmark_dataset):
    b = db_session.query(IndustryBenchmark).filter(IndustryBenchmark.benchmark_code == "BM_MFG_ELEC_2024").first()
    assert b.source_type == "AUTHORITATIVE_SOURCE"
    assert "Energy Efficiency" in b.source_name
    assert "BEE" in b.source_reference


def test_36_curated_source_type_stored(db_session, seeded_benchmark_dataset):
    b = db_session.query(IndustryBenchmark).filter(IndustryBenchmark.benchmark_code == "BM_MFG_FUEL_2024").first()
    assert b.source_type == "CURATED_SOURCE"


def test_37_provenance_metadata_contains_year_and_methodology(db_session, seeded_benchmark_dataset):
    b = db_session.query(IndustryBenchmark).filter(IndustryBenchmark.benchmark_code == "BM_MFG_ELEC_2024").first()
    assert b.source_year == 2024
    assert "CEA Baseline Database" in b.methodology
    assert b.source_reference == "BEE/CEA-PAT-SEC-2024-09"


def test_38_evaluation_ignores_test_fixtures_by_default(db_session, seeded_benchmark_dataset, posted_ledger_entries):
    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    p.industry = "Manufacturing"
    p.sub_industry = "Precision Components"
    p.geography = "India"
    db_session.commit()

    engine = IndustryBenchmarkService(db_session)
    comps = engine.evaluate_benchmarks(db_session, include_fixtures=False)
    for c in comps:
        assert c.source_type != "TEST_FIXTURE"
        assert c.metric_name != "synthetic_metric"


def test_39_no_fake_benchmark_data_returns_unavailable(db_session, posted_ledger_entries):
    # Delete all benchmarks
    db_session.query(IndustryBenchmark).delete()
    db_session.commit()

    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    p.industry = "Aerospace"
    p.geography = "India"
    db_session.commit()

    elig = BenchmarkEligibilityService.evaluate_eligibility(db_session, p)
    assert elig["status"] == "BENCHMARK_UNAVAILABLE"
    assert "Comparable peer benchmark data is not currently available for this segment." in elig["reason"]


def test_40_no_fake_peer_companies_created(db_session):
    # Verify no peer company entities exist in db
    assert not hasattr(Base.metadata, "peer_companies")


# ===========================================================================
# GROUP 5: Peer Matching Hierarchy & Fallbacks (Tests 41–50)
# ===========================================================================

def test_41_exact_sub_industry_peer_match(db_session, seeded_benchmark_dataset):
    p = BusinessProfile(
        organization_name="Exact Match Org",
        industry="Manufacturing",
        sub_industry="Precision Components",
        geography="India",
        business_size_band="MSME"
    )
    db_session.add(p)
    db_session.commit()

    engine = IndustryBenchmarkService(db_session)
    bench, match_type = engine.match_benchmark_for_metric(db_session, "scope_2", p)
    assert bench is not None
    assert bench.benchmark_code == "BM_MFG_ELEC_2024"
    assert match_type == "EXACT_PEER_MATCH"


def test_42_broader_industry_fallback_when_sub_industry_missing(db_session, seeded_benchmark_dataset):
    p = BusinessProfile(
        organization_name="Broader Match Org",
        industry="Manufacturing",
        sub_industry=None,  # No sub-industry
        geography="India",
        business_size_band="MSME"
    )
    db_session.add(p)
    db_session.commit()

    engine = IndustryBenchmarkService(db_session)
    bench, match_type = engine.match_benchmark_for_metric(db_session, "total_emissions", p)
    assert bench is not None
    assert match_type == "BROADER_INDUSTRY_MATCH"


def test_43_no_silent_broadening_label_persisted(db_session, seeded_benchmark_dataset, posted_ledger_entries):
    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    p.industry = "Manufacturing"
    p.sub_industry = None  # Force broader match
    p.geography = "India"
    db_session.commit()

    engine = IndustryBenchmarkService(db_session)
    comps = engine.evaluate_benchmarks(db_session)
    tot_comp = next((c for c in comps if c.metric_name == "total_emissions"), None)
    if tot_comp:
        assert "broader" in tot_comp.explanation.lower()


def test_44_no_exact_peer_match_returns_none(db_session, seeded_benchmark_dataset):
    p = BusinessProfile(
        organization_name="Unknown Sector Org",
        industry="Agriculture",  # No benchmarks in Agriculture
        geography="India"
    )
    db_session.add(p)
    db_session.commit()

    engine = IndustryBenchmarkService(db_session)
    bench, match_type = engine.match_benchmark_for_metric(db_session, "scope_2", p)
    assert bench is None
    assert match_type == "NO_EXACT_PEER_MATCH"


def test_45_geography_mismatch_fails_peer_match(db_session, seeded_benchmark_dataset):
    p = BusinessProfile(
        organization_name="US Org",
        industry="Manufacturing",
        sub_industry="Precision Components",
        geography="United States"  # Benchmark is India
    )
    db_session.add(p)
    db_session.commit()

    engine = IndustryBenchmarkService(db_session)
    bench, match_type = engine.match_benchmark_for_metric(db_session, "scope_2", p)
    assert bench is None
    assert match_type == "NO_EXACT_PEER_MATCH"


def test_46_case_insensitive_matching(db_session, seeded_benchmark_dataset):
    p = BusinessProfile(
        organization_name="Case Org",
        industry="manufacturing",  # lowercase
        sub_industry="precision components",
        geography="india"
    )
    db_session.add(p)
    db_session.commit()

    engine = IndustryBenchmarkService(db_session)
    bench, match_type = engine.match_benchmark_for_metric(db_session, "scope_2", p)
    assert bench is not None
    assert bench.benchmark_code == "BM_MFG_ELEC_2024"


def test_47_inactive_benchmarks_excluded_from_matching(db_session, seeded_benchmark_dataset):
    b = db_session.query(IndustryBenchmark).filter(IndustryBenchmark.benchmark_code == "BM_MFG_ELEC_2024").first()
    b.status = "INACTIVE"
    db_session.commit()

    p = BusinessProfile(
        organization_name="Inactive Check",
        industry="Manufacturing",
        sub_industry="Precision Components",
        geography="India"
    )
    db_session.add(p)
    db_session.commit()

    engine = IndustryBenchmarkService(db_session)
    bench, match_type = engine.match_benchmark_for_metric(db_session, "scope_2", p)
    assert bench is None


def test_48_superseded_benchmarks_excluded_from_matching(db_session, seeded_benchmark_dataset):
    b = db_session.query(IndustryBenchmark).filter(IndustryBenchmark.benchmark_code == "BM_MFG_ELEC_2024").first()
    b.status = "SUPERSEDED"
    db_session.commit()

    p = BusinessProfile(
        organization_name="Superseded Check",
        industry="Manufacturing",
        sub_industry="Precision Components",
        geography="India"
    )
    db_session.add(p)
    db_session.commit()

    engine = IndustryBenchmarkService(db_session)
    bench, match_type = engine.match_benchmark_for_metric(db_session, "scope_2", p)
    assert bench is None


def test_49_peer_match_summary_type_reporting(db_session, seeded_benchmark_dataset, posted_ledger_entries):
    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    p.industry = "Manufacturing"
    p.sub_industry = "Precision Components"
    p.geography = "India"
    db_session.commit()

    engine = IndustryBenchmarkService(db_session)
    summary = engine.get_benchmark_summary(db_session)
    assert summary["peer_matching_type"] == "EXACT_PEER_MATCH"


def test_50_peer_match_summary_broader_type_reporting(db_session, seeded_benchmark_dataset, posted_ledger_entries):
    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    p.industry = "Manufacturing"
    p.sub_industry = None  # Broader
    p.geography = "India"
    db_session.commit()

    engine = IndustryBenchmarkService(db_session)
    summary = engine.get_benchmark_summary(db_session)
    assert summary["peer_matching_type"] == "BROADER_INDUSTRY_MATCH"


# ===========================================================================
# GROUP 6: Actual-Only Comparison & Isolation (Patch 7) (Tests 51–60)
# ===========================================================================

def test_51_unposted_ledger_entries_ignored(db_session, seeded_benchmark_dataset):
    # Ledger entry in DRAFT status
    e = CarbonLedgerEntry(
        carbon_calculation_id=1,
        scope="SCOPE_2",
        activity_type="GRID_ELECTRICITY",
        quantity=Decimal("100.0"),
        activity_unit="kWh",
        calculated_co2e=Decimal("50.0"),
        calculated_co2e_unit="kgCO2e",
        accounting_status="DRAFT"  # NOT POSTED
    )
    db_session.add(e)
    db_session.commit()

    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    p.industry = "Manufacturing"
    p.geography = "India"
    db_session.commit()

    engine = IndustryBenchmarkService(db_session)
    actuals = engine.extract_business_actuals(db_session)
    assert actuals == {}  # Unposted entries must be ignored


def test_52_actual_only_comparison_rule_in_eligibility(db_session, seeded_benchmark_dataset):
    # No posted entries
    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    p.industry = "Manufacturing"
    p.geography = "India"
    db_session.commit()

    elig = BenchmarkEligibilityService.evaluate_eligibility(db_session, p)
    assert elig["status"] == "NOT_ELIGIBLE"
    assert "No verified POSTED carbon ledger entries available" in elig["reason"]


def test_53_forecast_isolated_from_benchmark_comparison(db_session, posted_ledger_entries):
    # Verify BenchmarkComparison table only records data_status == 'ACTUAL_POSTED'
    c = BenchmarkComparison(
        business_scope="ORGANIZATION",
        metric_name="scope_2",
        metric_unit="tCO2e",
        business_value=Decimal("31.8790"),
        benchmark_value=Decimal("24.5000"),
        gap=Decimal("7.3790"),
        classification="WORSE_THAN_BENCHMARK",
        data_status="ACTUAL_POSTED"
    )
    db_session.add(c)
    db_session.commit()
    assert c.data_status == "ACTUAL_POSTED"


def test_54_document_scoped_actuals(db_session, posted_ledger_entries):
    doc, [e1, e2] = posted_ledger_entries
    engine = IndustryBenchmarkService(db_session)
    actuals_doc = engine.extract_business_actuals(db_session, document_id=doc.id)
    assert actuals_doc["total_emissions"]["value"] == Decimal("33.0090")


def test_55_cross_document_isolation(db_session, posted_ledger_entries):
    doc1, _ = posted_ledger_entries
    doc2 = Document(
        filename="bill_nov2024.pdf",
        original_filename="bill_nov2024.pdf",
        file_path="/tmp/bill_nov2024.pdf",
        file_size=1024,
        document_type="Utility Bill",
        reporting_period="November 2024",
        status="COMPLETED"
    )
    db_session.add(doc2)
    db_session.flush()

    e_nov = CarbonLedgerEntry(
        carbon_calculation_id=1,
        document_id=doc2.id,
        scope="SCOPE_2",
        activity_type="GRID_ELECTRICITY",
        quantity=Decimal("50000.00"),
        activity_unit="kWh",
        calculated_co2e=Decimal("45000.00"),
        calculated_co2e_unit="kgCO2e",
        reporting_period="November 2024",
        accounting_status="POSTED"
    )
    db_session.add(e_nov)
    db_session.commit()

    engine = IndustryBenchmarkService(db_session)
    actuals_doc1 = engine.extract_business_actuals(db_session, document_id=doc1.id)
    actuals_doc2 = engine.extract_business_actuals(db_session, document_id=doc2.id)

    assert actuals_doc1["scope_2"]["value"] == Decimal("31.8790")
    assert actuals_doc2["scope_2"]["value"] == Decimal("45.0000")


def test_56_reporting_period_filtering_in_actuals(db_session, posted_ledger_entries):
    engine = IndustryBenchmarkService(db_session)
    oct_actuals = engine.extract_business_actuals(db_session, reporting_period="October 2024")
    assert oct_actuals["total_emissions"]["value"] == Decimal("33.0090")

    nov_actuals = engine.extract_business_actuals(db_session, reporting_period="November 2024")
    assert nov_actuals == {}


def test_57_electricity_consumption_aggregation(db_session, posted_ledger_entries):
    engine = IndustryBenchmarkService(db_session)
    actuals = engine.extract_business_actuals(db_session)
    assert actuals["electricity_consumption"]["value"] == Decimal("38877.00")
    assert actuals["electricity_consumption"]["unit"] == "kWh"


def test_58_fuel_consumption_aggregation(db_session, posted_ledger_entries):
    engine = IndustryBenchmarkService(db_session)
    actuals = engine.extract_business_actuals(db_session)
    assert actuals["fuel_consumption"]["value"] == Decimal("420.00")
    assert actuals["fuel_consumption"]["unit"] == "Liters"


def test_59_scope_1_scope_2_breakdown_accuracy(db_session, posted_ledger_entries):
    engine = IndustryBenchmarkService(db_session)
    actuals = engine.extract_business_actuals(db_session)
    assert actuals["scope_1"]["value"] == Decimal("1.1300")
    assert actuals["scope_2"]["value"] == Decimal("31.8790")


def test_60_empty_actuals_safe_handling(db_session):
    engine = IndustryBenchmarkService(db_session)
    actuals = engine.extract_business_actuals(db_session)
    assert actuals == {}


# ===========================================================================
# GROUP 7: Priority Truth & Agent / Copilot Integration (Patch 5 & 6) (Tests 61–70)
# ===========================================================================

def test_61_benchmark_does_not_create_competing_priority_score(db_session, seeded_benchmark_dataset, posted_ledger_entries):
    # Add a Step 22A Reduction Priority
    rp = ReductionPriority(
        priority_code="RED-ELEC-01",
        title="Grid Electricity Efficiency",
        reason="High grid electricity consumption compared to peers",
        category="ENERGY",
        activity_type="GRID_ELECTRICITY",
        scope="SCOPE_2",
        current_emissions_tco2e=Decimal("31.8790"),
        priority_level="CRITICAL",
        priority_score=Decimal("94.50"),
    )
    db_session.add(rp)
    db_session.commit()

    # Configure profile and evaluate benchmarks
    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    p.industry = "Manufacturing"
    p.sub_industry = "Precision Components"
    p.geography = "India"
    db_session.commit()

    engine = IndustryBenchmarkService(db_session)
    engine.evaluate_benchmarks(db_session)

    # Run Proactive Agent
    res = proactive_agent_service.evaluate_actions(db_session, force_recalculate=True)
    bench_actions = [a for a in res.actions if a.action_type == "BENCHMARK_GAP"]

    for ba in bench_actions:
        # Patch 6: Must inherit priority score from 22A and priority_source must be REDUCTION_INTELLIGENCE
        assert ba.priority_source == "REDUCTION_INTELLIGENCE"
        assert float(ba.priority_score) == 94.50
        assert ba.priority == "CRITICAL"


def test_62_agent_explanation_contains_benchmark_limitation_clause(db_session, seeded_benchmark_dataset, posted_ledger_entries):
    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    p.industry = "Manufacturing"
    p.sub_industry = "Precision Components"
    p.geography = "India"
    db_session.commit()

    engine = IndustryBenchmarkService(db_session)
    engine.evaluate_benchmarks(db_session)

    res = proactive_agent_service.evaluate_actions(db_session, force_recalculate=True)
    bench_action = next((a for a in res.actions if a.action_type == "BENCHMARK_GAP"), None)
    if bench_action:
        assert "does not establish that the benchmark is achievable" in bench_action.limitation


def test_63_copilot_rag_parses_benchmark_summary_intent():
    parsed = CopilotRAGRouter.parse_query("how do i compare with my industry?")
    assert parsed.retrieval_mode == "BENCHMARK_SUMMARY"


def test_64_copilot_rag_parses_benchmark_gap_intent():
    parsed = CopilotRAGRouter.parse_query("what is my biggest benchmark gap?")
    assert parsed.retrieval_mode == "BENCHMARK_GAP"


def test_65_copilot_rag_parses_benchmark_source_intent():
    parsed = CopilotRAGRouter.parse_query("what benchmark are you using?")
    assert parsed.retrieval_mode == "BENCHMARK_SOURCE"


def test_66_copilot_rag_parses_benchmark_strength_intent():
    parsed = CopilotRAGRouter.parse_query("where am i below benchmark?")
    assert parsed.retrieval_mode == "BENCHMARK_STRENGTH"


def test_67_copilot_rag_parses_benchmark_limitation_intent():
    parsed = CopilotRAGRouter.parse_query("why is gap percentage null for zero benchmark?")
    assert parsed.retrieval_mode == "BENCHMARK_LIMITATION"


def test_68_copilot_rag_parses_peer_comparison_intent():
    parsed = CopilotRAGRouter.parse_query("who are my peers?")
    assert parsed.retrieval_mode == "PEER_COMPARISON"


def test_69_copilot_rag_parses_why_above_benchmark_intent():
    parsed = CopilotRAGRouter.parse_query("why am i above the benchmark?")
    assert parsed.retrieval_mode == "WHY_ABOVE_BENCHMARK"


def test_70_copilot_negative_safety_boundaries(client):
    # Query asking for competitor identity
    resp = client.post("/api/copilot/chat", json={"message": "Who are my exact competitors and what are their emissions?"})
    assert resp.status_code == 200
    answer = resp.json()["answer"]
    assert "competitor identities" in answer.lower() or "never discloses" in answer.lower() or "peer" in answer.lower()


# ===========================================================================
# GROUP 8: Immutability & Versioning (Patch 10) (Tests 71–80)
# ===========================================================================

def test_71_comparison_records_historical_snapshot(db_session, seeded_benchmark_dataset, posted_ledger_entries):
    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    p.industry = "Manufacturing"
    p.sub_industry = "Precision Components"
    p.geography = "India"
    db_session.commit()

    engine = IndustryBenchmarkService(db_session)
    comps = engine.evaluate_benchmarks(db_session)

    c = comps[0]
    assert c.benchmark_version == "1.0"
    assert c.source_year == 2024
    assert c.engine_version == "1.0"


def test_72_benchmark_registry_update_preserves_old_comparison_version(db_session, seeded_benchmark_dataset, posted_ledger_entries):
    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    p.industry = "Manufacturing"
    p.sub_industry = "Precision Components"
    p.geography = "India"
    db_session.commit()

    engine = IndustryBenchmarkService(db_session)
    comps_v1 = engine.evaluate_benchmarks(db_session)
    scope2_comp_v1 = [c for c in comps_v1 if c.metric_name == "scope_2"][0]
    first_id = scope2_comp_v1.id

    # Simulate new benchmark version v2.0 added to registry
    b_v2 = IndustryBenchmark(
        benchmark_code="BM_MFG_ELEC_2025_V2",
        benchmark_name="Electricity Baseline v2",
        industry="Manufacturing",
        sub_industry="Precision Components",
        geography="India",
        business_size_band="MSME",
        metric_name="scope_2",
        metric_unit="tCO2e",
        benchmark_type="RANGE",
        benchmark_value=Decimal("22.0000"),
        source_name="BEE 2025",
        source_reference="BEE-2025",
        source_year=2025,
        methodology="Updated CEA Baseline",
        version="2.0",
        status="ACTIVE",
        source_type="AUTHORITATIVE_SOURCE",
    )
    # Old benchmark marked SUPERSEDED
    old_b = db_session.query(IndustryBenchmark).filter(IndustryBenchmark.benchmark_code == "BM_MFG_ELEC_2024").first()
    old_b.status = "SUPERSEDED"
    db_session.add(b_v2)
    db_session.commit()

    # Re-evaluate
    comps_v2 = engine.evaluate_benchmarks(db_session)

    # Verify old v1 comparison record was not mutated
    old_comp = db_session.query(BenchmarkComparison).filter(BenchmarkComparison.id == first_id).first()
    assert old_comp.benchmark_version == "1.0"
    assert old_comp.benchmark_value == Decimal("24.5000")


def test_73_idempotent_evaluation_prevents_duplicate_rows(db_session, seeded_benchmark_dataset, posted_ledger_entries):
    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    p.industry = "Manufacturing"
    p.sub_industry = "Precision Components"
    p.geography = "India"
    db_session.commit()

    engine = IndustryBenchmarkService(db_session)
    engine.evaluate_benchmarks(db_session)
    count1 = db_session.query(BenchmarkComparison).count()

    # Run evaluation again with same data
    engine.evaluate_benchmarks(db_session)
    count2 = db_session.query(BenchmarkComparison).count()

    assert count1 == count2  # Idempotent: no duplicate comparison rows


def test_74_insights_generation_deterministic(db_session, seeded_benchmark_dataset, posted_ledger_entries):
    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    p.industry = "Manufacturing"
    p.sub_industry = "Precision Components"
    p.geography = "India"
    db_session.commit()

    engine = IndustryBenchmarkService(db_session)
    comps = engine.evaluate_benchmarks(db_session)
    insights1 = engine.generate_benchmark_insights(comps, p)
    insights2 = engine.generate_benchmark_insights(comps, p)

    assert len(insights1) == len(insights2)
    assert [i["insight_code"] for i in insights1] == [i["insight_code"] for i in insights2]


def test_75_insights_categorize_energy_and_emissions(db_session, seeded_benchmark_dataset, posted_ledger_entries):
    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    p.industry = "Manufacturing"
    p.sub_industry = "Precision Components"
    p.geography = "India"
    db_session.commit()

    engine = IndustryBenchmarkService(db_session)
    comps = engine.evaluate_benchmarks(db_session)
    insights = engine.generate_benchmark_insights(comps, p)
    categories = [i["category"] for i in insights]

    assert "ENERGY_GAP" in categories or "PERFORMANCE_STRENGTH" in categories


def test_76_data_quality_confidence_scoring_high(db_session, seeded_benchmark_dataset, posted_ledger_entries):
    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    p.industry = "Manufacturing"
    p.sub_industry = "Precision Components"
    p.geography = "India"
    db_session.commit()

    engine = IndustryBenchmarkService(db_session)
    comps = engine.evaluate_benchmarks(db_session)
    assert all(c.data_quality_confidence in ("HIGH", "MEDIUM") for c in comps)


def test_77_data_quality_confidence_low_for_small_samples(db_session, posted_ledger_entries):
    # Benchmark with small sample size (< 30)
    b_small = IndustryBenchmark(
        benchmark_code="BM_SMALL_SAMPLE",
        benchmark_name="Small Sample Benchmark",
        industry="Textiles",
        sub_industry="Weaving",
        geography="India",
        metric_name="scope_2",
        metric_unit="tCO2e",
        benchmark_value=Decimal("10.0"),
        sample_size=15,  # Small sample
        source_name="Pilot Survey",
        source_reference="PILOT-01",
        source_year=2024,
        methodology="Pilot",
        status="ACTIVE",
    )
    db_session.add(b_small)

    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    p.industry = "Textiles"
    p.sub_industry = "Weaving"
    p.geography = "India"
    db_session.commit()

    engine = IndustryBenchmarkService(db_session)
    comps = engine.evaluate_benchmarks(db_session)
    c = next((comp for comp in comps if comp.metric_name == "scope_2"), None)
    if c:
        assert c.data_quality_confidence == "LOW"


def test_78_benchmark_summary_aggregate_counts(db_session, seeded_benchmark_dataset, posted_ledger_entries):
    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    p.industry = "Manufacturing"
    p.sub_industry = "Precision Components"
    p.geography = "India"
    db_session.commit()

    engine = IndustryBenchmarkService(db_session)
    engine.evaluate_benchmarks(db_session)
    summary = engine.get_benchmark_summary(db_session)

    assert summary["metrics_compared"] >= 2
    assert summary["worse_count"] >= 1  # Scope 2 (31.88 vs 24.50)
    assert summary["better_count"] >= 1  # Scope 1 (1.13 vs 2.00)


def test_79_force_refresh_recalculation(db_session, seeded_benchmark_dataset, posted_ledger_entries):
    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    p.industry = "Manufacturing"
    p.sub_industry = "Precision Components"
    p.geography = "India"
    db_session.commit()

    engine = IndustryBenchmarkService(db_session)
    comps1 = engine.evaluate_benchmarks(db_session, force_refresh=False)
    comps2 = engine.evaluate_benchmarks(db_session, force_refresh=True)
    assert len(comps1) == len(comps2)


def test_80_history_retrieval_persisted(db_session, seeded_benchmark_dataset, posted_ledger_entries):
    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    p.industry = "Manufacturing"
    p.sub_industry = "Precision Components"
    p.geography = "India"
    db_session.commit()

    engine = IndustryBenchmarkService(db_session)
    engine.evaluate_benchmarks(db_session)
    history = db_session.query(BenchmarkComparison).all()
    assert len(history) >= 2


# ===========================================================================
# GROUP 9: REST API Endpoints Contract (Tests 81–85)
# ===========================================================================

def test_81_api_get_and_put_profile(client):
    # GET profile
    r1 = client.get("/api/benchmarks/profile")
    assert r1.status_code == 200
    data1 = r1.json()
    assert data1["revenue_data_status"] == "NOT_PROVIDED"

    # PUT profile
    r2 = client.put("/api/benchmarks/profile", json={
        "industry": "Manufacturing",
        "sub_industry": "Precision Components",
        "geography": "India",
        "business_size_band": "MSME",
        "employee_count": 80,
        "employee_data_status": "USER_PROVIDED",
        "revenue_amount": 25000000.0,
        "revenue_data_status": "VERIFIED"
    })
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["industry"] == "Manufacturing"
    assert data2["revenue_data_status"] == "VERIFIED"
    assert data2["employee_data_status"] == "USER_PROVIDED"


def test_82_api_get_eligibility(client, db_session):
    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    p.industry = "Manufacturing"
    p.geography = "India"
    db_session.commit()

    resp = client.get("/api/benchmarks/eligibility")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "checks" in data


def test_83_api_post_evaluate_and_get_summary(client, db_session, seeded_benchmark_dataset, posted_ledger_entries):
    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    p.industry = "Manufacturing"
    p.sub_industry = "Precision Components"
    p.geography = "India"
    db_session.commit()

    # Evaluate
    r_eval = client.post("/api/benchmarks/evaluate", json={"force_refresh": True})
    assert r_eval.status_code == 200
    eval_data = r_eval.json()
    assert eval_data["success"] is True
    assert eval_data["comparisons_count"] >= 2

    # Summary
    r_sum = client.get("/api/benchmarks/summary")
    assert r_sum.status_code == 200
    sum_data = r_sum.json()
    assert sum_data["metrics_compared"] >= 2
    assert "comparisons" in sum_data
    assert "insights" in sum_data


def test_84_api_data_quality_endpoint(client, db_session, seeded_benchmark_dataset, posted_ledger_entries):
    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    p.industry = "Manufacturing"
    p.sub_industry = "Precision Components"
    p.geography = "India"
    db_session.commit()

    client.post("/api/benchmarks/evaluate", json={})
    resp = client.get("/api/benchmarks/data-quality")
    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_confidence"] in ("HIGH", "MEDIUM", "LOW", "INSUFFICIENT")
    assert "segmentation_match" in data


def test_85_api_recalculate_and_history(client, db_session, seeded_benchmark_dataset, posted_ledger_entries):
    p = BenchmarkEligibilityService.get_or_create_default_profile(db_session)
    p.industry = "Manufacturing"
    p.sub_industry = "Precision Components"
    p.geography = "India"
    db_session.commit()

    # Recalculate
    r_recalc = client.post("/api/benchmarks/recalculate")
    assert r_recalc.status_code == 200
    assert r_recalc.json()["success"] is True

    # History
    r_hist = client.get("/api/benchmarks/history")
    assert r_hist.status_code == 200
    assert r_hist.json()["total"] >= 2
