import os
import shutil
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, func

from backend.app.database.session import get_db
from backend.app.models.document import Document
from backend.app.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
    DashboardStatsResponse,
    ProcessDocumentRequest
)
from backend.app.services.extraction_service import ExtractionPipelineService
from backend.app.services.ocr_service import OCRService
from backend.app.services.llm_service import LLMService
from backend.app.utils.helpers import generate_unique_filename
from backend.app.utils.sample_generator import (
    generate_sample_electricity_bill,
    generate_sample_esg_audit_report,
    generate_sample_scanned_receipt_pdf
)

router = APIRouter(prefix="/api", tags=["Document AI"])
pipeline_service = ExtractionPipelineService()
llm_service = LLMService()

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get("/health")
def health_check():
    """System health and integration diagnostic check."""
    return {
        "status": "healthy",
        "service": "senseible-document-ai",
        "version": "1.0.0",
        "openai_configured": llm_service.is_configured(),
        "openai_model": llm_service.model,
        "ocr_available": OCRService.is_ocr_available()
    }

@router.post("/documents/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    auto_process: bool = Query(True, description="Automatically trigger extraction pipeline"),
    force_ocr: bool = Query(False, description="Force Tesseract OCR extraction"),
    db: Session = Depends(get_db)
):
    """
    Upload a PDF sustainability document and execute the AI extraction pipeline.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF documents are supported (.pdf)"
        )

    unique_filename = generate_unique_filename(file.filename)
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # Save uploaded file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_size = os.path.getsize(file_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file on disk: {str(e)}"
        )

    # Create initial document record
    doc = Document(
        filename=unique_filename,
        original_filename=file.filename,
        file_path=file_path,
        file_size=file_size,
        mime_type="application/pdf",
        status="PENDING"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Run extraction pipeline
    if auto_process:
        doc = pipeline_service.process_document(db, doc.id, force_ocr=force_ocr)

    return doc

@router.post("/documents/{document_id}/process", response_model=DocumentResponse)
def process_document(
    document_id: int,
    request: ProcessDocumentRequest = ProcessDocumentRequest(),
    db: Session = Depends(get_db)
):
    """
    Manually trigger or reprocess extraction pipeline for a given document.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    updated_doc = pipeline_service.process_document(db, doc.id, force_ocr=request.force_ocr)
    return updated_doc

@router.get("/documents", response_model=DocumentListResponse)
def list_documents(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    doc_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    List all uploaded sustainability documents with filtering and search.
    """
    query = db.query(Document)

    if status_filter:
        query = query.filter(Document.status == status_filter.upper())
    if doc_type:
        query = query.filter(Document.document_type == doc_type)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Document.original_filename.ilike(search_pattern),
                Document.company_name.ilike(search_pattern),
                Document.document_type.ilike(search_pattern)
            )
        )

    total = query.count()
    documents = query.order_by(desc(Document.created_at)).offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "documents": documents
    }

@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(document_id: int, db: Session = Depends(get_db)):
    """
    Get detailed extracted information for a specific document.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: int, db: Session = Depends(get_db)):
    """
    Delete a document and its stored PDF from disk.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove file from disk
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except OSError:
            pass

    db.delete(doc)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/documents/{document_id}/download-json")
def download_document_json(document_id: int, db: Session = Depends(get_db)):
    """
    Export structured extraction data as a downloadable JSON file.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not doc.structured_data:
        raise HTTPException(status_code=400, detail="Document has no structured data extracted yet")

    json_str = json.dumps(doc.structured_data, indent=2)
    filename = f"{os.path.splitext(doc.original_filename)[0]}_extracted.json"
    
    return Response(
        content=json_str,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    Get aggregated MSME sustainability and document processing statistics.
    """
    docs = db.query(Document).all()
    
    total = len(docs)
    processed = sum(1 for d in docs if d.status == "COMPLETED")
    pending = sum(1 for d in docs if d.status in ["PENDING", "EXTRACTING_TEXT", "RUNNING_LLM", "VALIDATING"])
    failed = sum(1 for d in docs if d.status == "FAILED")

    total_energy = sum((d.total_energy_kwh or 0) for d in docs if d.status == "COMPLETED")
    total_emissions = sum((d.total_emissions_tco2e or 0) for d in docs if d.status == "COMPLETED")
    total_water = sum((d.total_water_kl or 0) for d in docs if d.status == "COMPLETED")
    total_waste = sum((d.total_waste_kg or 0) for d in docs if d.status == "COMPLETED")

    # Group breakdowns
    doc_types = {}
    compliance = {}
    methods = {}

    for d in docs:
        if d.document_type:
            doc_types[d.document_type] = doc_types.get(d.document_type, 0) + 1
        if d.compliance_status:
            compliance[d.compliance_status] = compliance.get(d.compliance_status, 0) + 1
        if d.extraction_method:
            methods[d.extraction_method] = methods.get(d.extraction_method, 0) + 1

    return {
        "total_documents": total,
        "processed_count": processed,
        "pending_count": pending,
        "failed_count": failed,
        "total_energy_kwh": round(total_energy, 2),
        "total_emissions_tco2e": round(total_emissions, 2),
        "total_water_kl": round(total_water, 2),
        "total_waste_kg": round(total_waste, 2),
        "document_types_breakdown": doc_types,
        "compliance_breakdown": compliance,
        "extraction_methods_breakdown": methods
    }

@router.post("/documents/sample-seed", status_code=status.HTTP_201_CREATED)
def seed_sample_documents(
    sample_type: str = Query("electricity", description="electricity | esg | scanned"),
    db: Session = Depends(get_db)
):
    """
    Generate and process a realistic sample MSME sustainability PDF for immediate test/demo.
    - 'electricity': Clean text HT Industrial Electricity Bill (PyMuPDF extraction)
    - 'esg': Clean text MSME ESG Sustainability Audit Report (PyMuPDF extraction)
    - 'scanned': Scanned Fuel & Waste Manifest Image-PDF (Triggers Tesseract OCR Fallback!)
    """
    if sample_type == "electricity":
        orig_name = "Apex_Precision_Forgings_Electricity_Bill.pdf"
        unique_name = generate_unique_filename(orig_name)
        file_path = os.path.join(UPLOAD_DIR, unique_name)
        generate_sample_electricity_bill(file_path)
    elif sample_type == "esg":
        orig_name = "GreenEco_Textiles_Annual_ESG_Audit_2024.pdf"
        unique_name = generate_unique_filename(orig_name)
        file_path = os.path.join(UPLOAD_DIR, unique_name)
        generate_sample_esg_audit_report(file_path)
    elif sample_type == "scanned":
        orig_name = "Scanned_Industrial_Waste_Disposal_Log.pdf"
        unique_name = generate_unique_filename(orig_name)
        file_path = os.path.join(UPLOAD_DIR, unique_name)
        generate_sample_scanned_receipt_pdf(file_path)
    else:
        raise HTTPException(status_code=400, detail="Invalid sample_type. Choose: electricity, esg, or scanned")

    file_size = os.path.getsize(file_path)
    doc = Document(
        filename=unique_name,
        original_filename=orig_name,
        file_path=file_path,
        file_size=file_size,
        mime_type="application/pdf",
        status="PENDING"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Process immediately
    processed_doc = pipeline_service.process_document(db, doc.id)
    return processed_doc
