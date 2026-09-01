import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from backend.app.database.base import Base
from backend.app.models.document import Document
from backend.app.models.sustainability_metric import SustainabilityMetric
from backend.app.services.insights_service import InsightsService, insights_service
from backend.app.main import app
from backend.app.database.session import get_db

@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test_insights.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    yield db
    db.close()

def test_a_twelve_percent_electricity_increase(test_db):
    """Test A: Electricity increases by 12% (> 10% threshold) -> ATTENTION."""
    m1 = SustainabilityMetric(
        document_id=1,
        company_name="Acme Corp",
        metric_type="electricity_consumption",
        category="energy",
        value=1000.0,
        unit="kWh",
        period_start="October 2024",
        source_field="energy.electricity_kwh"
    )
    m2 = SustainabilityMetric(
        document_id=2,
        company_name="Acme Corp",
        metric_type="electricity_consumption",
        category="energy",
        value=1120.0,
        unit="kWh",
        period_start="November 2024",
        source_field="energy.electricity_kwh"
    )
    test_db.add_all([m1, m2])
    test_db.commit()

    service = InsightsService()
    insights = service.generate_metric_insights(test_db, company="Acme Corp")

    increase_insights = [i for i in insights if i.category == "INCREASE"]
    assert len(increase_insights) == 1
    ins = increase_insights[0]
    assert ins.severity == "ATTENTION"
    assert ins.percentage_change == 12.0
    assert "12%" in ins.message
    assert "Internal monitoring threshold" in (ins.threshold_note or "")
    assert ins.source_document_id == 2
    assert ins.previous_source_document_id == 1

def test_b_five_percent_electricity_decrease(test_db):
    """Test B: Electricity decreases by 5% -> INFO, neutral wording without praise."""
    m1 = SustainabilityMetric(
        document_id=1,
        company_name="Acme Corp",
        metric_type="electricity_consumption",
        category="energy",
        value=1000.0,
        unit="kWh",
        period_start="October 2024",
        source_field="energy.electricity_kwh"
    )
    m2 = SustainabilityMetric(
        document_id=2,
        company_name="Acme Corp",
        metric_type="electricity_consumption",
        category="energy",
        value=950.0,
        unit="kWh",
        period_start="November 2024",
        source_field="energy.electricity_kwh"
    )
    test_db.add_all([m1, m2])
    test_db.commit()

    service = InsightsService()
    insights = service.generate_metric_insights(test_db, company="Acme Corp")

    decrease_insights = [i for i in insights if i.category == "DECREASE"]
    assert len(decrease_insights) == 1
    ins = decrease_insights[0]
    assert ins.severity == "INFO"
    assert ins.percentage_change == -5.0
    assert "5%" in ins.message

    # Must NOT contain positive praise words
    msg_lower = ins.message.lower()
    for forbidden in ["great", "improvement", "excellent", "good", "congratulations"]:
        assert forbidden not in msg_lower

def test_c_missing_water_in_latest_period(test_db):
    """Test C: Water reported in previous period but missing in latest period -> MISSING_DATA."""
    # October: Electricity + Water
    m_oct_elec = SustainabilityMetric(
        document_id=1,
        company_name="Acme Corp",
        metric_type="electricity_consumption",
        category="energy",
        value=5000.0,
        unit="kWh",
        period_start="October 2024",
        source_field="energy.electricity_kwh"
    )
    m_oct_water = SustainabilityMetric(
        document_id=1,
        company_name="Acme Corp",
        metric_type="water_consumption",
        category="water",
        value=1000.0,
        unit="kL",
        period_start="October 2024",
        source_field="water_and_waste.water_consumption_kl"
    )
    # November: Electricity only (water missing)
    m_nov_elec = SustainabilityMetric(
        document_id=2,
        company_name="Acme Corp",
        metric_type="electricity_consumption",
        category="energy",
        value=5200.0,
        unit="kWh",
        period_start="November 2024",
        source_field="energy.electricity_kwh"
    )
    test_db.add_all([m_oct_elec, m_oct_water, m_nov_elec])
    test_db.commit()

    service = InsightsService()
    insights = service.generate_metric_insights(test_db, company="Acme Corp")

    missing = [i for i in insights if i.category == "MISSING_DATA"]
    assert len(missing) == 1
    assert missing[0].metric_type == "water_consumption"
    assert missing[0].severity == "INFO"
    assert "not reported" in missing[0].message

def test_d_single_period_no_comparison(test_db):
    """Test D: Only one period exists -> No period-over-period comparison insight."""
    m1 = SustainabilityMetric(
        document_id=1,
        company_name="Acme Corp",
        metric_type="electricity_consumption",
        category="energy",
        value=1000.0,
        unit="kWh",
        period_start="October 2024",
        source_field="energy.electricity_kwh"
    )
    test_db.add(m1)
    test_db.commit()

    service = InsightsService()
    insights = service.generate_metric_insights(test_db, company="Acme Corp")

    # No INCREASE or DECREASE comparison insight
    comparison_insights = [i for i in insights if i.category in ["INCREASE", "DECREASE"]]
    assert len(comparison_insights) == 0

def test_e_three_consecutive_increases_trend(test_db):
    """Test E: Three consecutive increasing periods (Oct, Nov, Dec) -> TREND."""
    m1 = SustainabilityMetric(
        document_id=1,
        company_name="Acme Corp",
        metric_type="electricity_consumption",
        category="energy",
        value=1000.0,
        unit="kWh",
        period_start="October 2024",
        source_field="energy.electricity_kwh"
    )
    m2 = SustainabilityMetric(
        document_id=2,
        company_name="Acme Corp",
        metric_type="electricity_consumption",
        category="energy",
        value=1100.0,
        unit="kWh",
        period_start="November 2024",
        source_field="energy.electricity_kwh"
    )
    m3 = SustainabilityMetric(
        document_id=3,
        company_name="Acme Corp",
        metric_type="electricity_consumption",
        category="energy",
        value=1200.0,
        unit="kWh",
        period_start="December 2024",
        source_field="energy.electricity_kwh"
    )
    test_db.add_all([m1, m2, m3])
    test_db.commit()

    service = InsightsService()
    insights = service.generate_metric_insights(test_db, company="Acme Corp")

    trends = [i for i in insights if i.category == "TREND"]
    assert len(trends) == 1
    assert trends[0].severity == "ATTENTION"
    assert "consecutive reporting periods" in trends[0].message
    assert trends[0].source_document_id == 3

def test_f_non_consecutive_periods_no_trend(test_db):
    """Test F: Missing month: October + December only -> No three consecutive periods trend."""
    m1 = SustainabilityMetric(
        document_id=1,
        company_name="Acme Corp",
        metric_type="electricity_consumption",
        category="energy",
        value=1000.0,
        unit="kWh",
        period_start="October 2024",
        source_field="energy.electricity_kwh"
    )
    m2 = SustainabilityMetric(
        document_id=2,
        company_name="Acme Corp",
        metric_type="electricity_consumption",
        category="energy",
        value=1200.0,
        unit="kWh",
        period_start="December 2024",
        source_field="energy.electricity_kwh"
    )
    test_db.add_all([m1, m2])
    test_db.commit()

    service = InsightsService()
    insights = service.generate_metric_insights(test_db, company="Acme Corp")

    trends = [i for i in insights if i.category == "TREND"]
    assert len(trends) == 0

def test_g_ocr_review_required_insight(test_db):
    """Test G: OCR document with low quality / needs review -> NEEDS_REVIEW with REVIEW severity."""
    doc = Document(
        filename="scanned_manifest.pdf",
        original_filename="Scanned Waste Manifest.pdf",
        file_path="/tmp/fake.pdf",
        file_size=1024,
        company_name="Tara Engineering Works",
        document_type="Waste Manifest",
        extraction_method="ocr_fallback",
        quality_score=67.0,
        review_status="NEEDS_REVIEW",
        status="COMPLETED"
    )
    test_db.add(doc)
    test_db.commit()

    service = InsightsService()
    insights = service.generate_metric_insights(test_db, company="Tara Engineering Works")

    reviews = [i for i in insights if i.category == "NEEDS_REVIEW"]
    assert len(reviews) == 1
    assert reviews[0].severity == "REVIEW"
    assert reviews[0].source_document_id == doc.id
    assert "OCR" in reviews[0].message
    assert "67/100" in reviews[0].message

def test_h_unit_mismatch_no_invalid_comparison(test_db):
    """Test H: Incompatible units (kWh vs Liters) -> No comparison insight."""
    m1 = SustainabilityMetric(
        document_id=1,
        company_name="Acme Corp",
        metric_type="electricity_consumption",
        category="energy",
        value=1000.0,
        unit="kWh",
        period_start="October 2024",
        source_field="energy.electricity_kwh"
    )
    m2 = SustainabilityMetric(
        document_id=2,
        company_name="Acme Corp",
        metric_type="electricity_consumption",
        category="energy",
        value=1200.0,
        unit="Liters",  # Incompatible unit
        period_start="November 2024",
        source_field="energy.electricity_kwh"
    )
    test_db.add_all([m1, m2])
    test_db.commit()

    service = InsightsService()
    insights = service.generate_metric_insights(test_db, company="Acme Corp")

    comparison_insights = [i for i in insights if i.category in ["INCREASE", "DECREASE"]]
    assert len(comparison_insights) == 0

def test_i_new_metric_first_time(test_db):
    """Test I: Metric appears for the first time -> NEW_DATA."""
    m1 = SustainabilityMetric(
        document_id=1,
        company_name="Acme Corp",
        metric_type="water_consumption",
        category="water",
        value=1200.0,
        unit="kL",
        period_start="November 2024",
        source_field="water_and_waste.water_consumption_kl"
    )
    test_db.add(m1)
    test_db.commit()

    service = InsightsService()
    insights = service.generate_metric_insights(test_db, company="Acme Corp")

    new_data = [i for i in insights if i.category == "NEW_DATA"]
    assert len(new_data) == 1
    assert new_data[0].metric_type == "water_consumption"
    assert new_data[0].severity == "INFO"
    assert "first time" in new_data[0].message

def test_j_api_endpoint_filters(test_db):
    """Test J: GET /api/insights with company, severity, and metric_type filters."""
    # Seed metrics and documents
    m1 = SustainabilityMetric(
        document_id=1,
        company_name="Tara Engineering",
        metric_type="electricity_consumption",
        category="energy",
        value=1000.0,
        unit="kWh",
        period_start="October 2024",
        source_field="energy.electricity_kwh"
    )
    m2 = SustainabilityMetric(
        document_id=2,
        company_name="Tara Engineering",
        metric_type="electricity_consumption",
        category="energy",
        value=1200.0,  # 20% increase -> ATTENTION
        unit="kWh",
        period_start="November 2024",
        source_field="energy.electricity_kwh"
    )
    m3 = SustainabilityMetric(
        document_id=3,
        company_name="Beta Steel",
        metric_type="fuel_consumption",
        category="energy",
        value=500.0,
        unit="Liters",
        period_start="October 2024",
        source_field="energy.fuel_diesel_liters"
    )
    doc_rev = Document(
        filename="scanned.pdf",
        original_filename="Scanned.pdf",
        file_path="/tmp/fake2.pdf",
        file_size=500,
        company_name="Tara Engineering",
        extraction_method="ocr_fallback",
        quality_score=60.0,
        review_status="NEEDS_REVIEW",
        status="COMPLETED"
    )
    test_db.add_all([m1, m2, m3, doc_rev])
    test_db.commit()

    # Override get_db in FastAPI app
    app.dependency_overrides[get_db] = lambda: test_db
    client = TestClient(app)

    try:
        # 1. No filters
        res = client.get("/api/insights")
        assert res.status_code == 200
        data = res.json()
        assert "insights" in data
        assert data["count"] >= 2

        # 2. Company filter
        res_company = client.get("/api/insights?company=Tara%20Engineering")
        assert res_company.status_code == 200
        data_c = res_company.json()
        for item in data_c["insights"]:
            assert item["company_name"] == "Tara Engineering"

        # 3. Severity filter
        res_sev = client.get("/api/insights?severity=ATTENTION")
        assert res_sev.status_code == 200
        data_s = res_sev.json()
        for item in data_s["insights"]:
            assert item["severity"] == "ATTENTION"

        # 4. Metric type filter
        res_type = client.get("/api/insights?metric_type=electricity_consumption")
        assert res_type.status_code == 200
        data_t = res_type.json()
        for item in data_t["insights"]:
            assert item["metric_type"] == "electricity_consumption"

    finally:
        app.dependency_overrides.clear()

def test_k_not_applicable_never_marked_missing(test_db):
    """Test K: A metric never previously reported for a company is not marked MISSING_DATA."""
    # Company reports only Electricity in Oct and Nov. Water was never reported.
    m1 = SustainabilityMetric(
        document_id=1,
        company_name="Acme Corp",
        metric_type="electricity_consumption",
        category="energy",
        value=1000.0,
        unit="kWh",
        period_start="October 2024",
        source_field="energy.electricity_kwh"
    )
    m2 = SustainabilityMetric(
        document_id=2,
        company_name="Acme Corp",
        metric_type="electricity_consumption",
        category="energy",
        value=1050.0,
        unit="kWh",
        period_start="November 2024",
        source_field="energy.electricity_kwh"
    )
    test_db.add_all([m1, m2])
    test_db.commit()

    service = InsightsService()
    insights = service.generate_metric_insights(test_db, company="Acme Corp")

    # Water or Fuel must NOT appear as missing data
    missing_insights = [i for i in insights if i.category == "MISSING_DATA"]
    assert len(missing_insights) == 0

def test_l_missing_month_no_fabrication_no_three_period_trend(test_db):
    """Test L: October + December only. Do not fabricate November, do not generate a three-period trend."""
    m1 = SustainabilityMetric(
        document_id=1,
        company_name="Acme Corp",
        metric_type="electricity_consumption",
        category="energy",
        value=1000.0,
        unit="kWh",
        period_start="October 2024",
        source_field="energy.electricity_kwh"
    )
    m2 = SustainabilityMetric(
        document_id=2,
        company_name="Acme Corp",
        metric_type="electricity_consumption",
        category="energy",
        value=1100.0,
        unit="kWh",
        period_start="December 2024",
        source_field="energy.electricity_kwh"
    )
    test_db.add_all([m1, m2])
    test_db.commit()

    service = InsightsService()
    insights = service.generate_metric_insights(test_db, company="Acme Corp")

    trends = [i for i in insights if i.category == "TREND"]
    assert len(trends) == 0
