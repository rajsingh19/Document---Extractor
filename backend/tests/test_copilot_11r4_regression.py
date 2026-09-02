import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.session import SessionLocal
from backend.app.models.sustainability_metric import SustainabilityMetric

client = TestClient(app)

def test_document1_has_no_water_metric():
    """Verify Document #1 contains zero water metrics."""
    with SessionLocal() as db:
        water_metrics = db.query(SustainabilityMetric).filter(
            SustainabilityMetric.document_id == 1,
            SustainabilityMetric.metric_type.in_(["water_consumption", "freshwater", "recycled_water"])
        ).all()
        assert len(water_metrics) == 0

def test_document1_has_no_waste_metric():
    """Verify Document #1 contains zero waste metrics."""
    with SessionLocal() as db:
        waste_metrics = db.query(SustainabilityMetric).filter(
            SustainabilityMetric.document_id == 1,
            SustainabilityMetric.metric_type.like("%waste%")
        ).all()
        assert len(waste_metrics) == 0

def test_document1_diesel_is_420():
    """Verify Document #1 diesel fuel is exactly 420 L."""
    with SessionLocal() as db:
        fuel = db.query(SustainabilityMetric).filter(
            SustainabilityMetric.document_id == 1,
            SustainabilityMetric.metric_type == "fuel_consumption"
        ).first()
        assert fuel is not None
        assert fuel.value == 420.0
        assert fuel.unit == "Liters"

def test_document1_power_factor_is_096():
    """Verify Document #1 power factor is 0.96."""
    res = client.post("/api/copilot/chat", json={"document_id": 1, "message": "What is the power factor?"})
    assert res.status_code == 200
    assert "0.96" in res.json()["answer"]

def test_document1_solar_is_3850():
    """Verify Document #1 rooftop solar returns 3,850 kWh."""
    res = client.post("/api/copilot/chat", json={"document_id": 1, "message": "How much rooftop solar electricity was generated?"})
    assert res.status_code == 200
    assert "3,850" in res.json()["answer"] or "3850" in res.json()["answer"]

def test_document1_grid_electricity_is_44900():
    """Verify Document #1 grid electricity returns 44,900 kWh."""
    res = client.post("/api/copilot/chat", json={"document_id": 1, "message": "How much electricity did we purchase from the grid?"})
    assert res.status_code == 200
    assert "44,900" in res.json()["answer"] or "44900" in res.json()["answer"]

def test_natural_gas_query_returns_unavailable():
    """Verify natural gas query states data is not present."""
    res = client.post("/api/copilot/chat", json={"document_id": 1, "message": "What is our natural gas consumption?"})
    assert res.status_code == 200
    ans = res.json()["answer"].lower()
    assert "not present" in ans or "not available" in ans or "not contain" in ans

def test_temporal_query_january_2025_returns_unavailable():
    """Verify January 2025 electricity query states data is unavailable."""
    res = client.post("/api/copilot/chat", json={"document_id": 1, "message": "What was our electricity consumption in January 2025?"})
    assert res.status_code == 200
    ans = res.json()["answer"].lower()
    assert "not available" in ans or "october 2024" in ans

def test_metadata_query_company_location():
    """Verify company location returns Kanpur, Uttar Pradesh."""
    res = client.post("/api/copilot/chat", json={"document_id": 1, "message": "Where is the company located?"})
    assert res.status_code == 200
    ans = res.json()["answer"]
    assert "Kanpur" in ans and "Uttar Pradesh" in ans

def test_metadata_query_invoice_amount():
    """Verify total invoice amount returns ₹453,169.56."""
    res = client.post("/api/copilot/chat", json={"document_id": 1, "message": "What is the total invoice amount?"})
    assert res.status_code == 200
    ans = res.json()["answer"]
    assert "453,169.56" in ans

def test_recommendations_do_not_propose_water():
    """Verify recommendations for Document #1 never propose water actions."""
    res = client.post("/api/copilot/chat", json={"document_id": 1, "message": "What are the recommended actions to reduce our environmental impact?"})
    assert res.status_code == 200
    ans = res.json()["answer"].lower()
    assert "water" not in ans
    assert "31.88" in ans or "electricity" in ans

def test_peak_demand_followup_preserves_october_context():
    """Verify follow-up 'What was the peak demand during that period?' returns 128.5 kVA."""
    history = [
        {"role": "user", "content": "What reporting period does this electricity data belong to?"},
        {"role": "assistant", "content": "The electricity data belongs to the October 2024 reporting period."}
    ]
    res = client.post(
        "/api/copilot/chat",
        json={"document_id": 1, "message": "What was the peak demand during that period?", "history": history}
    )
    assert res.status_code == 200
    ans = res.json()["answer"]
    assert "128.5" in ans
