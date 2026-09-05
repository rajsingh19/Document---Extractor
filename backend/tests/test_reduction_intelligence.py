"""
tests/test_reduction_intelligence.py — Comprehensive Test Suite for Reduction Opportunity Intelligence Engine (Step 22A).

Covers:
1. ReductionPriority database model & Decimal precision
2. Scoring weights & threshold configuration
3. Impact calculation (>=50%, 25-50%, 10-25%, <10%, 0 denominator)
4. Trend scoring (>=25%, 10-25%, <10%, stable, decreasing, repeated periods)
5. Persistence scoring (1 period, 2 periods, 3+ periods, missing periods)
6. Forecast signal integration & insufficient data safeguards
7. Data quality blockers & unresolved emission factors
8. Actionability scoring (concrete action vs DATA_GAP vs ANALYSIS_REQUIRED)
9. Existing project status (PLANNED, IN_PROGRESS, COMPLETED)
10. Priority level mapping & score normalization (0-100)
11. Deduplication & stable identity
12. Document scoping & cross-document isolation
13. Summary KPIs & counters
14. Recalculation idempotency
15. Source data immutability (CarbonLedgerEntry, CarbonCalculation, etc.)
16. API endpoints (list, detail, summary, doc-scoped, recalculate)
17. Copilot grounding, intent routing, and safety refusal boundaries
"""
import pytest
from datetime import datetime
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend.app.database.base import Base
from backend.app.database.session import get_db
from backend.app.models.document import Document
from backend.app.models.carbon_calculation import CarbonCalculation
from backend.app.models.carbon_ledger import CarbonLedgerEntry
from backend.app.models.reduction_opportunity import ReductionOpportunity
from backend.app.models.reduction_project import ReductionProject
from backend.app.models.sustainability_metric import SustainabilityMetric
from backend.app.models.emission_forecast import EmissionForecast
from backend.app.models.reduction_intelligence import ReductionPriority
from backend.app.config.reduction_intelligence import (
    REDUCTION_INTELLIGENCE_VERSION,
    IMPACT_WEIGHT,
    TREND_WEIGHT,
    FORECAST_WEIGHT,
    PERSISTENCE_WEIGHT,
    ACTIONABILITY_WEIGHT,
    DATA_QUALITY_WEIGHT,
    BLOCKER_WEIGHT,
    TOTAL_MAX_WEIGHT,
    IMPACT_SCORE_VERY_HIGH,
    IMPACT_SCORE_HIGH,
    IMPACT_SCORE_MEDIUM,
    IMPACT_SCORE_LOW,
    IMPACT_SCORE_ZERO,
    TREND_SCORE_STRONG,
    TREND_SCORE_MODERATE,
    TREND_SCORE_WEAK,
    TREND_SCORE_STABLE_OR_DECREASING,
    PERSISTENCE_SCORE_STRONG,
    PERSISTENCE_SCORE_MODERATE,
    PERSISTENCE_SCORE_LOW,
    ACTIONABILITY_SCORE_CONCRETE,
    ACTIONABILITY_SCORE_ANALYSIS,
    ACTIONABILITY_SCORE_DATA_GAP,
    DATA_QUALITY_SCORE_UNRESOLVED_FACTOR,
    BLOCKER_SCORE_CRITICAL,
    PRIORITY_LEVEL_CRITICAL,
    PRIORITY_LEVEL_HIGH,
    PRIORITY_LEVEL_MEDIUM,
    PRIORITY_LEVEL_LOW,
    PRIORITY_LEVEL_INFORMATIONAL,
)
from backend.app.services.reduction_intelligence import reduction_intelligence_service
from backend.app.services.copilot_context import classify_intent
from backend.app.services.copilot_service import copilot_service


# ==============================================================================
# FIXTURES
# ==============================================================================
@pytest.fixture(scope="function")
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db(db_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_sample_document(db, doc_id=1, filename="test_doc.pdf"):
    doc = Document(
        id=doc_id,
        filename=filename,
        original_filename=filename,
        file_path=f"/tmp/{filename}",
        file_size=1024,
        mime_type="application/pdf",
        status="COMPLETED",
        review_status="VERIFIED"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def create_sample_calculation(db, calc_id=1, doc_id=1, scope="SCOPE_2", co2e_kg=31879.0):
    calc = CarbonCalculation(
        id=calc_id,
        activity_data_id=calc_id,
        document_id=doc_id,
        activity_type="grid_electricity",
        scope=scope,
        quantity=Decimal("38876.8"),
        activity_unit="kWh",
        calculated_co2e=Decimal(str(co2e_kg)),
        calculated_co2e_unit="kgCO2e",
        status="CALCULATED",
        calculation_version="1.0"
    )
    db.add(calc)
    db.commit()
    db.refresh(calc)
    return calc



def create_sample_ledger_entry(
    db,
    calc_id=1,
    doc_id=1,
    activity="grid_electricity",
    category="ENERGY",
    scope="SCOPE_2",
    period="2024-10",
    co2e_kg=31879.0,
    status="POSTED",
    factor_id=1,
    factor_value=0.82
):
    entry = CarbonLedgerEntry(
        carbon_calculation_id=calc_id,
        document_id=doc_id,
        activity_type=activity,
        category=category,
        scope=scope,
        quantity=Decimal("38876.8"),
        activity_unit="kWh",
        calculated_co2e=Decimal(str(co2e_kg)),
        calculated_co2e_unit="kgCO2e",
        emission_factor_id=factor_id,
        factor_value=Decimal(str(factor_value)) if factor_value else None,
        reporting_period=period,
        reporting_year=int(period[:4]) if len(period) >= 4 and period[:4].isdigit() else 2024,
        accounting_status=status,
        ledger_version="1.0"
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


# ==============================================================================
# 1. MODEL PERSISTENCE & SCHEMA TESTS
# ==============================================================================
class TestReductionPriorityModel:

    def test_01_create_priority_record(self, db):
        doc = create_sample_document(db, 1)
        p = ReductionPriority(
            priority_code="PRIORITY_SCOPE_2_ENERGY_GRID_DOC_1",
            document_id=doc.id,
            scope="SCOPE_2",
            category="ENERGY",
            activity_type="grid_electricity",
            priority_rank=1,
            priority_score=Decimal("92.50"),
            priority_level="CRITICAL",
            impact_score=Decimal("30.00"),
            trend_score=Decimal("20.00"),
            forecast_score=Decimal("15.00"),
            persistence_score=Decimal("15.00"),
            actionability_score=Decimal("10.00"),
            data_quality_score=Decimal("0.00"),
            blocker_score=Decimal("2.50"),
            title="Investigate Grid Electricity Demand",
            reason="Grid electricity accounts for 96.6% of posted emissions.",
            current_emissions_kgco2e=Decimal("31879.000000"),
            current_emissions_tco2e=Decimal("31.879000"),
            previous_emissions_kgco2e=Decimal("28000.000000"),
            change_percent=Decimal("13.85"),
            forecast_emissions_kgco2e=Decimal("34000.000000"),
            source_reference="Ledger Entry #1",
            calculation_version="1.0"
        )
        db.add(p)
        db.commit()
        db.refresh(p)

        assert p.id is not None
        assert p.priority_code == "PRIORITY_SCOPE_2_ENERGY_GRID_DOC_1"
        assert p.priority_score == Decimal("92.50")
        assert p.current_emissions_tco2e == Decimal("31.879000")

    def test_02_decimal_precision_retained(self, db):
        p = ReductionPriority(
            priority_code="PRIORITY_TEST_DECIMAL",
            title="Test Precision",
            reason="Verify exact decimal handling",
            priority_score=Decimal("88.75"),
            priority_level="CRITICAL",
            current_emissions_kgco2e=Decimal("1125.600000"),
            current_emissions_tco2e=Decimal("1.125600"),
            change_percent=Decimal("24.9999"),
        )
        db.add(p)
        db.commit()
        db.refresh(p)

        assert p.current_emissions_kgco2e == Decimal("1125.600000")
        assert p.current_emissions_tco2e == Decimal("1.125600")
        assert isinstance(p.priority_score, Decimal)

    def test_03_nullable_foreign_keys(self, db):
        p = ReductionPriority(
            priority_code="PRIORITY_GLOBAL_NULL_FK",
            document_id=None,
            opportunity_id=None,
            project_id=None,
            title="Global Priority",
            reason="No foreign keys attached",
            priority_score=Decimal("50.00"),
            priority_level="MEDIUM",
            current_emissions_kgco2e=Decimal("500.000000"),
            current_emissions_tco2e=Decimal("0.500000"),
        )
        db.add(p)
        db.commit()
        db.refresh(p)

        assert p.id is not None
        assert p.document_id is None
        assert p.opportunity_id is None
        assert p.project_id is None

    def test_04_to_dict_method(self, db):
        p = ReductionPriority(
            priority_code="PRIORITY_TO_DICT",
            title="Dict Conversion",
            reason="Verify to_dict helper",
            priority_score=Decimal("75.00"),
            priority_level="HIGH",
            impact_score=Decimal("22.00"),
            current_emissions_kgco2e=Decimal("1000.000000"),
            current_emissions_tco2e=Decimal("1.000000"),
        )
        db.add(p)
        db.commit()
        db.refresh(p)

        d = p.to_dict()
        assert d["priority_code"] == "PRIORITY_TO_DICT"
        assert d["priority_score"] == 75.0
        assert d["impact_score"] == 22.0
        assert d["current_emissions_tco2e"] == 1.0


# ==============================================================================
# 2. CONFIGURATION & WEIGHT SUMMATION TESTS
# ==============================================================================
class TestScoringConfiguration:

    def test_05_weight_constants_sum_to_100(self):
        assert TOTAL_MAX_WEIGHT == Decimal("100.0")
        assert IMPACT_WEIGHT == Decimal("30.0")
        assert TREND_WEIGHT == Decimal("20.0")
        assert FORECAST_WEIGHT == Decimal("15.0")
        assert PERSISTENCE_WEIGHT == Decimal("15.0")
        assert ACTIONABILITY_WEIGHT == Decimal("10.0")
        assert DATA_QUALITY_WEIGHT == Decimal("5.0")
        assert BLOCKER_WEIGHT == Decimal("5.0")

    def test_06_version_constant_is_1_0(self):
        assert REDUCTION_INTELLIGENCE_VERSION == "1.0"


# ==============================================================================
# 3. IMPACT SIGNAL TESTS
# ==============================================================================
class TestImpactSignal:

    def test_07_impact_greater_than_50_percent(self, db):
        # 31.88 tCO2e out of 33.00 tCO2e = 96.6% -> should score 30/30
        score = reduction_intelligence_service._calculate_impact_score(
            source_kg=Decimal("31879.0"),
            total_kg=Decimal("33004.6")
        )
        assert score == IMPACT_SCORE_VERY_HIGH
        assert score == Decimal("30.0")

    def test_08_impact_tier_25_to_50_percent(self, db):
        # 30% of total -> score 22/30
        score = reduction_intelligence_service._calculate_impact_score(
            source_kg=Decimal("3000.0"),
            total_kg=Decimal("10000.0")
        )
        assert score == IMPACT_SCORE_HIGH
        assert score == Decimal("22.0")

    def test_09_impact_tier_10_to_25_percent(self, db):
        # 15% of total -> score 14/30
        score = reduction_intelligence_service._calculate_impact_score(
            source_kg=Decimal("1500.0"),
            total_kg=Decimal("10000.0")
        )
        assert score == IMPACT_SCORE_MEDIUM
        assert score == Decimal("14.0")

    def test_10_impact_tier_less_than_10_percent(self, db):
        # 3.4% of total -> score 6/30
        score = reduction_intelligence_service._calculate_impact_score(
            source_kg=Decimal("1125.6"),
            total_kg=Decimal("33004.6")
        )
        assert score == IMPACT_SCORE_LOW
        assert score == Decimal("6.0")

    def test_11_impact_zero_total_emissions_safe(self, db):
        # Total emissions = 0 -> score 0 without division by zero
        score = reduction_intelligence_service._calculate_impact_score(
            source_kg=Decimal("0.0"),
            total_kg=Decimal("0.0")
        )
        assert score == IMPACT_SCORE_ZERO
        assert score == Decimal("0.0")


# ==============================================================================
# 4. TREND SIGNAL TESTS
# ==============================================================================
class TestTrendSignal:

    def test_12_trend_strong_increase_25_percent(self):
        # 30% increase -> strong trend (20/20)
        score = reduction_intelligence_service._calculate_trend_score(
            change_pct=Decimal("30.0"),
            is_repeated_increase=False
        )
        assert score == TREND_SCORE_STRONG
        assert score == Decimal("20.0")

    def test_13_trend_moderate_increase_10_to_25_percent(self):
        # 15% increase -> moderate trend (14/20)
        score = reduction_intelligence_service._calculate_trend_score(
            change_pct=Decimal("15.0"),
            is_repeated_increase=False
        )
        assert score == TREND_SCORE_MODERATE
        assert score == Decimal("14.0")

    def test_14_trend_weak_increase_less_than_10_percent(self):
        # 5% increase -> weak trend (8/20)
        score = reduction_intelligence_service._calculate_trend_score(
            change_pct=Decimal("5.0"),
            is_repeated_increase=False
        )
        assert score == TREND_SCORE_WEAK
        assert score == Decimal("8.0")

    def test_15_trend_stable_or_decreasing(self):
        # -10% decrease -> 0/20
        score = reduction_intelligence_service._calculate_trend_score(
            change_pct=Decimal("-10.0"),
            is_repeated_increase=False
        )
        assert score == TREND_SCORE_STABLE_OR_DECREASING
        assert score == Decimal("0.0")

    def test_16_trend_repeated_consecutive_increases(self):
        # 3 consecutive increases bonus
        series = [
            ("2024-08", Decimal("1000.0")),
            ("2024-09", Decimal("1100.0")),
            ("2024-10", Decimal("1250.0")),
        ]
        change_pct, is_repeated = reduction_intelligence_service._calculate_trend_metrics(series)
        assert is_repeated is True
        assert change_pct is not None
        score = reduction_intelligence_service._calculate_trend_score(change_pct, is_repeated)
        assert score > TREND_SCORE_MODERATE


# ==============================================================================
# 5. PERSISTENCE SIGNAL TESTS
# ==============================================================================
class TestPersistenceSignal:

    def test_17_persistence_3_or_more_periods(self):
        score = reduction_intelligence_service._calculate_persistence_score(3)
        assert score == PERSISTENCE_SCORE_STRONG
        assert score == Decimal("15.0")

    def test_18_persistence_2_periods(self):
        score = reduction_intelligence_service._calculate_persistence_score(2)
        assert score == PERSISTENCE_SCORE_MODERATE
        assert score == Decimal("10.0")

    def test_19_persistence_1_period(self):
        score = reduction_intelligence_service._calculate_persistence_score(1)
        assert score == PERSISTENCE_SCORE_LOW
        assert score == Decimal("5.0")

    def test_20_persistence_0_periods(self):
        score = reduction_intelligence_service._calculate_persistence_score(0)
        assert score == Decimal("0.0")


# ==============================================================================
# 6. FORECAST SIGNAL TESTS
# ==============================================================================
class TestForecastSignal:

    def test_21_forecast_insufficient_data_returns_zero_no_penalty(self, db):
        # When less than 3 periods exist, forecast signal returns 0 and is marked unavailable
        doc = create_sample_document(db, 1)
        calc = create_sample_calculation(db, 1, doc.id)
        create_sample_ledger_entry(db, calc.id, doc.id, period="2024-10", co2e_kg=1000.0)

        dto, score, fcst_kg = reduction_intelligence_service._evaluate_forecast_signal(
            db=db,
            scope="SCOPE_2",
            category="ENERGY",
            activity_type="grid_electricity",
            last_actual_kg=Decimal("1000.0")
        )
        assert score == Decimal("0.0")
        assert dto is None

    def test_22_forecast_with_sufficient_periods_evaluated(self, db):
        doc = create_sample_document(db, 1)
        calc = create_sample_calculation(db, 1, doc.id)
        # Create 4 consecutive actual periods
        create_sample_ledger_entry(db, calc.id, doc.id, period="2024-07", co2e_kg=1000.0)
        create_sample_ledger_entry(db, calc.id, doc.id, period="2024-08", co2e_kg=1100.0)
        create_sample_ledger_entry(db, calc.id, doc.id, period="2024-09", co2e_kg=1200.0)
        create_sample_ledger_entry(db, calc.id, doc.id, period="2024-10", co2e_kg=1300.0)

        dto, score, fcst_kg = reduction_intelligence_service._evaluate_forecast_signal(
            db=db,
            scope="SCOPE_2",
            category="ENERGY",
            activity_type="grid_electricity",
            last_actual_kg=Decimal("1300.0")
        )
        assert dto is not None
        assert score > Decimal("0.0")


# ==============================================================================
# 7. DATA QUALITY & BLOCKER SIGNAL TESTS
# ==============================================================================
class TestDataQualityAndBlockers:

    def test_23_unresolved_emission_factor_flags_blocker(self, db):
        doc = create_sample_document(db, 1)
        calc = create_sample_calculation(db, 1, doc.id)
        # Entry with factor_value = None
        entry = create_sample_ledger_entry(db, calc.id, doc.id, factor_id=None, factor_value=None)

        dq_score, blocker_score, is_dq = reduction_intelligence_service._calculate_data_quality_score(
            entries=[entry],
            opportunity=None
        )
        assert is_dq is True
        assert dq_score == DATA_QUALITY_SCORE_UNRESOLVED_FACTOR
        assert blocker_score == BLOCKER_SCORE_CRITICAL

    def test_24_clean_posted_entry_has_zero_dq_penalty(self, db):
        doc = create_sample_document(db, 1)
        calc = create_sample_calculation(db, 1, doc.id)
        entry = create_sample_ledger_entry(db, calc.id, doc.id, factor_id=1, factor_value=0.82)

        dq_score, blocker_score, is_dq = reduction_intelligence_service._calculate_data_quality_score(
            entries=[entry],
            opportunity=None
        )
        assert is_dq is False
        assert dq_score == Decimal("0.0")
        assert blocker_score == Decimal("0.0")


# ==============================================================================
# 8. ACTIONABILITY & PROJECT SIGNAL TESTS
# ==============================================================================
class TestActionabilityAndProjects:

    def test_25_concrete_opportunity_scores_max_actionability(self, db):
        opp = ReductionOpportunity(
            opportunity_code="OPP_CONCRETE_1",
            title="Install Rooftop Solar",
            description="Install 50kW solar array",
            category="ENERGY",
            scope="SCOPE_2",
            priority="HIGH",
            trigger_type="HIGH_ENERGY_USE",
            recommended_action="Conduct site rooftop load assessment and issue solar EPC tender.",
            rationale="Reduces grid reliance.",
            limitations="Capex required."
        )
        score, action_type = reduction_intelligence_service._calculate_actionability_score(opp)
        assert score == ACTIONABILITY_SCORE_CONCRETE
        assert action_type == "CONCRETE"

    def test_26_data_gap_opportunity_classified(self, db):
        opp = ReductionOpportunity(
            opportunity_code="OPP_DATA_GAP_1",
            title="Solar Factor Unresolved",
            description="Missing emission factor for solar self-generation",
            category="DATA_QUALITY",
            scope="SCOPE_2",
            priority="HIGH",
            trigger_type="UNRESOLVED_FACTOR",
            recommended_action="Obtain verified factor.",
            rationale="Factor required.",
            limitations="Unresolved."
        )
        score, action_type = reduction_intelligence_service._calculate_actionability_score(opp)
        assert score == ACTIONABILITY_SCORE_DATA_GAP
        assert action_type == "DATA_GAP"

    def test_27_project_in_progress_deprioritizes_as_fresh_action(self):
        proj = ReductionProject(
            project_code="PRJ-2024-0001",
            title="Solar PV Installation",
            category="ENERGY",
            status="IN_PROGRESS"
        )
        modifier = reduction_intelligence_service._calculate_project_status_modifier(proj)
        assert modifier < Decimal("0.0")

    def test_28_project_planned_has_no_negative_modifier(self):
        proj = ReductionProject(
            project_code="PRJ-2024-0002",
            title="HVAC Tuneup",
            category="ENERGY",
            status="PLANNED"
        )
        modifier = reduction_intelligence_service._calculate_project_status_modifier(proj)
        assert modifier == Decimal("0.0")


# ==============================================================================
# 9. PRIORITY LEVEL MAPPING & TOTAL SCORE TESTS
# ==============================================================================
class TestScoreAggregationAndRanking:

    def test_29_critical_priority_level_threshold(self):
        assert reduction_intelligence_service._map_priority_level(Decimal("85.0")) == PRIORITY_LEVEL_CRITICAL
        assert reduction_intelligence_service._map_priority_level(Decimal("80.0")) == PRIORITY_LEVEL_CRITICAL

    def test_30_high_priority_level_threshold(self):
        assert reduction_intelligence_service._map_priority_level(Decimal("75.0")) == PRIORITY_LEVEL_HIGH
        assert reduction_intelligence_service._map_priority_level(Decimal("60.0")) == PRIORITY_LEVEL_HIGH

    def test_31_medium_priority_level_threshold(self):
        assert reduction_intelligence_service._map_priority_level(Decimal("55.0")) == PRIORITY_LEVEL_MEDIUM
        assert reduction_intelligence_service._map_priority_level(Decimal("40.0")) == PRIORITY_LEVEL_MEDIUM

    def test_32_low_priority_level_threshold(self):
        assert reduction_intelligence_service._map_priority_level(Decimal("30.0")) == PRIORITY_LEVEL_LOW
        assert reduction_intelligence_service._map_priority_level(Decimal("20.0")) == PRIORITY_LEVEL_LOW

    def test_33_informational_priority_level_threshold(self):
        assert reduction_intelligence_service._map_priority_level(Decimal("15.0")) == PRIORITY_LEVEL_INFORMATIONAL
        assert reduction_intelligence_service._map_priority_level(Decimal("0.0")) == PRIORITY_LEVEL_INFORMATIONAL


# ==============================================================================
# 10. EVALUATE PRIORITIES SERVICE & DEDUPLICATION TESTS
# ==============================================================================
class TestEvaluatePrioritiesService:

    def test_34_evaluate_priorities_orders_highest_emission_first(self, db):
        doc = create_sample_document(db, 1)
        calc1 = create_sample_calculation(db, 1, doc.id, scope="SCOPE_2", co2e_kg=31879.0)
        calc2 = create_sample_calculation(db, 2, doc.id, scope="SCOPE_1", co2e_kg=1125.6)

        create_sample_ledger_entry(db, calc1.id, doc.id, activity="grid_electricity", category="ENERGY", scope="SCOPE_2", co2e_kg=31879.0)
        create_sample_ledger_entry(db, calc2.id, doc.id, activity="diesel_generator", category="FUEL", scope="SCOPE_1", co2e_kg=1125.6)

        priorities = reduction_intelligence_service.evaluate_priorities(db, document_id=doc.id, save_to_db=True)

        assert len(priorities) == 2
        assert priorities[0].priority_rank == 1
        assert "grid_electricity" in priorities[0].activity_type or "Grid" in priorities[0].title
        assert priorities[0].current_emissions_kgco2e > priorities[1].current_emissions_kgco2e


    def test_35_non_posted_entries_excluded_from_priorities(self, db):
        doc = create_sample_document(db, 1)
        calc1 = create_sample_calculation(db, 1, doc.id, scope="SCOPE_2", co2e_kg=31879.0)
        calc2 = create_sample_calculation(db, 2, doc.id, scope="SCOPE_1", co2e_kg=50000.0)

        create_sample_ledger_entry(db, calc1.id, doc.id, activity="grid_electricity", co2e_kg=31879.0, status="POSTED")
        create_sample_ledger_entry(db, calc2.id, doc.id, activity="diesel_generator", co2e_kg=50000.0, status="PENDING")

        priorities = reduction_intelligence_service.evaluate_priorities(db, document_id=doc.id, save_to_db=True)

        assert len(priorities) == 1
        assert priorities[0].activity_type == "grid_electricity"

    def test_36_deduplication_combines_multiple_entries_same_activity(self, db):
        doc = create_sample_document(db, 1)
        calc1 = create_sample_calculation(db, 1, doc.id, scope="SCOPE_2", co2e_kg=10000.0)

        # 3 posted entries for the same activity
        create_sample_ledger_entry(db, calc1.id, doc.id, activity="grid_electricity", period="2024-08", co2e_kg=10000.0)
        create_sample_ledger_entry(db, calc1.id, doc.id, activity="grid_electricity", period="2024-09", co2e_kg=11000.0)
        create_sample_ledger_entry(db, calc1.id, doc.id, activity="grid_electricity", period="2024-10", co2e_kg=12000.0)

        priorities = reduction_intelligence_service.evaluate_priorities(db, document_id=doc.id, save_to_db=True)

        # Must merge into 1 reduction priority
        assert len(priorities) == 1
        assert priorities[0].activity_type == "grid_electricity"
        assert priorities[0].persistence_score == PERSISTENCE_SCORE_STRONG

    def test_37_cross_document_isolation(self, db):
        doc1 = create_sample_document(db, 1, "doc1.pdf")
        doc2 = create_sample_document(db, 2, "doc2.pdf")

        calc1 = create_sample_calculation(db, 1, doc1.id, co2e_kg=5000.0)
        calc2 = create_sample_calculation(db, 2, doc2.id, co2e_kg=8000.0)

        create_sample_ledger_entry(db, calc1.id, doc1.id, activity="grid_electricity", co2e_kg=5000.0)
        create_sample_ledger_entry(db, calc2.id, doc2.id, activity="diesel_fuel", co2e_kg=8000.0)

        priorities_doc1 = reduction_intelligence_service.evaluate_priorities(db, document_id=doc1.id, save_to_db=False)
        priorities_doc2 = reduction_intelligence_service.evaluate_priorities(db, document_id=doc2.id, save_to_db=False)

        assert len(priorities_doc1) == 1
        assert priorities_doc1[0].activity_type == "grid_electricity"

        assert len(priorities_doc2) == 1
        assert priorities_doc2[0].activity_type == "diesel_fuel"


# ==============================================================================
# 11. SUMMARY & KPI TESTS
# ==============================================================================
class TestSummaryAndKPIs:

    def test_38_empty_database_summary(self, db):
        summary = reduction_intelligence_service.get_summary(db)
        assert summary.total_priorities == 0
        assert summary.critical == 0
        assert summary.high == 0
        assert summary.top_priority is None

    def test_39_summary_with_priorities(self, db):
        doc = create_sample_document(db, 1)
        calc1 = create_sample_calculation(db, 1, doc.id, scope="SCOPE_2", co2e_kg=31879.0)
        create_sample_ledger_entry(db, calc1.id, doc.id, activity="grid_electricity", co2e_kg=31879.0)

        summary = reduction_intelligence_service.get_summary(db, document_id=doc.id)
        assert summary.total_priorities >= 1
        assert summary.top_priority is not None
        assert summary.top_priority_score is not None


# ==============================================================================
# 12. IMMUTABILITY & REPEATABILITY TESTS
# ==============================================================================
class TestImmutabilityAndRepeatability:

    def test_40_ledger_entries_never_mutated(self, db):
        doc = create_sample_document(db, 1)
        calc = create_sample_calculation(db, 1, doc.id, co2e_kg=31879.0)
        entry = create_sample_ledger_entry(db, calc.id, doc.id, co2e_kg=31879.0)

        orig_co2e = entry.calculated_co2e
        orig_status = entry.accounting_status

        reduction_intelligence_service.evaluate_priorities(db, document_id=doc.id, save_to_db=True)
        reduction_intelligence_service.evaluate_priorities(db, document_id=doc.id, save_to_db=True)

        db.refresh(entry)
        assert entry.calculated_co2e == orig_co2e
        assert entry.accounting_status == orig_status

    def test_41_idempotent_recalculation_no_duplicate_rows(self, db):
        doc = create_sample_document(db, 1)
        calc = create_sample_calculation(db, 1, doc.id, co2e_kg=31879.0)
        create_sample_ledger_entry(db, calc.id, doc.id, co2e_kg=31879.0)

        reduction_intelligence_service.evaluate_priorities(db, document_id=doc.id, save_to_db=True)
        count_first = db.query(ReductionPriority).filter(ReductionPriority.document_id == doc.id).count()

        reduction_intelligence_service.evaluate_priorities(db, document_id=doc.id, save_to_db=True)
        count_second = db.query(ReductionPriority).filter(ReductionPriority.document_id == doc.id).count()

        assert count_first == count_second

    def test_42_same_input_produces_identical_scores(self, db):
        doc = create_sample_document(db, 1)
        calc = create_sample_calculation(db, 1, doc.id, co2e_kg=31879.0)
        create_sample_ledger_entry(db, calc.id, doc.id, co2e_kg=31879.0)

        run1 = reduction_intelligence_service.evaluate_priorities(db, document_id=doc.id, save_to_db=False)
        run2 = reduction_intelligence_service.evaluate_priorities(db, document_id=doc.id, save_to_db=False)

        assert run1[0].priority_score == run2[0].priority_score
        assert run1[0].priority_level == run2[0].priority_level


# ==============================================================================
# 13. API ENDPOINT TESTS
# ==============================================================================
class TestAPIEndpoints:

    def test_43_get_priorities_empty(self, client):
        resp = client.get("/api/reduction-intelligence")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_44_get_priorities_with_data(self, client, db):
        doc = create_sample_document(db, 1)
        calc = create_sample_calculation(db, 1, doc.id, co2e_kg=31879.0)
        create_sample_ledger_entry(db, calc.id, doc.id, co2e_kg=31879.0)

        resp = client.get("/api/reduction-intelligence")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert data["items"][0]["priority_level"] in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

    def test_45_get_summary_endpoint(self, client, db):
        doc = create_sample_document(db, 1)
        calc = create_sample_calculation(db, 1, doc.id, co2e_kg=31879.0)
        create_sample_ledger_entry(db, calc.id, doc.id, co2e_kg=31879.0)

        resp = client.get("/api/reduction-intelligence/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_priorities"] >= 1
        assert data["top_priority"] is not None

    def test_46_get_priorities_alias_endpoint(self, client, db):
        doc = create_sample_document(db, 1)
        calc = create_sample_calculation(db, 1, doc.id, co2e_kg=31879.0)
        create_sample_ledger_entry(db, calc.id, doc.id, co2e_kg=31879.0)

        resp = client.get("/api/reduction-intelligence/priorities")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    def test_47_get_priority_by_id_success(self, client, db):
        doc = create_sample_document(db, 1)
        calc = create_sample_calculation(db, 1, doc.id, co2e_kg=31879.0)
        create_sample_ledger_entry(db, calc.id, doc.id, co2e_kg=31879.0)

        priorities = reduction_intelligence_service.evaluate_priorities(db, document_id=doc.id, save_to_db=True)
        p_id = priorities[0].id

        resp = client.get(f"/api/reduction-intelligence/{p_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == p_id
        assert data["score_breakdown"] is not None

    def test_48_get_priority_by_id_not_found(self, client):
        resp = client.get("/api/reduction-intelligence/99999")
        assert resp.status_code == 404

    def test_49_get_document_priorities_endpoint(self, client, db):
        doc = create_sample_document(db, 1)
        calc = create_sample_calculation(db, 1, doc.id, co2e_kg=31879.0)
        create_sample_ledger_entry(db, calc.id, doc.id, co2e_kg=31879.0)

        resp = client.get(f"/api/reduction-intelligence/document/{doc.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    def test_50_post_recalculate_endpoint(self, client, db):
        doc = create_sample_document(db, 1)
        calc = create_sample_calculation(db, 1, doc.id, co2e_kg=31879.0)
        create_sample_ledger_entry(db, calc.id, doc.id, co2e_kg=31879.0)

        resp = client.post("/api/reduction-intelligence/recalculate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SUCCESS"
        assert data["priorities_generated"] >= 1

    def test_51_get_recalculate_convenience_endpoint(self, client, db):
        doc = create_sample_document(db, 1)
        calc = create_sample_calculation(db, 1, doc.id, co2e_kg=31879.0)
        create_sample_ledger_entry(db, calc.id, doc.id, co2e_kg=31879.0)

        resp = client.get("/api/reduction-intelligence/recalculate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SUCCESS"

    def test_52_filter_by_scope(self, client, db):
        doc = create_sample_document(db, 1)
        calc1 = create_sample_calculation(db, 1, doc.id, scope="SCOPE_2", co2e_kg=31879.0)
        calc2 = create_sample_calculation(db, 2, doc.id, scope="SCOPE_1", co2e_kg=1125.6)

        create_sample_ledger_entry(db, calc1.id, doc.id, activity="grid_electricity", scope="SCOPE_2", co2e_kg=31879.0)
        create_sample_ledger_entry(db, calc2.id, doc.id, activity="diesel_generator", scope="SCOPE_1", co2e_kg=1125.6)

        resp = client.get("/api/reduction-intelligence?scope=SCOPE_2")
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["scope"] == "SCOPE_2"

    def test_53_filter_by_priority_level(self, client, db):
        doc = create_sample_document(db, 1)
        calc = create_sample_calculation(db, 1, doc.id, scope="SCOPE_2", co2e_kg=31879.0)
        create_sample_ledger_entry(db, calc.id, doc.id, co2e_kg=31879.0)

        resp = client.get("/api/reduction-intelligence?priority_level=CRITICAL")
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["priority_level"] == "CRITICAL"


# ==============================================================================
# 14. COPILOT GROUNDING & SAFETY TESTS
# ==============================================================================
class TestCopilotIntegration:

    def test_54_intent_classification_focus_on_first(self):
        intent = classify_intent("What should I focus on first to reduce emissions?")
        assert intent == "ACTION_RECOMMENDATION"

    def test_55_intent_classification_biggest_reduction_opportunity(self):
        intent = classify_intent("What is my biggest reduction opportunity?")
        assert intent == "ACTION_RECOMMENDATION"

    def test_56_intent_classification_why_is_electricity_top_priority(self):
        intent = classify_intent("Why is electricity my top priority?")
        assert intent == "ACTION_RECOMMENDATION"

    def test_57_intent_classification_where_to_reduce_emissions(self):
        intent = classify_intent("Where can I reduce emissions?")
        assert intent == "ACTION_RECOMMENDATION"

    def test_58_copilot_response_grounded_in_priorities(self, db):
        doc = create_sample_document(db, 1)
        calc = create_sample_calculation(db, 1, doc.id, scope="SCOPE_2", co2e_kg=31879.0)
        create_sample_ledger_entry(db, calc.id, doc.id, co2e_kg=31879.0)

        resp = copilot_service.chat(db, "What should I focus on first?", document_id=doc.id)
        assert resp.answer is not None
        assert "Grid Electricity" in resp.answer or "electricity" in resp.answer.lower()
        assert resp.intent == "ACTION_RECOMMENDATION"


    def test_59_copilot_refusal_boundary_no_hallucinated_savings(self, db):
        doc = create_sample_document(db, 1)
        calc = create_sample_calculation(db, 1, doc.id, scope="SCOPE_2", co2e_kg=31879.0)
        create_sample_ledger_entry(db, calc.id, doc.id, co2e_kg=31879.0)

        resp = copilot_service.chat(db, "How much will switching to solar save me in cost?", document_id=doc.id)
        assert "does not generate hypothetical financial savings" in resp.answer or "Step 22C" in resp.answer

    def test_60_copilot_why_electricity_explanation(self, db):
        doc = create_sample_document(db, 1)
        calc = create_sample_calculation(db, 1, doc.id, scope="SCOPE_2", co2e_kg=31879.0)
        create_sample_ledger_entry(db, calc.id, doc.id, co2e_kg=31879.0)

        resp = copilot_service.chat(db, "Why is electricity my top priority?", document_id=doc.id)
        assert "31.88 tCO2e" in resp.answer or "largest share" in resp.answer
