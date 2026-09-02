import os
import shutil
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.database.session import SessionLocal
from backend.app.models.document import Document
from backend.app.models.sustainability_metric import SustainabilityMetric
from backend.app.services.copilot_rag import copilot_hybrid_retriever
from backend.app.services.extraction_service import ExtractionPipelineService

client = TestClient(app)

MSME_PDF_PATH = "/home/raj/Downloads/msme_test_invoice.pdf"


def test_msme_invoice_upload_and_extraction():
    """Verify msme_test_invoice.pdf can be uploaded and extracted without 500 errors."""
    assert os.path.exists(MSME_PDF_PATH), f"File not found: {MSME_PDF_PATH}"

    with open(MSME_PDF_PATH, "rb") as f:
        pdf_bytes = f.read()

    response = client.post(
        "/api/documents/upload",
        files={"file": ("msme_test_invoice.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code in (200, 201), f"Upload failed with {response.status_code}: {response.text}"
    data = response.json()

    assert data.get("company_name") == "TARA ENGINEERING WORKS"
    assert data.get("document_type") == "Electricity Bill"
    assert data.get("total_energy_kwh") == 48750.0
    assert data.get("total_emissions_tco2e") == 33.01
    assert data.get("status") == "COMPLETED"


def test_msme_invoice_duplicate_detection():
    """Verify uploading an already-processed document returns duplicate status gracefully with HTTP 200."""
    with open(MSME_PDF_PATH, "rb") as f:
        pdf_bytes = f.read()

    response = client.post(
        "/api/documents/upload",
        files={"file": ("msme_test_invoice.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data.get("duplicate") is True
    assert "existing_document_id" in data
    assert data.get("company_name") == "TARA ENGINEERING WORKS"


def test_fresh_msme_invoice_upload_normalizes_metrics(tmp_path):
    """Verify a fresh MSME invoice upload creates normalized SustainabilityMetric records."""
    db = SessionLocal()
    try:
        with open(MSME_PDF_PATH, "rb") as f:
            pdf_bytes = f.read()

        # Add a unique comment to ensure unique hash for fresh pipeline run
        unique_bytes = pdf_bytes + f"\n%regression_test_{tmp_path.name}\n".encode()

        response = client.post(
            "/api/documents/upload",
            files={"file": (f"msme_test_{tmp_path.name}.pdf", unique_bytes, "application/pdf")},
        )
        assert response.status_code == 201, f"Expected 201 Created, got {response.status_code}: {response.text}"
        doc_data = response.json()
        doc_id = doc_data["id"]

        # Verify normalized metrics exist in DB
        metrics = db.query(SustainabilityMetric).filter(SustainabilityMetric.document_id == doc_id).all()
        m_map = {m.metric_type: m.value for m in metrics}

        assert "electricity_consumption" in m_map
        assert m_map["electricity_consumption"] == 48750.0
        assert m_map.get("scope_1_emissions") == 1.13
        assert m_map.get("scope_2_emissions") == 31.88
        assert m_map.get("total_ghg_emissions") == 33.01
        assert m_map.get("peak_demand") == 128.5

        # Clean up the test document
        test_doc = db.query(Document).filter(Document.id == doc_id).first()
        if test_doc:
            if os.path.exists(test_doc.file_path):
                try:
                    os.remove(test_doc.file_path)
                except OSError:
                    pass
            db.delete(test_doc)
            db.commit()
    finally:
        db.close()


def test_copilot_rag_with_msme_invoice():
    """Verify Copilot RAG retriever grounds correctly on the uploaded MSME document."""
    db = SessionLocal()
    try:
        # Document 1 is Tara Engineering Works MSME invoice in the canonical DB
        ctx = copilot_hybrid_retriever.retrieve(db, "What is the peak demand?", document_id=1)
        assert len(ctx.rag_metrics) > 0
        peak = ctx.rag_metrics[0]
        assert peak.metric_type == "peak_demand"
        assert peak.value == 128.5

        ctx_elec = copilot_hybrid_retriever.retrieve(db, "What electricity consumption is reported?", document_id=1)
        assert len(ctx_elec.rag_metrics) > 0
        assert ctx_elec.rag_metrics[0].value == 48750.0

        ctx_emiss = copilot_hybrid_retriever.retrieve(db, "How can I reduce my carbon emission?", document_id=1)
        emiss_map = {m.metric_type: m.value for m in ctx_emiss.rag_metrics}
        assert emiss_map.get("scope_1_emissions") == 1.13
        assert emiss_map.get("scope_2_emissions") == 31.88
    finally:
        db.close()


def test_pipeline_missing_file_clean_failure(tmp_path):
    """Verify that a missing file on disk fails cleanly without session corruption."""
    db = SessionLocal()
    try:
        doc = Document(
            filename="nonexistent.pdf",
            original_filename="nonexistent.pdf",
            file_path="/tmp/definitely_non_existent_file_12345.pdf",
            file_size=100,
            mime_type="application/pdf",
            status="PENDING",
            review_status="NEEDS_REVIEW"
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        pipeline = ExtractionPipelineService()
        result = pipeline.process_document(db, doc.id)

        assert result.status == "FAILED"
        assert "File not found" in result.error_message

        # Clean up
        db.delete(result)
        db.commit()
    finally:
        db.close()
