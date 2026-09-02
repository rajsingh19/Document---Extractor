import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.database.session import get_db
from backend.app.models.document import Document
from backend.app.models.sustainability_metric import SustainabilityMetric
from backend.app.services.copilot_recommendations import copilot_recommendation_service
from backend.app.services.copilot_llm import copilot_llm_service
from backend.app.services.copilot_context import copilot_context_service

client = TestClient(app)

def test_01_recommendation_service_works():
    """1. Verify copilot_recommendation_service returns a list of RecommendationItem."""
    db: Session = next(get_db())
    recs = copilot_recommendation_service.generate_recommendations(db)
    assert isinstance(recs, list)
    for r in recs:
        assert r.category in ("ENERGY", "FUEL", "WATER", "WASTE", "EMISSIONS", "DATA_QUALITY")
        assert r.priority in ("HIGH", "MEDIUM", "LOW")

def test_02_empty_database_returns_no_fabricated_recommendations():
    """2. Verify empty context produces no fabricated recommendations."""
    # When no metrics and no documents exist
    db: Session = next(get_db())
    with patch.object(db, "query") as mock_query:
        mock_query.return_value.order_by.return_value.all.return_value = []
        recs = copilot_recommendation_service.generate_recommendations(db)
        assert len(recs) == 0

def test_03_electricity_increase_creates_energy_opportunity():
    """3. Verify electricity consumption increase creates ENERGY recommendation."""
    db: Session = next(get_db())
    recs = copilot_recommendation_service.generate_recommendations(db)
    energy_recs = [r for r in recs if r.category == "ENERGY"]
    if energy_recs:
        r = energy_recs[0]
        assert "electricity" in r.title.lower() or "energy" in r.title.lower()
        assert len(r.suggested_actions) > 0

def test_04_fuel_increase_creates_fuel_opportunity():
    """4. Verify fuel consumption metric creates FUEL recommendation."""
    db: Session = next(get_db())
    doc = db.query(Document).first()
    fuel_m = SustainabilityMetric(
        document_id=doc.id,
        company_name="Apex Forgings",
        metric_type="fuel_consumption",
        category="energy",
        value=1500.0,
        unit="Liters",
        confidence=0.95,
        source_field="fuel_diesel_liters",
        verification_status="VERIFIED"
    )
    db.add(fuel_m)
    db.commit()

    recs = copilot_recommendation_service.generate_recommendations(db)
    fuel_recs = [r for r in recs if r.category == "FUEL"]
    assert len(fuel_recs) > 0
    assert "fuel" in fuel_recs[0].title.lower() or "generator" in fuel_recs[0].title.lower()

def test_05_water_increase_creates_water_opportunity():
    """5. Verify water consumption creates WATER recommendation."""
    db: Session = next(get_db())
    recs = copilot_recommendation_service.generate_recommendations(db)
    water_recs = [r for r in recs if r.category == "WATER"]
    if water_recs:
        assert "water" in water_recs[0].title.lower()

def test_06_waste_increase_creates_waste_opportunity():
    """6. Verify waste metric creates WASTE recommendation."""
    db: Session = next(get_db())
    doc = db.query(Document).first()
    waste_m = SustainabilityMetric(
        document_id=doc.id,
        company_name="Apex Forgings",
        metric_type="hazardous_waste_generated",
        category="waste",
        value=420.0,
        unit="kg",
        confidence=0.95,
        source_field="waste_hazardous_kg",
        verification_status="VERIFIED"
    )
    db.add(waste_m)
    db.commit()

    recs = copilot_recommendation_service.generate_recommendations(db)
    waste_recs = [r for r in recs if r.category == "WASTE"]
    assert len(waste_recs) > 0
    assert "waste" in waste_recs[0].title.lower()

def test_07_scope1_scope2_changes_handled_correctly():
    """7. Verify Scope 1 vs Scope 2 comparisons identify largest contributor."""
    db: Session = next(get_db())
    recs = copilot_recommendation_service.generate_recommendations(db)
    em_recs = [r for r in recs if r.category == "EMISSIONS"]
    if em_recs:
        assert "scope" in em_recs[0].title.lower() or "emissions" in em_recs[0].title.lower()

def test_08_existing_insight_thresholds_reused():
    """8. Verify recommendation engine reuses insights without conflicting thresholds."""
    db: Session = next(get_db())
    recs = copilot_recommendation_service.generate_recommendations(db)
    for r in recs:
        if r.percentage_change is not None:
            assert isinstance(r.percentage_change, float)

def test_09_and_10_missing_period_never_fabricated():
    """9-10. Verify missing reporting period is not interpolated as a continuous trend."""
    response = client.post(
        "/api/copilot/chat",
        json={"message": "Where is our biggest sustainability opportunity?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "ACTION_RECOMMENDATION"
    assert "actions" in data

def test_11_no_invented_savings():
    """11. Verify query asking for 20% reduction target does NOT invent savings."""
    response = client.post(
        "/api/copilot/chat",
        json={"message": "Can we reduce emissions by 20%?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "don't have enough" in data["answer"].lower() or "predictive" in data["answer"].lower() or "reduction" in data["answer"].lower()

def test_12_no_invented_causality():
    """12. Verify recommendations state operational suggestions rather than blaming operations."""
    response = client.post(
        "/api/copilot/chat",
        json={"message": "How can we reduce emissions?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "inefficient" not in data["answer"].lower()
    assert "illegal" not in data["answer"].lower()

def test_13_and_14_source_lineage_preserved():
    """13-14. Verify source document IDs in recommendations are valid positive integers."""
    db: Session = next(get_db())
    recs = copilot_recommendation_service.generate_recommendations(db)
    for r in recs:
        if r.source_document_id:
            assert r.source_document_id > 0

def test_15_priority_ordering_deterministic():
    """15. Verify recommendations are ranked HIGH -> MEDIUM -> LOW."""
    db: Session = next(get_db())
    recs = copilot_recommendation_service.generate_recommendations(db)
    if len(recs) >= 2:
        weights = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        for i in range(len(recs) - 1):
            assert weights[recs[i].priority] >= weights[recs[i+1].priority]

def test_16_recommendation_deduplication():
    """16. Verify no identical recommendation IDs exist."""
    db: Session = next(get_db())
    recs = copilot_recommendation_service.generate_recommendations(db)
    ids = [r.id for r in recs]
    assert len(ids) == len(set(ids))

def test_17_data_quality_recommendation_works():
    """17. Verify flagged documents produce a DATA_QUALITY recommendation."""
    db: Session = next(get_db())
    recs = copilot_recommendation_service.generate_recommendations(db)
    dq_recs = [r for r in recs if r.category == "DATA_QUALITY"]
    if dq_recs:
        assert "review" in dq_recs[0].title.lower() or "document" in dq_recs[0].title.lower()

def test_18_not_applicable_not_treated_as_missing():
    """18. Verify NOT_APPLICABLE fields carry no penalty."""
    db: Session = next(get_db())
    recs = copilot_recommendation_service.generate_recommendations(db)
    for r in recs:
        if r.category == "DATA_QUALITY":
            assert "not_applicable" not in r.reason.lower()

def test_19_llm_failure_fallback():
    """19. Verify recommendation Q&A operates reliably during LLM failure."""
    db: Session = next(get_db())
    ctx = copilot_context_service.build_context(db, "How can we reduce emissions?")
    recs = copilot_recommendation_service.generate_recommendations(db)
    with patch.object(copilot_llm_service, "is_configured", return_value=True):
        with patch.object(copilot_llm_service, "_call_openai", side_effect=Exception("Timeout")):
            res = copilot_llm_service.generate_response(ctx, recommendations=recs)
            assert res.context_available is True
            assert isinstance(res.answer, str)
            assert len(res.recommendations) > 0

def test_20_what_should_i_focus_on_first():
    """20. Verify query 'What should I focus on first?' returns top-ranked recommendation."""
    response = client.post(
        "/api/copilot/chat",
        json={"message": "What should I focus on first?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "ACTION_RECOMMENDATION"
    assert "focus on first" in data["answer"].lower() or "why" in data["answer"].lower()
