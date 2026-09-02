import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database.base import Base
from backend.app.models.document import Document
from backend.app.models.sustainability_metric import SustainabilityMetric
from backend.app.services.copilot_context import classify_intent, copilot_context_service
from backend.app.services.copilot_service import copilot_service
from backend.app.services.llm_service import LLMService


@pytest.fixture
def mock_emissions_db():
    """Isolated in-memory test database seeded with real MSME invoice emissions data."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()

    doc = Document(
        id=1,
        filename="msme_test_invoice.pdf",
        original_filename="msme_test_invoice.pdf",
        file_path="uploads/msme_test_invoice.pdf",
        document_type="Electricity Bill",
        file_size=24780,
        status="COMPLETED",
        review_status="COMPLETED",
        quality_score=100.0,
        reporting_period="2024-10-01 to 2024-10-31",
        total_energy_kwh=48750.0,
        total_emissions_tco2e=33.01,
        structured_data={
            "document_type": "Electricity Bill",
            "company": {"name": "TARA ENGINEERING WORKS"},
            "period": {"billing_month": "October 2024"},
            "energy": {
                "electricity_kwh": 48750.0,
                "peak_demand_kva_kw": 128.5,
                "power_factor": 0.96,
                "fuel_diesel_liters": 420.0,
            },
            "carbon_emissions": {
                "scope_1_direct_tco2e": 1.13,
                "scope_2_indirect_tco2e": 31.88,
                "total_ghg_emissions_tco2e": 33.01,
            },
            "evidence": [
                {
                    "field": "scope_1_direct_tco2e",
                    "value": 1.13,
                    "unit": "tCO2e",
                    "confidence": 0.98,
                    "confidence_level": "HIGH",
                    "source_text": "Scope 1 GHG Emissions 1.13 tCO2e",
                },
                {
                    "field": "scope_2_indirect_tco2e",
                    "value": 31.88,
                    "unit": "tCO2e",
                    "confidence": 0.98,
                    "confidence_level": "HIGH",
                    "source_text": "Scope 2 GHG Emissions 31.88 tCO2e",
                },
                {
                    "field": "total_ghg_emissions_tco2e",
                    "value": 33.01,
                    "unit": "tCO2e",
                    "confidence": 0.98,
                    "confidence_level": "HIGH",
                    "source_text": "Total GHG Emissions 33.01 tCO2e",
                },
            ],
        },
    )
    db.add(doc)

    metrics = [
        SustainabilityMetric(
            document_id=1,
            metric_type="electricity_consumption",
            category="energy",
            value=48750.0,
            unit="kWh",
            source_field="electricity_kwh",
            source_text="Total Active Energy Consumption 48,750.00 kWh",
        ),
        SustainabilityMetric(
            document_id=1,
            metric_type="peak_demand",
            category="energy",
            value=128.5,
            unit="kVA",
            source_field="peak_demand_kva_kw",
            source_text="Recorded Peak Demand 128.50 kVA",
        ),
        SustainabilityMetric(
            document_id=1,
            metric_type="fuel_consumption",
            category="energy",
            value=420.0,
            unit="Liters",
            source_field="fuel_diesel_liters",
            source_text="Diesel Generator Fuel Used 420.00 Liters",
        ),
        SustainabilityMetric(
            document_id=1,
            metric_type="scope_1_emissions",
            category="carbon",
            value=1.13,
            unit="tCO2e",
            source_field="scope_1_direct_tco2e",
            source_text="Scope 1 GHG Emissions 1.13 tCO2e",
        ),
        SustainabilityMetric(
            document_id=1,
            metric_type="scope_2_emissions",
            category="carbon",
            value=31.88,
            unit="tCO2e",
            source_field="scope_2_indirect_tco2e",
            source_text="Scope 2 GHG Emissions 31.88 tCO2e",
        ),
        SustainabilityMetric(
            document_id=1,
            metric_type="total_ghg_emissions",
            category="carbon",
            value=33.01,
            unit="tCO2e",
            source_field="total_ghg_emissions_tco2e",
            source_text="Total GHG Emissions 33.01 tCO2e",
        ),
    ]
    for m in metrics:
        db.add(m)

    db.commit()
    yield db
    db.close()


def test_metric_mapping_heuristic_extraction():
    """A. Verify extraction heuristic correctly maps Scope 1, Scope 2, and Total GHG."""
    raw_text = """--- PAGE 1 ---
TARA ENGINEERING WORKS
Environmental Information
Metric Value Unit
Scope 1 GHG Emissions
1.13
tCO2e
Scope 2 GHG Emissions
31.88
tCO2e
Total GHG Emissions
33.01
tCO2e"""

    llm = LLMService()
    extraction = llm._heuristic_fallback_extraction(raw_text, extraction_method="pymupdf")
    carbon = extraction["carbon_emissions"]

    assert carbon["scope_1_direct_tco2e"] == 1.13
    assert carbon["scope_2_indirect_tco2e"] == 31.88
    assert carbon["total_ghg_emissions_tco2e"] == 33.01


def test_metric_mapping_in_copilot_database(mock_emissions_db):
    """A. Verify metrics are correctly associated in database and context."""
    metrics = mock_emissions_db.query(SustainabilityMetric).filter(SustainabilityMetric.category == "carbon").all()
    m_dict = {m.metric_type: m.value for m in metrics}

    assert m_dict["scope_1_emissions"] == 1.13
    assert m_dict["scope_2_emissions"] == 31.88
    assert m_dict["total_ghg_emissions"] == 33.01


def test_reduction_question_routing():
    """B. Verify all variations of emissions reduction questions route to ACTION_RECOMMENDATION."""
    queries = [
        "how can i reduce my carbon emission",
        "how can I reduce emissions",
        "what can I do to lower my carbon footprint",
        "how can we reduce our GHG emissions",
        "where should I focus to reduce emissions",
        "what should I do to reduce carbon emissions",
        "how to reduce emissions",
        "where to focus to reduce carbon footprint",
        "Can I reduce emissions by 20%?",
    ]
    for q in queries:
        assert classify_intent(q) == "ACTION_RECOMMENDATION", f"Failed for query: {q}"


def test_recommendation_response_structure(mock_emissions_db):
    """C. Verify response contains WHAT, WHY, WHAT NEXT, SOURCE sections with correct numbers."""
    res = copilot_service.chat(mock_emissions_db, "how can i reduce my carbon emission")

    assert res.intent == "ACTION_RECOMMENDATION"
    answer = res.answer

    # Assert required structural headers
    assert "**WHAT:**" in answer
    assert "**WHY:**" in answer
    assert "**WHAT NEXT:**" in answer
    assert "**SOURCE:**" in answer

    # Assert accurate metric values
    assert "1.13 tCO2e" in answer
    assert "31.88 tCO2e" in answer
    assert "33.01 tCO2e" in answer

    # Assert Scope 2 dominance focus
    assert "Electricity-related emissions" in answer or "Scope 2" in answer


def test_no_invented_savings(mock_emissions_db):
    """D. Verify speculative percentage claims like 20% are rejected and not invented."""
    res = copilot_service.chat(mock_emissions_db, "Can I reduce emissions by 20%?")

    assert res.intent == "ACTION_RECOMMENDATION"
    answer = res.answer

    # Must NOT claim that an action reduces emissions by 20%
    assert "will reduce emissions by 20%" not in answer.lower()
    assert "guaranteed" not in answer.lower()
    assert "do not have verified calculations" in answer.lower() or "not enough verified engineering" in answer.lower() or "models" in answer.lower()


def test_no_invented_causality(mock_emissions_db):
    """E. Verify response uses cautious, grounded operational language."""
    res = copilot_service.chat(mock_emissions_db, "how can i reduce my carbon emission")
    answer = res.answer.lower()

    # Must NOT invent unsupported causal claims
    assert "your emissions are high because" not in answer
    assert "the generator caused" not in answer
    assert "installing solar will reduce emissions by" not in answer
    assert "you can save ₹" not in answer


def test_source_integrity(mock_emissions_db):
    """F. Verify every returned source maps to a real context document and metric."""
    res = copilot_service.chat(mock_emissions_db, "how can i reduce my carbon emission")

    assert len(res.sources) > 0
    valid_doc_ids = {d.id for d in mock_emissions_db.query(Document).all()}

    for src in res.sources:
        assert src.document_id in valid_doc_ids
        assert src.document_name == "msme_test_invoice.pdf"
        assert src.source_text is not None


def test_metric_queries_accuracy(mock_emissions_db):
    """Verify standard metric lookups return exact figures and do not confuse electricity with fuel."""
    res_peak = copilot_service.chat(mock_emissions_db, "What is the peak demand?")
    assert "128.5 kVA" in res_peak.answer

    res_elec = copilot_service.chat(mock_emissions_db, "What electricity consumption is reported?")
    assert "48,750 kWh" in res_elec.answer
    assert "Fuel Consumption" not in res_elec.answer
