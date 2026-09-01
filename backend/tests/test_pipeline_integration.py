import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.database.base import Base
from backend.app.models.document import Document
from backend.app.models.audit import AuditLog
from backend.app.services.extraction_service import ExtractionPipelineService
from backend.app.utils.sample_generator import (
    generate_sample_electricity_bill,
    generate_sample_esg_audit_report,
    generate_sample_scanned_receipt_pdf,
    generate_sample_adversarial_invoice
)

@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    yield db
    db.close()

def test_pipeline_sample_electricity_bill(test_db, tmp_path):
    pdf_path = str(tmp_path / "test_electricity.pdf")
    generate_sample_electricity_bill(pdf_path)
    
    doc = Document(
        filename="test_electricity.pdf",
        original_filename="test_electricity.pdf",
        file_path=pdf_path,
        file_size=os.path.getsize(pdf_path),
        mime_type="application/pdf",
        status="PENDING",
        review_status="NEEDS_REVIEW"
    )
    test_db.add(doc)
    test_db.commit()
    test_db.refresh(doc)
    
    pipeline = ExtractionPipelineService()
    processed_doc = pipeline.process_document(test_db, doc.id, force_ocr=False)
    
    assert processed_doc.status == "COMPLETED"
    assert processed_doc.document_type == "Electricity Bill"
    assert processed_doc.quality_score == 100.0
    assert processed_doc.review_status == "COMPLETED"
    
    summary = processed_doc.quality_summary
    assert summary["expected_fields_found"] == 4
    assert summary["expected_fields_missing"] == 0
    assert "water_consumption_kl" in summary["not_applicable_list"]
    assert "hazardous_waste_kg" in summary["not_applicable_list"]

def test_pipeline_sample_esg_audit(test_db, tmp_path):
    pdf_path = str(tmp_path / "test_esg.pdf")
    generate_sample_esg_audit_report(pdf_path)
    
    doc = Document(
        filename="test_esg.pdf",
        original_filename="test_esg.pdf",
        file_path=pdf_path,
        file_size=os.path.getsize(pdf_path),
        mime_type="application/pdf",
        status="PENDING",
        review_status="NEEDS_REVIEW"
    )
    test_db.add(doc)
    test_db.commit()
    test_db.refresh(doc)
    
    pipeline = ExtractionPipelineService()
    processed_doc = pipeline.process_document(test_db, doc.id, force_ocr=False)
    
    assert processed_doc.status == "COMPLETED"
    assert processed_doc.document_type == "ESG Audit Report"
    assert processed_doc.quality_score >= 95.0
    assert processed_doc.review_status == "COMPLETED"
    
    summary = processed_doc.quality_summary
    assert summary["expected_fields_missing"] == 0

def test_pipeline_sample_scanned_waste_manifest(test_db, tmp_path):
    pdf_path = str(tmp_path / "test_scanned.pdf")
    generate_sample_scanned_receipt_pdf(pdf_path)
    
    doc = Document(
        filename="test_scanned.pdf",
        original_filename="test_scanned.pdf",
        file_path=pdf_path,
        file_size=os.path.getsize(pdf_path),
        mime_type="application/pdf",
        status="PENDING",
        review_status="NEEDS_REVIEW"
    )
    test_db.add(doc)
    test_db.commit()
    test_db.refresh(doc)
    
    pipeline = ExtractionPipelineService()
    processed_doc = pipeline.process_document(test_db, doc.id, force_ocr=True)
    
    assert processed_doc.status == "COMPLETED"
    assert processed_doc.extraction_method == "ocr_fallback"
    assert processed_doc.review_status == "NEEDS_REVIEW"
    assert processed_doc.quality_score < 85.0
    
    summary = processed_doc.quality_summary
    assert summary["scoring_breakdown"]["ocr_penalty"] == 15.0

def test_pipeline_sample_adversarial_invoice(test_db, tmp_path):
    pdf_path = str(tmp_path / "test_adversarial.pdf")
    generate_sample_adversarial_invoice(pdf_path)
    
    doc = Document(
        filename="test_adversarial.pdf",
        original_filename="test_adversarial.pdf",
        file_path=pdf_path,
        file_size=os.path.getsize(pdf_path),
        mime_type="application/pdf",
        status="PENDING",
        review_status="NEEDS_REVIEW"
    )
    test_db.add(doc)
    test_db.commit()
    test_db.refresh(doc)
    
    pipeline = ExtractionPipelineService()
    processed_doc = pipeline.process_document(test_db, doc.id, force_ocr=False)
    
    assert processed_doc.status == "COMPLETED"
    assert processed_doc.total_energy_kwh == 100000.0
    assert processed_doc.total_water_kl is None  # strictly null, zero hallucination
    assert processed_doc.total_waste_kg is None  # strictly null
    
    summary = processed_doc.quality_summary
    # water and waste must not reduce score for commercial invoice
    assert "water_consumption_kl" in summary["not_applicable_list"]
    assert "hazardous_waste_kg" in summary["not_applicable_list"]
