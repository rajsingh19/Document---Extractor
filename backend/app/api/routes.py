import os
import shutil
import json
import hashlib
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, func

from backend.app.database.session import get_db
from backend.app.models.document import Document
from backend.app.models.audit import AuditLog
from backend.app.models.sustainability_metric import SustainabilityMetric
from backend.app.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
    DashboardStatsResponse,
    ProcessDocumentRequest,
    FieldVerifyRequest,
    FieldCorrectionRequest,
    ReviewStatusRequest,
    ClassificationUpdateRequest
)
from backend.app.schemas.copilot import CopilotRequest, CopilotResponse, CopilotContext
from backend.app.services.extraction_service import ExtractionPipelineService
from backend.app.services.ocr_service import OCRService
from backend.app.services.llm_service import LLMService
from backend.app.services.normalization_service import NormalizationService
from backend.app.services.insights_service import insights_service
from backend.app.services.copilot_service import copilot_service
from backend.app.services.copilot_context import copilot_context_service
from backend.app.utils.helpers import generate_unique_filename, parse_period_key
from backend.app.utils.sample_generator import (
    generate_sample_electricity_bill,
    generate_sample_esg_audit_report,
    generate_sample_scanned_receipt_pdf,
    generate_sample_adversarial_invoice
)

router = APIRouter(prefix="/api", tags=["Document AI"])
pipeline_service = ExtractionPipelineService()
llm_service = LLMService()
normalization_service = NormalizationService()

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB max limit

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """System health and integration diagnostic check."""
    db_status = "connected"
    try:
        db.query(Document.id).first()
    except Exception:
        db_status = "error"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "service": "senseible-document-ai",
        "version": "1.0.0",
        "database": db_status,
        "extraction_service": "available",
        "ocr_available": OCRService.is_ocr_available(),
        "openai_configured": llm_service.is_configured(),
        "llm_status": "Configured (Live)" if llm_service.is_configured() else "Deterministic Heuristic Engine Active"
    }

@router.post("/documents/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    auto_process: bool = Query(True, description="Automatically trigger extraction pipeline"),
    force_ocr: bool = Query(False, description="Force Tesseract OCR extraction"),
    db: Session = Depends(get_db)
):
    """
    Upload a PDF sustainability document, check for deterministic SHA-256 duplicate,
    and execute the AI extraction pipeline.
    """
    safe_name = os.path.basename(file.filename or "document.pdf")
    if not safe_name.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF documents are supported (.pdf)"
        )

    file_bytes = await file.read()
    file_size = len(file_bytes)

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes)."
        )

    if file_size > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds maximum allowed limit of 25 MB."
        )

    # Magic byte validation for valid PDF format
    if not (file_bytes.startswith(b"%PDF") or b"%PDF-" in file_bytes[:1024]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid PDF format: file header does not contain valid PDF signature (%PDF)."
        )

    file_hash = hashlib.sha256(file_bytes).hexdigest()

    # Deterministic duplicate detection: check if exact file was already uploaded
    existing_doc = db.query(Document).filter(
        Document.file_hash == file_hash,
        Document.status == "COMPLETED"
    ).first()

    if existing_doc:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "duplicate": True,
                "existing_document_id": existing_doc.id,
                "message": "This document has already been processed.",
                **existing_doc.to_dict()
            }
        )

    unique_filename = generate_unique_filename(safe_name)
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    try:
        with open(file_path, "wb") as buffer:
            buffer.write(file_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save file on storage volume."
        )

    doc = Document(
        filename=unique_filename,
        original_filename=safe_name,
        file_path=file_path,
        file_size=file_size,
        file_hash=file_hash,
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
    try:
        normalization_service.normalize_extraction(db, doc)
    except Exception as e:
        print(f"Notice: Normalization after verify failed: {e}")
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
    try:
        normalization_service.normalize_extraction(db, doc)
    except Exception as e:
        print(f"Notice: Normalization after correction failed: {e}")
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
    try:
        normalization_service.normalize_extraction(db, doc)
    except Exception as e:
        print(f"Notice: Normalization after status update failed: {e}")
    return doc

@router.put("/documents/{document_id}/classification", response_model=DocumentResponse)
def update_classification(
    document_id: int,
    request: ClassificationUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Manually correct or update document classification.
    Preserves original AI classification in audit trail, updates expected fields mapping,
    re-evaluates deterministic quality score, and re-normalizes sustainability metrics.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    old_doc_type = doc.document_type or "Unknown / Other"
    new_doc_type = request.document_type

    doc.document_type = new_doc_type

    # Update classification metadata
    classification = dict(doc.classification or {})
    classification["document_type"] = new_doc_type
    classification["classification_method"] = "human"
    classification["confidence"] = 1.0
    classification["confidence_level"] = "HIGH"
    classification["conflict"] = False
    classification["reasoning"] = request.notes or f"Manually classified as {new_doc_type} by human reviewer."
    doc.classification = classification

    # Audit trail entry
    audit_entry = AuditLog(
        document_id=doc.id,
        field_name="classification",
        original_ai_value=old_doc_type,
        corrected_value=new_doc_type,
        action="classification_change",
        notes=request.notes or f"Human reviewer changed classification from {old_doc_type} to {new_doc_type}"
    )
    db.add(audit_entry)

    # Recalculate deterministic quality score based on newly expected fields
    if doc.structured_data:
        structured = doc.structured_data
        structured["document_type"] = new_doc_type
        evidence_list = structured.get("evidence", [])
        
        # Calculate new quality score for the updated document type
        quality_res = llm_service.calculate_deterministic_quality_score(
            doc_type=new_doc_type,
            data=structured,
            evidence=evidence_list,
            extraction_method=doc.extraction_method or "pymupdf",
            is_scanned_ocr=(doc.extraction_method == "ocr_fallback")
        )
        doc.quality_score = quality_res["quality_score"]
        doc.quality_summary = quality_res
        structured["quality_summary"] = quality_res
        doc.structured_data = structured

    db.commit()
    db.refresh(doc)

    # Re-normalize sustainability metrics for the new document type
    try:
        normalization_service.normalize_extraction(db, doc)
    except Exception as e:
        print(f"Notice: Normalization after classification update failed: {e}")

    return doc

@router.post("/documents/{document_id}/normalize")
def normalize_document_endpoint(document_id: int, db: Session = Depends(get_db)):
    """
    Normalize extracted document fields into standardized SustainabilityMetric records.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not doc.structured_data:
        raise HTTPException(status_code=400, detail="Document has no structured data extracted yet")

    metrics = normalization_service.normalize_extraction(db, doc)
    return {
        "document_id": doc.id,
        "metrics_created": len(metrics),
        "metrics": [m.to_dict() for m in metrics]
    }

@router.get("/metrics")
def list_normalized_metrics(
    company: Optional[str] = Query(None, description="Filter by company name"),
    metric_type: Optional[str] = Query(None, description="Filter by metric type"),
    category: Optional[str] = Query(None, description="Filter by category"),
    start_date: Optional[str] = Query(None, description="Filter by period start"),
    end_date: Optional[str] = Query(None, description="Filter by period end"),
    verification_status: Optional[str] = Query(None, description="Filter by verification status"),
    db: Session = Depends(get_db)
):
    """
    List standardized sustainability metrics across documents with optional filtering.
    """
    query = db.query(SustainabilityMetric)
    if company:
        query = query.filter(SustainabilityMetric.company_name.ilike(f"%{company}%"))
    if metric_type:
        query = query.filter(SustainabilityMetric.metric_type == metric_type)
    if category:
        query = query.filter(SustainabilityMetric.category == category)
    if start_date:
        query = query.filter(SustainabilityMetric.period_start >= start_date)
    if end_date:
        query = query.filter(SustainabilityMetric.period_end <= end_date)
    if verification_status:
        query = query.filter(SustainabilityMetric.verification_status == verification_status)

    metrics = query.order_by(desc(SustainabilityMetric.created_at)).all()
    return {
        "total": len(metrics),
        "metrics": [m.to_dict() for m in metrics]
    }

@router.get("/metrics/summary")
def get_portfolio_metrics_summary(db: Session = Depends(get_db)):
    """
    Get portfolio-level aggregated sustainability totals.
    Guarantees unit safety by strictly summing compatible units only.
    """
    metrics = db.query(SustainabilityMetric).all()

    # Sum only compatible units
    total_electricity_kwh = sum(m.value for m in metrics if m.metric_type == "electricity_consumption" and m.unit == "kWh")
    total_renewable_energy_kwh = sum(m.value for m in metrics if m.metric_type == "renewable_energy" and m.unit == "kWh")
    total_fuel_liters = sum(m.value for m in metrics if m.metric_type == "fuel_consumption" and m.unit in ["Liters", "L", "lts"])
    total_scope_1_tco2e = sum(m.value for m in metrics if m.metric_type == "scope_1_emissions" and m.unit == "tCO2e")
    total_scope_2_tco2e = sum(m.value for m in metrics if m.metric_type == "scope_2_emissions" and m.unit == "tCO2e")
    total_ghg_emissions_tco2e = sum(m.value for m in metrics if m.metric_type == "total_ghg_emissions" and m.unit == "tCO2e")
    if not total_ghg_emissions_tco2e:
        total_ghg_emissions_tco2e = total_scope_1_tco2e + total_scope_2_tco2e

    total_water_kl = sum(m.value for m in metrics if m.metric_type == "water_consumption" and m.unit == "kL")
    total_recycled_water_kl = sum(m.value for m in metrics if m.metric_type == "recycled_water" and m.unit == "kL")
    total_hazardous_waste_kg = sum(m.value for m in metrics if m.metric_type == "hazardous_waste" and m.unit == "kg")
    total_non_hazardous_waste_kg = sum(m.value for m in metrics if m.metric_type == "non_hazardous_waste" and m.unit == "kg")
    total_waste_kg = total_hazardous_waste_kg + total_non_hazardous_waste_kg

    ai_extracted_count = sum(1 for m in metrics if m.verification_status == "AI_EXTRACTED")
    human_verified_count = sum(1 for m in metrics if m.verification_status == "HUMAN_VERIFIED")
    docs_with_metrics = len(set(m.document_id for m in metrics))

    # Calculate actual latest available reporting period for each category (never using upload date)
    def get_latest_period(category_types):
        recs = [m for m in metrics if m.metric_type in category_types and (m.period_start or m.period_end)]
        if not recs:
            return None
        sorted_recs = sorted(recs, key=lambda r: parse_period_key(r.period_start or r.period_end), reverse=True)
        return sorted_recs[0].period_start or sorted_recs[0].period_end

    latest_available_data = {
        "electricity": get_latest_period(["electricity_consumption", "renewable_energy"]),
        "ghg": get_latest_period(["scope_1_emissions", "scope_2_emissions", "total_ghg_emissions"]),
        "water": get_latest_period(["water_consumption", "recycled_water"]),
        "waste": get_latest_period(["hazardous_waste", "non_hazardous_waste", "recycled_waste"]),
    }

    return {
        "total_electricity_kwh": round(total_electricity_kwh, 2),
        "total_renewable_energy_kwh": round(total_renewable_energy_kwh, 2),
        "total_fuel_liters": round(total_fuel_liters, 2),
        "total_scope_1_tco2e": round(total_scope_1_tco2e, 2),
        "total_scope_2_tco2e": round(total_scope_2_tco2e, 2),
        "total_total_ghg_tco2e": round(total_ghg_emissions_tco2e, 2),
        "total_water_kl": round(total_water_kl, 2),
        "total_recycled_water_kl": round(total_recycled_water_kl, 2),
        "total_hazardous_waste_kg": round(total_hazardous_waste_kg, 2),
        "total_non_hazardous_waste_kg": round(total_non_hazardous_waste_kg, 2),
        "total_waste_kg": round(total_waste_kg, 2),
        "ai_extracted_count": ai_extracted_count,
        "human_verified_count": human_verified_count,
        "total_metrics_count": len(metrics),
        "documents_with_metrics_count": docs_with_metrics,
        "latest_available_data": latest_available_data
    }

@router.get("/metrics/trends")
def get_metrics_trends(
    metric_type: str = Query("electricity_consumption", description="Metric type to query trends for"),
    company: Optional[str] = Query(None, description="Filter by company name"),
    start_date: Optional[str] = Query(None, description="Filter by period start"),
    end_date: Optional[str] = Query(None, description="Filter by period end"),
    db: Session = Depends(get_db)
):
    """
    Return chronological sustainability metric history for trend analysis.
    Sorted chronologically by reporting period. Never fabricates missing periods.
    """
    query = db.query(SustainabilityMetric).filter(SustainabilityMetric.metric_type == metric_type)
    if company:
        query = query.filter(SustainabilityMetric.company_name.ilike(f"%{company}%"))
    if start_date:
        query = query.filter(SustainabilityMetric.period_start >= start_date)
    if end_date:
        query = query.filter(SustainabilityMetric.period_end <= end_date)

    records = query.all()
    if not records:
        return {
            "company_name": company or "All Companies",
            "metric_type": metric_type,
            "unit": "kWh",
            "data": []
        }

    unit = records[0].unit

    # Sort chronologically by standard period key
    def sort_key(m):
        p = m.period_start or m.period_end or "9999-99"
        return (parse_period_key(p), m.created_at or datetime.min)

    sorted_records = sorted(records, key=sort_key)

    data_points = []
    for m in sorted_records:
        period_raw = m.period_start or m.period_end or "Unknown"
        data_points.append({
            "id": m.id,
            "document_id": m.document_id,
            "company_name": m.company_name,
            "period": parse_period_key(period_raw),
            "period_label": period_raw,
            "period_start": m.period_start,
            "period_end": m.period_end,
            "value": m.value,
            "unit": m.unit,
            "source_field": m.source_field,
            "source_text": m.source_text,
            "confidence": m.confidence,
            "verification_status": m.verification_status,
            "created_at": m.created_at.isoformat() if m.created_at else None
        })

    return {
        "company_name": company or (records[0].company_name if records else "All Companies"),
        "metric_type": metric_type,
        "unit": unit,
        "data": data_points
    }

@router.get("/metrics/change")
def get_metrics_change(
    metric_type: str = Query("electricity_consumption", description="Metric type to compare"),
    company: Optional[str] = Query(None, description="Filter by company name"),
    db: Session = Depends(get_db)
):
    """
    Period-over-period comparison between the latest two reporting periods.
    """
    query = db.query(SustainabilityMetric).filter(SustainabilityMetric.metric_type == metric_type)
    if company:
        query = query.filter(SustainabilityMetric.company_name.ilike(f"%{company}%"))

    records = query.all()
    if not records:
        return {
            "metric_type": metric_type,
            "unit": "kWh",
            "current_period": None,
            "current_value": None,
            "previous_period": None,
            "previous_value": None,
            "absolute_change": None,
            "percentage_change": None
        }

    def sort_key(m):
        p = m.period_start or m.period_end or "9999-99"
        return (parse_period_key(p), m.created_at or datetime.min)

    sorted_records = sorted(records, key=sort_key)

    if len(sorted_records) < 2:
        latest = sorted_records[0]
        return {
            "metric_type": metric_type,
            "unit": latest.unit,
            "current_period": parse_period_key(latest.period_start or latest.period_end or "Unknown"),
            "current_value": latest.value,
            "previous_period": None,
            "previous_value": None,
            "absolute_change": None,
            "percentage_change": None
        }

    curr = sorted_records[-1]
    prev = sorted_records[-2]

    abs_change = round(curr.value - prev.value, 2)
    pct_change = round(((curr.value - prev.value) / prev.value) * 100, 2) if prev.value != 0 else 0.0

    return {
        "metric_type": metric_type,
        "unit": curr.unit,
        "current_period": parse_period_key(curr.period_start or curr.period_end or "Unknown"),
        "current_value": curr.value,
        "previous_period": parse_period_key(prev.period_start or prev.period_end or "Unknown"),
        "previous_value": prev.value,
        "absolute_change": abs_change,
        "percentage_change": pct_change
    }

@router.get("/insights")
def get_sustainability_insights(
    company: Optional[str] = Query(None, description="Filter insights by company name"),
    severity: Optional[str] = Query(None, description="Filter insights by severity (INFO, ATTENTION, REVIEW)"),
    metric_type: Optional[str] = Query(None, description="Filter insights by metric type"),
    db: Session = Depends(get_db)
):
    """
    Generate deterministic, explainable sustainability insights across stored documents and metrics.
    """
    insights = insights_service.generate_metric_insights(
        db=db,
        company=company,
        severity=severity,
        metric_type=metric_type
    )
    return {
        "count": len(insights),
        "total": len(insights),
        "insights": [i.model_dump() for i in insights]
    }


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

@router.post("/copilot/chat", response_model=CopilotResponse)
def copilot_chat(
    request: CopilotRequest,
    db: Session = Depends(get_db)
):
    """
    Senseible AI Copilot conversation endpoint (Step 11B grounded context).
    Classifies intent, builds grounded context from database, and returns structured response contract.
    """
    try:
        cleaned_msg = (request.message or "").strip()
        if not cleaned_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message cannot be empty."
            )
        if len(cleaned_msg) > 2000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message exceeds maximum allowed length of 2000 characters."
            )
        
        response = copilot_service.chat(db, cleaned_msg)
        return response
    except HTTPException:
        raise
    except Exception as e:
        # Never expose internal exception details or stack traces
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request with Copilot. Please try again."
        )

@router.get("/copilot/context", response_model=CopilotContext)
def get_copilot_context(
    query: str = Query("What documents do I have?", description="User query for context retrieval"),
    db: Session = Depends(get_db)
):
    """
    Development/debug endpoint to inspect the structured grounded context generated
    for a given query across documents, metrics, evidence, and deterministic insights.
    """
    return copilot_context_service.build_context(db, query)

