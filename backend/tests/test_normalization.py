import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.database.base import Base
from backend.app.models.document import Document
from backend.app.models.audit import AuditLog
from backend.app.models.sustainability_metric import SustainabilityMetric
from backend.app.services.normalization_service import NormalizationService
from backend.app.services.extraction_service import ExtractionPipelineService
from backend.app.utils.sample_generator import (
    generate_sample_electricity_bill,
    generate_sample_esg_audit_report,
    generate_sample_scanned_receipt_pdf,
    generate_sample_adversarial_invoice
)

@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test_norm.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    yield db
    db.close()

def test_normalization_complete_electricity_bill(test_db, tmp_path):
    pdf_path = str(tmp_path / "elec.pdf")
    generate_sample_electricity_bill(pdf_path)

    doc = Document(
        filename="elec.pdf",
        original_filename="elec.pdf",
        file_path=pdf_path,
        file_size=os.path.getsize(pdf_path),
        mime_type="application/pdf",
        status="PENDING"
    )
    test_db.add(doc)
    test_db.commit()
    test_db.refresh(doc)

    pipeline = ExtractionPipelineService()
    processed_doc = pipeline.process_document(test_db, doc.id, force_ocr=False)

    metrics = test_db.query(SustainabilityMetric).filter(SustainabilityMetric.document_id == doc.id).all()
    assert len(metrics) >= 4

    metric_types = {m.metric_type: m for m in metrics}
    assert "electricity_consumption" in metric_types
    elec_metric = metric_types["electricity_consumption"]
    assert elec_metric.value == 124500.0
    assert elec_metric.unit == "kWh"
    assert elec_metric.verification_status == "AI_EXTRACTED"
    assert elec_metric.source_field == "energy.electricity_kwh"
    assert elec_metric.source_text is not None

    assert "renewable_energy" in metric_types
    assert metric_types["renewable_energy"].value == 18200.0
    assert metric_types["renewable_energy"].unit == "kWh"

    assert "fuel_consumption" in metric_types
    assert metric_types["fuel_consumption"].value == 1250.0
    assert metric_types["fuel_consumption"].unit in ["Liters", "L"]

    assert "scope_1_emissions" in metric_types
    assert metric_types["scope_1_emissions"].value == 3.35
    assert metric_types["scope_1_emissions"].unit == "tCO2e"

    assert "scope_2_emissions" in metric_types
    assert metric_types["scope_2_emissions"].value == 75.47
    assert metric_types["scope_2_emissions"].unit == "tCO2e"

    assert "energy_cost" in metric_types
    assert metric_types["energy_cost"].value == 1005948.94

    # Crucial Rule: Null fields (water and waste) MUST NOT generate metrics!
    assert "water_consumption" not in metric_types
    assert "hazardous_waste" not in metric_types

def test_normalization_human_correction_override(test_db):
    doc = Document(
        filename="manual.pdf",
        original_filename="manual.pdf",
        file_path="/tmp/fake.pdf",
        file_size=1000,
        mime_type="application/pdf",
        status="COMPLETED",
        review_status="VERIFIED",
        company_name="Acme Corp",
        reporting_period="October 2024",
        structured_data={
            "company": {"name": "Acme Corp"},
            "period": {"billing_month": "October 2024"},
            "energy": {"electricity_kwh": 124500.0},
            "evidence": [
                {
                    "field": "electricity_kwh",
                    "value": 124500.0,
                    "unit": "kWh",
                    "source_text": "Active Energy 124,500 kWh",
                    "confidence": 0.95
                }
            ]
        },
        field_corrections={
            "electricity_kwh": {
                "original_ai_value": 124500.0,
                "corrected_value": 124050.0,
                "unit": "kWh",
                "is_verified": True
            }
        }
    )
    test_db.add(doc)
    test_db.commit()
    test_db.refresh(doc)

    norm_service = NormalizationService()
    metrics = norm_service.normalize_extraction(test_db, doc)

    assert len(metrics) == 1
    m = metrics[0]
    assert m.metric_type == "electricity_consumption"
    # MUST use the corrected value, not the original AI value!
    assert m.value == 124050.0
    assert m.unit == "kWh"
    assert m.verification_status == "HUMAN_VERIFIED"
    assert m.source_text == "Active Energy 124,500 kWh"

def test_normalization_adversarial_invoice_distinct_units(test_db, tmp_path):
    pdf_path = str(tmp_path / "adv.pdf")
    generate_sample_adversarial_invoice(pdf_path)

    doc = Document(
        filename="adv.pdf",
        original_filename="adv.pdf",
        file_path=pdf_path,
        file_size=os.path.getsize(pdf_path),
        mime_type="application/pdf",
        status="PENDING"
    )
    test_db.add(doc)
    test_db.commit()
    test_db.refresh(doc)

    pipeline = ExtractionPipelineService()
    processed_doc = pipeline.process_document(test_db, doc.id, force_ocr=False)

    metrics = test_db.query(SustainabilityMetric).filter(SustainabilityMetric.document_id == doc.id).all()
    metric_types = {m.metric_type: m for m in metrics}

    # Verify: ₹100,000 (cost) != 100,000 kWh (energy) != 1,000 L (fuel)
    assert "electricity_consumption" in metric_types
    assert metric_types["electricity_consumption"].value == 100000.0
    assert metric_types["electricity_consumption"].unit == "kWh"

    assert "fuel_consumption" in metric_types
    assert metric_types["fuel_consumption"].value == 1000.0
    assert metric_types["fuel_consumption"].unit == "Liters"

    assert "energy_cost" in metric_types
    assert metric_types["energy_cost"].value == 100000.0
    assert metric_types["energy_cost"].unit == "INR"

    # Zero hallucination on water and waste
    assert "water_consumption" not in metric_types
    assert "hazardous_waste" not in metric_types

def test_normalization_esg_audit_water_and_waste(test_db, tmp_path):
    pdf_path = str(tmp_path / "esg.pdf")
    generate_sample_esg_audit_report(pdf_path)

    doc = Document(
        filename="esg.pdf",
        original_filename="esg.pdf",
        file_path=pdf_path,
        file_size=os.path.getsize(pdf_path),
        mime_type="application/pdf",
        status="PENDING"
    )
    test_db.add(doc)
    test_db.commit()
    test_db.refresh(doc)

    pipeline = ExtractionPipelineService()
    processed_doc = pipeline.process_document(test_db, doc.id, force_ocr=False)

    metrics = test_db.query(SustainabilityMetric).filter(SustainabilityMetric.document_id == doc.id).all()
    metric_types = {m.metric_type: m for m in metrics}

    assert "water_consumption" in metric_types
    assert metric_types["water_consumption"].value == 42800.0
    assert metric_types["water_consumption"].unit == "kL"

    assert "recycled_water" in metric_types
    assert metric_types["recycled_water"].value == 36380.0

    assert "hazardous_waste" in metric_types
    assert metric_types["hazardous_waste"].value == 4200.0
    assert metric_types["hazardous_waste"].unit == "kg"
