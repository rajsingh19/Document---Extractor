import os
import shutil
import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, func

from backend.app.database.session import get_db
from backend.app.models.document import Document
from backend.app.models.audit import AuditLog
from backend.app.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
    DashboardStatsResponse,
    ProcessDocumentRequest,
    FieldVerifyRequest,
    FieldCorrectionRequest,
    ReviewStatusRequest
)
from backend.app.services.extraction_service import ExtractionPipelineService
from backend.app.services.ocr_service import OCRService
from backend.app.services.llm_service import LLMService
from backend.app.utils.helpers import generate_unique_filename
from backend.app.utils.sample_generator import (
    generate_sample_electricity_bill,
    generate_sample_esg_audit_report,
    generate_sample_scanned_receipt_pdf,
    generate_sample_adversarial_invoice
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

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_size = os.path.getsize(file_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file on disk: {str(e)}"
        )

    doc = Document(
        filename=unique_filename,
        original_filename=file.filename,
        file_path=file_path,
        file_size=file_size,
        mime_type="application/pdf",
        status="PENDING",
        review_status="NEEDS_REVIEW"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

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
    review_status_filter: Optional[str] = Query(None, alias="review_status"),
    doc_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    List all uploaded sustainability documents with filtering, review status filter, and search.
    """
    query = db.query(Document)

    if status_filter:
        query = query.filter(Document.status == status_filter.upper())
    if review_status_filter:
        query = query.filter(Document.review_status == review_status_filter.upper())
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

@router.put("/documents/{document_id}/verify-field", response_model=DocumentResponse)
def verify_field(
    document_id: int,
    request: FieldVerifyRequest,
    db: Session = Depends(get_db)
):
    """
    Mark a specific extracted field as human-verified.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    structured = doc.structured_data or {}
    evidence_list = structured.get("evidence", [])
    
    field_found = False
    for ev in evidence_list:
        if ev.get("field") == request.field_name:
            ev["is_verified"] = True
            field_found = True
            break
            
    if not field_found:
        evidence_list.append({
            "field": request.field_name,
            "value": None,
            "unit": None,
            "confidence": 1.0,
            "confidence_level": "HIGH",
            "source_text": "Human Verified",
            "is_verified": True,
            "human_corrected_value": None
        })

    structured["evidence"] = evidence_list
    doc.structured_data = structured

    # Update quality summary count
    quality_summary = doc.quality_summary or {}
    quality_summary["human_verified"] = sum(1 for ev in evidence_list if ev.get("is_verified"))
    doc.quality_summary = quality_summary

    # Audit log
    audit_entry = AuditLog(
        document_id=doc.id,
        field_name=request.field_name,
        original_ai_value=None,
        corrected_value=None,
        action="field_verified",
        notes="Field verified by human reviewer"
    )
    db.add(audit_entry)
    
    # Recalculate review status if all evidence is verified
    if all(ev.get("is_verified") for ev in evidence_list if ev.get("value") is not None):
        doc.review_status = "VERIFIED"

    db.commit()
    db.refresh(doc)
    return doc

@router.put("/documents/{document_id}/correct-field", response_model=DocumentResponse)
def correct_field(
    document_id: int,
    request: FieldCorrectionRequest,
    db: Session = Depends(get_db)
):
    """
    Correct an extracted field value. Preserves original AI value, stores human correction,
    and writes to the audit trail without permanently overwriting original AI extraction.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    structured = doc.structured_data or {}
    evidence_list = structured.get("evidence", [])

    original_val = None
    field_found = False

    for ev in evidence_list:
        if ev.get("field") == request.field_name:
            original_val = ev.get("value")
            ev["human_corrected_value"] = request.corrected_value
            ev["is_verified"] = True
            if request.unit:
                ev["unit"] = request.unit
            field_found = True
            break

    if not field_found:
        evidence_list.append({
            "field": request.field_name,
            "value": None,
            "unit": request.unit,
            "confidence": 1.0,
            "confidence_level": "HIGH",
            "source_text": "Human Corrected",
            "is_verified": True,
            "human_corrected_value": request.corrected_value
        })

    structured["evidence"] = evidence_list

    # Sync top-level schema section if applicable
    field_name = request.field_name
    corrected_val = request.corrected_value

    if field_name == "company_name":
        if "company" not in structured: structured["company"] = {}
        structured["company"]["name"] = str(corrected_val)
        doc.company_name = str(corrected_val)
    elif field_name == "electricity_kwh":
        if "energy" not in structured: structured["energy"] = {}
        val_float = float(corrected_val) if corrected_val is not None else None
        structured["energy"]["electricity_kwh"] = val_float
        doc.total_energy_kwh = val_float
    elif field_name == "fuel_diesel_liters":
        if "energy" not in structured: structured["energy"] = {}
        val_float = float(corrected_val) if corrected_val is not None else None
        structured["energy"]["fuel_diesel_liters"] = val_float
    elif field_name == "total_energy_cost_inr":
        if "energy" not in structured: structured["energy"] = {}
        val_float = float(corrected_val) if corrected_val is not None else None
        structured["energy"]["total_energy_cost_inr"] = val_float
    elif field_name == "water_consumption_kl":
        if "water_and_waste" not in structured: structured["water_and_waste"] = {}
        val_float = float(corrected_val) if corrected_val is not None else None
        structured["water_and_waste"]["water_consumption_kl"] = val_float
        doc.total_water_kl = val_float
    elif field_name in ["hazardous_waste_kg", "non_hazardous_waste_kg"]:
        if "water_and_waste" not in structured: structured["water_and_waste"] = {}
        val_float = float(corrected_val) if corrected_val is not None else None
        structured["water_and_waste"][field_name] = val_float
        doc.total_waste_kg = (
            (structured["water_and_waste"].get("non_hazardous_waste_kg") or 0) +
            (structured["water_and_waste"].get("hazardous_waste_kg") or 0)
        ) or None
    elif field_name == "scope_1_direct_tco2e":
        if "carbon_emissions" not in structured: structured["carbon_emissions"] = {}
        val_float = float(corrected_val) if corrected_val is not None else None
        structured["carbon_emissions"]["scope_1_direct_tco2e"] = val_float
        doc.total_emissions_tco2e = (val_float or 0) + (structured["carbon_emissions"].get("scope_2_indirect_tco2e") or 0)
    elif field_name == "scope_2_indirect_tco2e":
        if "carbon_emissions" not in structured: structured["carbon_emissions"] = {}
        val_float = float(corrected_val) if corrected_val is not None else None
        structured["carbon_emissions"]["scope_2_indirect_tco2e"] = val_float
        doc.total_emissions_tco2e = (structured["carbon_emissions"].get("scope_1_direct_tco2e") or 0) + (val_float or 0)
    elif field_name == "compliance_status":
        if "compliance" not in structured: structured["compliance"] = {}
        structured["compliance"]["compliance_status"] = str(corrected_val) if corrected_val else None
        doc.compliance_status = str(corrected_val) if corrected_val else None

    doc.structured_data = structured

    # Track corrections in Document.field_corrections
    field_corrections = doc.field_corrections or {}
    field_corrections[field_name] = {
        "original_ai_value": original_val,
        "corrected_value": corrected_val,
        "unit": request.unit,
        "updated_at": datetime.utcnow().isoformat()
    }
    doc.field_corrections = field_corrections

    # Update quality summary human_verified count
    quality_summary = doc.quality_summary or {}
    quality_summary["human_verified"] = sum(1 for ev in evidence_list if ev.get("is_verified"))
    # Bonus points for human verification
    orig_score = quality_summary.get("quality_score", doc.quality_score or 80.0)
    new_score = min(100.0, round(orig_score + 2.5, 1))
    quality_summary["quality_score"] = new_score
    doc.quality_score = new_score
    doc.quality_summary = quality_summary

    # Audit Log Entry
    audit_entry = AuditLog(
        document_id=doc.id,
        field_name=field_name,
        original_ai_value=original_val,
        corrected_value=corrected_val,
        action="human_correction",
        notes=f"Corrected value to {corrected_val}"
    )
    db.add(audit_entry)
    
    # Mark review status as VERIFIED
    doc.review_status = "VERIFIED"

    db.commit()
    db.refresh(doc)
    return doc

@router.put("/documents/{document_id}/review-status", response_model=DocumentResponse)
def update_review_status(
    document_id: int,
    request: ReviewStatusRequest,
    db: Session = Depends(get_db)
):
    """
    Manually update human review status ('COMPLETED', 'NEEDS_REVIEW', 'VERIFIED').
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    valid_statuses = ["COMPLETED", "NEEDS_REVIEW", "VERIFIED"]
    new_status = request.review_status.upper()
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid review_status. Must be one of {valid_statuses}")

    old_status = doc.review_status
    doc.review_status = new_status

    if doc.structured_data and isinstance(doc.structured_data, dict):
        if "metadata" in doc.structured_data:
            doc.structured_data["metadata"]["review_status"] = new_status

    audit_entry = AuditLog(
        document_id=doc.id,
        field_name="review_status",
        original_ai_value=old_status,
        corrected_value=new_status,
        action="review_status_change",
        notes=f"Changed document review status from {old_status} to {new_status}"
    )
    db.add(audit_entry)

    db.commit()
    db.refresh(doc)
    return doc

@router.get("/documents/{document_id}/audit-trail")
def get_audit_trail(document_id: int, db: Session = Depends(get_db)):
    """
    Get audit history and human correction logs for a document.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    logs = db.query(AuditLog).filter(AuditLog.document_id == document_id).order_by(desc(AuditLog.timestamp)).all()
    return {
        "document_id": doc.id,
        "filename": doc.original_filename,
        "review_status": doc.review_status,
        "field_corrections": doc.field_corrections or {},
        "audit_logs": [l.to_dict() for l in logs]
    }

@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: int, db: Session = Depends(get_db)):
    """
    Delete a document and its stored PDF from disk.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

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
    Get aggregated MSME sustainability, human review, and document processing statistics.
    """
    docs = db.query(Document).all()
    
    total = len(docs)
    processed = sum(1 for d in docs if d.status == "COMPLETED")
    pending = sum(1 for d in docs if d.status in ["PENDING", "EXTRACTING_TEXT", "RUNNING_LLM", "VALIDATING"])
    failed = sum(1 for d in docs if d.status == "FAILED")
    needs_review = sum(1 for d in docs if d.review_status == "NEEDS_REVIEW")
    verified = sum(1 for d in docs if d.review_status == "VERIFIED")

    total_energy = sum((d.total_energy_kwh or 0) for d in docs if d.status == "COMPLETED")
    total_emissions = sum((d.total_emissions_tco2e or 0) for d in docs if d.status == "COMPLETED")
    total_water = sum((d.total_water_kl or 0) for d in docs if d.status == "COMPLETED")
    total_waste = sum((d.total_waste_kg or 0) for d in docs if d.status == "COMPLETED")

    doc_types = {}
    compliance = {}
    review_statuses = {}
    methods = {}

    for d in docs:
        if d.document_type:
            doc_types[d.document_type] = doc_types.get(d.document_type, 0) + 1
        if d.compliance_status:
            compliance[d.compliance_status] = compliance.get(d.compliance_status, 0) + 1
        if d.review_status:
            review_statuses[d.review_status] = review_statuses.get(d.review_status, 0) + 1
        if d.extraction_method:
            methods[d.extraction_method] = methods.get(d.extraction_method, 0) + 1

    return {
        "total_documents": total,
        "processed_count": processed,
        "pending_count": pending,
        "failed_count": failed,
        "needs_review_count": needs_review,
        "verified_count": verified,
        "total_energy_kwh": round(total_energy, 2),
        "total_emissions_tco2e": round(total_emissions, 2),
        "total_water_kl": round(total_water, 2),
        "total_waste_kg": round(total_waste, 2),
        "document_types_breakdown": doc_types,
        "compliance_breakdown": compliance,
        "review_status_breakdown": review_statuses,
        "extraction_methods_breakdown": methods
    }

@router.post("/documents/sample-seed", status_code=status.HTTP_201_CREATED)
def seed_sample_documents(
    sample_type: str = Query("electricity", description="electricity | esg | scanned | adversarial"),
    db: Session = Depends(get_db)
):
    """
    Generate and process a realistic sample MSME sustainability PDF for immediate test/demo.
    """
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    filename_map = {
        "electricity": "sample_industrial_electricity_bill.pdf",
        "esg": "sample_esg_sustainability_audit.pdf",
        "scanned": "sample_scanned_waste_manifest.pdf",
        "adversarial": "sample_adversarial_invoice.pdf"
    }

    if sample_type not in filename_map:
        raise HTTPException(status_code=400, detail="Invalid sample_type. Choose 'electricity', 'esg', 'scanned', or 'adversarial'.")

    target_filename = filename_map[sample_type]
    file_path = os.path.join(UPLOAD_DIR, target_filename)

    if sample_type == "electricity":
        generate_sample_electricity_bill(file_path)
    elif sample_type == "esg":
        generate_sample_esg_audit_report(file_path)
    elif sample_type == "scanned":
        generate_sample_scanned_receipt_pdf(file_path)
    elif sample_type == "adversarial":
        generate_sample_adversarial_invoice(file_path)

    file_size = os.path.getsize(file_path)

    doc = Document(
        filename=target_filename,
        original_filename=target_filename,
        file_path=file_path,
        file_size=file_size,
        mime_type="application/pdf",
        status="PENDING",
        review_status="NEEDS_REVIEW"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    force_ocr = (sample_type == "scanned")
    doc = pipeline_service.process_document(db, doc.id, force_ocr=force_ocr)
    return doc
