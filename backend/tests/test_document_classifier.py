import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.database.base import Base
from backend.app.models.document import Document
from backend.app.models.audit import AuditLog
from backend.app.models.sustainability_metric import SustainabilityMetric
from backend.app.services.document_classifier import DocumentClassifier
from backend.app.services.extraction_service import ExtractionPipelineService
from backend.app.services.llm_service import LLMService
from backend.app.utils.sample_generator import (
    generate_sample_electricity_bill,
    generate_sample_esg_audit_report,
    generate_sample_scanned_receipt_pdf,
    generate_sample_adversarial_invoice
)

@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test_classifier.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    yield db
    db.close()

def test_electricity_bill_classification():
    classifier = DocumentClassifier()
    sample_text = """
    TARA ENGINEERING WORKS
    INDUSTRIAL ELECTRICITY BILL - MAHADISCOM
    Consumer No: 028549102482
    Billing Month: October 2024
    Sanctioned Load: 150 kVA
    Contract Demand: 125 kVA
    Meter Reading: Active Energy kWh: 48,750.00
    Peak Maximum Demand: 128.5 kVA
    Average Power Factor: 0.96 Lag
    Energy Charges Tariff Rate: Rs 7.80 per kWh
    Total Net Payable: INR 4,82,350.00
    """
    res = classifier.classify_document(sample_text)
    assert res.document_type == "Electricity Bill"
    assert res.confidence >= 0.85
    assert res.confidence_level == "HIGH"
    assert len(res.detected_signals) >= 3
    assert "Electricity consumption" in res.reasoning or "Electricity" in res.reasoning

def test_esg_audit_classification():
    classifier = DocumentClassifier()
    sample_text = """
    GREEN ECO TEXTILES PVT. LTD.
    ANNUAL ESG & SUSTAINABILITY AUDIT REPORT
    Reporting Period: 2023-04-01 to 2024-03-31
    Scope 1 Direct GHG Emissions: 110.76 tCO2e
    Scope 2 Indirect Purchased Electricity: 82.97 tCO2e
    Total Fresh Water Consumption: 42,800.00 kL
    Total Hazardous Waste Generated: 4,200.00 kg
    BRSR Compliance Score: 94.5%
    """
    res = classifier.classify_document(sample_text)
    assert res.document_type == "ESG Audit Report"
    assert res.confidence >= 0.85
    assert res.confidence_level == "HIGH"

def test_waste_manifest_classification():
    classifier = DocumentClassifier()
    sample_text = """
    FORM 10 - HAZARDOUS WASTE MANIFEST
    State Pollution Control Board Consignment Note
    Waste Generator: CUSTOMER Shree Balaji Polymers
    Transporter Vehicle No: MH-12-Q-4821
    Disposal Facility: Maharashtra TSDF Treatment Facility
    Waste Category: 5.1 Spent Solvent Residue
    Net Weight: 466.50 kg
    """
    res = classifier.classify_document(sample_text)
    assert res.document_type == "Waste Manifest"
    assert res.confidence >= 0.85
    assert res.confidence_level == "HIGH"

def test_commercial_invoice_classification():
    classifier = DocumentClassifier()
    sample_text = """
    TAX INVOICE - COMMERCIAL SALES
    Invoice No: INV-2024-9482
    GSTIN: 27AABCT3920M1Z8
    Buyer: Bharat Heavy Engineering Pvt. Ltd.
    HSN/SAC: 84834000
    CGST @ 9%: INR 9,000.00
    SGST @ 9%: INR 9,000.00
    Total Taxable Value: INR 1,00,000.00
    Total Invoice Value Payable: INR 1,18,000.00
    """
    res = classifier.classify_document(sample_text)
    assert res.document_type == "Commercial Invoice"
    assert res.confidence >= 0.85

def test_unknown_document_classification():
    classifier = DocumentClassifier()
    # Random generic text without sustainability/utility indicators
    sample_text = """
    Meeting Notes
    Discussed team sprint planning for quarterly software roadmap.
    Action items: complete task backlog by Friday.
    """
    res = classifier.classify_document(sample_text)
    assert res.document_type == "Unknown / Other"
    assert res.confidence <= 0.50
    assert res.confidence_level == "LOW"

def test_heuristic_fallback_and_confidence():
    classifier = DocumentClassifier(llm_service=None)
    # 2 signals -> MEDIUM confidence
    sample_text = "Diesel fuel delivery voucher. Total fuel supplied: 1250 Liters."
    res = classifier.classify_document(sample_text)
    assert res.document_type == "Fuel Receipt"
    assert res.confidence_level in ["MEDIUM", "HIGH"]

def test_ambiguous_document_dominant_purpose():
    classifier = DocumentClassifier()
    # Invoice format containing electricity utility sub-items
    sample_text = """
    TAX INVOICE / ELECTRICITY WHEELING CHARGES
    GSTIN: 27ABCDE1234F1Z5
    Active Energy kWh Consumption: 100,000 kWh
    Peak Demand: 250 kVA
    Power Factor: 0.98
    Net Total Payable Amount: INR 1,00,000.00
    """
    res = classifier.classify_document(sample_text)
    # Dominant operational utility purpose is Electricity Bill
    assert res.document_type == "Electricity Bill"

def test_human_classification_correction_pipeline(test_db, tmp_path):
    pdf_path = str(tmp_path / "invoice.pdf")
    generate_sample_adversarial_invoice(pdf_path)

    doc = Document(
        filename="invoice.pdf",
        original_filename="invoice.pdf",
        file_path=pdf_path,
        file_size=os.path.getsize(pdf_path),
        mime_type="application/pdf",
        status="PENDING"
    )
    test_db.add(doc)
    test_db.commit()
    test_db.refresh(doc)

    pipeline = ExtractionPipelineService()
    processed_doc = pipeline.process_document(test_db, doc.id)

    assert processed_doc.classification is not None
    orig_type = processed_doc.document_type

    # Human reviewer corrects classification to Electricity Bill
    old_type = processed_doc.document_type
    new_type = "Electricity Bill"
    processed_doc.document_type = new_type
    
    classification = dict(processed_doc.classification or {})
    classification["document_type"] = new_type
    classification["classification_method"] = "human"
    classification["conflict"] = False
    processed_doc.classification = classification

    audit_entry = AuditLog(
        document_id=processed_doc.id,
        field_name="classification",
        original_ai_value=old_type,
        corrected_value=new_type,
        action="classification_change",
        notes="Human reviewer verified as Electricity Bill"
    )
    test_db.add(audit_entry)
    test_db.commit()
    test_db.refresh(processed_doc)

    # Verify audit trail records the change
    audit_logs = test_db.query(AuditLog).filter(
        AuditLog.document_id == processed_doc.id,
        AuditLog.action == "classification_change"
    ).all()
    assert len(audit_logs) >= 1
    assert audit_logs[0].original_ai_value == old_type
    assert audit_logs[0].corrected_value == new_type
    assert processed_doc.classification["classification_method"] == "human"
