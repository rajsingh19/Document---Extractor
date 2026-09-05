"""
api/carbon_credit.py — FastAPI Endpoints for Carbon Credit Readiness & Project Eligibility Assessment Engine (Step 20).

CRITICAL BOUNDARIES:
- Assesses project readiness for methodology and certification review only.
- Does NOT issue, create, sell, or predict tradable carbon credits.
- Does NOT calculate market value or carbon-credit price.
- Does NOT guarantee additionality, permanence, or certification.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.schemas.carbon_credit import (
    CarbonCreditAssessmentCreate,
    CarbonCreditAssessmentStatusUpdate,
    CarbonCreditAssessmentResponse,
    CarbonCreditAssessmentList,
    CarbonCreditRequirementResponse,
    CarbonCreditEvidenceResponse,
    CarbonCreditNextAction,
    CarbonCreditChecklistItem,
    CarbonCreditMethodologyReadiness,
)
from backend.app.services.carbon_credit_readiness import (
    carbon_credit_service,
    CARBON_CREDIT_DISCLAIMER,
    METHODOLOGY_DISCLAIMER,
    REQUIREMENT_DEFINITIONS,
    DIMENSION_METADATA,
)
from backend.app.services.carbon_credit_pdf import carbon_credit_pdf_renderer

router = APIRouter(prefix="/carbon-credit", tags=["Carbon Credit Readiness"])


@router.get("/framework")
def get_carbon_credit_framework():
    """
    Get Carbon Credit Readiness framework metadata, scoring methodology, and product boundary disclaimers.
    """
    return {
        "framework_name": "Carbon Credit Readiness & Project Eligibility Assessment Engine",
        "engine_version": "1.0",
        "disclaimer": CARBON_CREDIT_DISCLAIMER,
        "methodology_disclaimer": METHODOLOGY_DISCLAIMER,
        "default_standard": "GENERIC_CARBON_STANDARD",
        "scoring_methodology": (
            "Deterministic weighted completion score across 15 dimensions: Project Definition, Baseline, "
            "Activity Data, Carbon Accounting, Emission Factors, Reduction Evidence, Additionality Information, "
            "Monitoring, Measurement, Verification, Methodology Review, Standard Review, Reporting, "
            "Governance, and Evidence Package. Scores: 0-39: NOT_READY, 40-69: PARTIALLY_READY, "
            "70-100: READY_FOR_METHODOLOGY_REVIEW."
        ),
        "dimensions_count": len(DIMENSION_METADATA),
        "requirements_count": len(REQUIREMENT_DEFINITIONS),
        "boundaries": {
            "carbon_credits_issued": False,
            "tradable_credits": False,
            "market_value_estimation": False,
            "guaranteed_additionality": False,
            "guaranteed_issuance": False,
        }
    }


@router.get("/requirements")
def list_carbon_credit_requirements():
    """
    List all 15 readiness requirement criteria definitions.
    """
    return REQUIREMENT_DEFINITIONS


@router.post("/assessments", response_model=CarbonCreditAssessmentResponse, status_code=status.HTTP_201_CREATED)
def create_carbon_credit_assessment(
    data: CarbonCreditAssessmentCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new draft CarbonCreditAssessment tied strictly to an existing ReductionProject.
    """
    try:
        assessment = carbon_credit_service.create_assessment(db, data)
        return carbon_credit_service.build_assessment_dto(db, assessment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/assessments", response_model=CarbonCreditAssessmentList)
def list_carbon_credit_assessments(
    project_id: Optional[int] = Query(None, description="Filter by ReductionProject ID"),
    reporting_period: Optional[str] = Query(None, description="Filter by reporting period"),
    status: Optional[str] = Query(None, description="Filter by assessment status"),
    db: Session = Depends(get_db)
):
    """
    List Carbon Credit Readiness assessments with optional filtering.
    """
    assessments = carbon_credit_service.get_assessments(db, project_id, reporting_period, status)
    items = [carbon_credit_service.build_assessment_dto(db, a) for a in assessments]
    return {"total": len(items), "items": items}


@router.get("/assessments/{assessment_id}", response_model=CarbonCreditAssessmentResponse)
def get_carbon_credit_assessment(
    assessment_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed Carbon Credit Readiness assessment object.
    """
    assessment = carbon_credit_service.get_assessment(db, assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Carbon credit assessment not found")
    return carbon_credit_service.build_assessment_dto(db, assessment)


@router.post("/assessments/{assessment_id}/generate", response_model=CarbonCreditAssessmentResponse)
def generate_carbon_credit_assessment(
    assessment_id: int,
    db: Session = Depends(get_db)
):
    """
    Deterministically evaluate readiness requirements and compute overall score across 15 dimensions.
    """
    try:
        assessment = carbon_credit_service.generate_assessment(db, assessment_id)
        return carbon_credit_service.build_assessment_dto(db, assessment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/assessments/{assessment_id}/requirements", response_model=List[CarbonCreditRequirementResponse])
def get_carbon_credit_assessment_requirements(
    assessment_id: int,
    db: Session = Depends(get_db)
):
    """
    Get evaluated requirement items for a Carbon Credit Readiness assessment.
    """
    assessment = carbon_credit_service.get_assessment(db, assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Carbon credit assessment not found")
    dto = carbon_credit_service.build_assessment_dto(db, assessment)
    return dto.requirements


@router.get("/assessments/{assessment_id}/evidence", response_model=List[CarbonCreditEvidenceResponse])
def get_carbon_credit_assessment_evidence(
    assessment_id: int,
    db: Session = Depends(get_db)
):
    """
    Get evidence provenance records linked to a Carbon Credit Readiness assessment.
    """
    assessment = carbon_credit_service.get_assessment(db, assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Carbon credit assessment not found")
    dto = carbon_credit_service.build_assessment_dto(db, assessment)
    evidence_list = []
    for req in dto.requirements:
        evidence_list.extend(req.evidence_items)
    return evidence_list


@router.get("/assessments/{assessment_id}/actions", response_model=List[CarbonCreditNextAction])
def get_carbon_credit_assessment_actions(
    assessment_id: int,
    db: Session = Depends(get_db)
):
    """
    Get recommended next actions for improving project readiness posture.
    """
    assessment = carbon_credit_service.get_assessment(db, assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Carbon credit assessment not found")
    dto = carbon_credit_service.build_assessment_dto(db, assessment)
    return dto.next_actions


@router.get("/assessments/{assessment_id}/checklist", response_model=List[CarbonCreditChecklistItem])
def get_carbon_credit_assessment_checklist(
    assessment_id: int,
    db: Session = Depends(get_db)
):
    """
    Get project certification pathway checklist across 15 categories.
    """
    assessment = carbon_credit_service.get_assessment(db, assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Carbon credit assessment not found")
    dto = carbon_credit_service.build_assessment_dto(db, assessment)
    return dto.checklist


@router.get("/assessments/{assessment_id}/methodology", response_model=CarbonCreditMethodologyReadiness)
def get_carbon_credit_assessment_methodology(
    assessment_id: int,
    db: Session = Depends(get_db)
):
    """
    Get methodology review readiness status and structural parameters.
    """
    assessment = carbon_credit_service.get_assessment(db, assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Carbon credit assessment not found")
    dto = carbon_credit_service.build_assessment_dto(db, assessment)
    return dto.methodology


@router.post("/assessments/{assessment_id}/finalize", response_model=CarbonCreditAssessmentResponse)
def finalize_carbon_credit_assessment(
    assessment_id: int,
    db: Session = Depends(get_db)
):
    """
    Finalize Carbon Credit Readiness assessment (makes assessment immutable).
    """
    try:
        assessment = carbon_credit_service.update_assessment_status(
            db=db,
            assessment_id=assessment_id,
            new_status="FINALIZED",
            notes="Assessment finalized for methodology and program review."
        )
        return carbon_credit_service.build_assessment_dto(db, assessment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/assessments/{assessment_id}/status", response_model=CarbonCreditAssessmentResponse)
def update_carbon_credit_assessment_status(
    assessment_id: int,
    data: CarbonCreditAssessmentStatusUpdate,
    db: Session = Depends(get_db)
):
    """
    Update assessment workflow status.
    """
    try:
        assessment = carbon_credit_service.update_assessment_status(
            db=db,
            assessment_id=assessment_id,
            new_status=data.status,
            notes=data.notes,
        )
        return carbon_credit_service.build_assessment_dto(db, assessment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/assessments/{assessment_id}/pdf")
def get_carbon_credit_assessment_pdf(
    assessment_id: int,
    db: Session = Depends(get_db)
):
    """
    Download deterministic ReportLab PDF report for Carbon Credit Readiness assessment.
    """
    assessment = carbon_credit_service.get_assessment(db, assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Carbon credit assessment not found")

    dto = carbon_credit_service.build_assessment_dto(db, assessment)
    pdf_bytes = carbon_credit_pdf_renderer.render(dto)

    filename = f"{assessment.assessment_code}_Carbon_Credit_Readiness_{assessment.reporting_period}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
