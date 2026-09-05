"""
schemas/carbon_credit.py — Pydantic Schemas for Carbon Credit Readiness & Project Eligibility Assessment Engine (Step 20).
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CarbonCreditAssessmentCreate(BaseModel):
    project_id: int
    reporting_period: Optional[str] = None  # if not provided, defaults to project baseline or active period
    notes: Optional[str] = None


class CarbonCreditAssessmentStatusUpdate(BaseModel):
    status: str  # DRAFT, GENERATED, NEEDS_REVIEW, READY_FOR_METHODOLOGY_REVIEW, FINALIZED
    notes: Optional[str] = None


class CarbonCreditEvidenceResponse(BaseModel):
    id: int
    assessment_id: int
    requirement_id: int
    project_id: int
    source_type: Optional[str] = None
    source_id: Optional[int] = None
    document_id: Optional[int] = None
    source_field: Optional[str] = None
    source_text: Optional[str] = None
    reporting_period: Optional[str] = None
    page_number: Optional[int] = None
    evidence_status: str
    created_at: datetime

    class Config:
        from_attributes = True


class CarbonCreditRequirementResponse(BaseModel):
    id: int
    assessment_id: int
    requirement_code: str
    requirement_name: str
    category: str
    description: Optional[str] = None
    weight: float
    required: bool
    status: str
    reason: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[int] = None
    evidence_items: List[CarbonCreditEvidenceResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class CarbonCreditDimensionSummary(BaseModel):
    category: str
    title: str
    score: float
    max_weight: float
    status: str  # SUPPORTED, PARTIAL, MISSING, NEEDS_REVIEW, NOT_APPLICABLE
    supported_count: int
    total_count: int
    explanation: str
    source_ref: Optional[str] = None


class CarbonCreditMissingRequirement(BaseModel):
    requirement_code: str
    requirement_name: str
    category: str
    status: str
    priority: str  # HIGH, MEDIUM, LOW
    reason: str
    what_is_needed: str
    evidence_currently_available: str
    recommended_action: str
    source_reference: Optional[str] = None


class CarbonCreditNextAction(BaseModel):
    action: str
    priority: str  # HIGH, MEDIUM, LOW
    reason: str
    category: str
    source: Optional[str] = None
    expected_readiness_impact: str


class CarbonCreditChecklistItem(BaseModel):
    section_number: int
    section_name: str
    item_code: str
    title: str
    status: str  # READY, PARTIAL, MISSING, NEEDS_REVIEW, NOT_APPLICABLE
    description: str
    evidence_ref: Optional[str] = None


class CarbonCreditMethodologyReadiness(BaseModel):
    overall_methodology_status: str  # READY, PARTIAL, MISSING, NEEDS_REVIEW
    framework: str = "GENERIC_CARBON_STANDARD"
    project_type: Optional[str] = None
    activity_boundary: Optional[str] = None
    baseline_status: str = "NEEDS_REVIEW"
    monitoring_status: str = "NEEDS_REVIEW"
    emissions_traceability_status: str = "NEEDS_REVIEW"
    evidence_status: str = "NEEDS_REVIEW"
    measurement_status: str = "NEEDS_REVIEW"
    verification_pathway_status: str = "NOT_RECORDED"
    disclaimer: str = (
        "Methodology review evaluates structural project data completeness against generic carbon standards. "
        "It does not certify, validate, or guarantee eligibility under Verra VCS, Gold Standard, or any registry."
    )


class CarbonCreditAccountingSummary(BaseModel):
    accounted_emissions_tco2e: Optional[float] = None
    measured_emissions_tco2e: Optional[float] = None
    baseline_co2e_tco2e: Optional[float] = None
    observed_reduction_tco2e: Optional[float] = None
    posted_ledger_entries_count: int = 0
    unit_label: str = "tCO2e"
    note: str = "All figures represent accounted or measured greenhouse gas emissions (tCO2e), not carbon credits."


class CarbonCreditAssessmentEventResponse(BaseModel):
    id: int
    assessment_id: int
    event_type: str
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    notes: Optional[str] = None
    actor: str
    created_at: datetime

    class Config:
        from_attributes = True


class CarbonCreditAssessmentResponse(BaseModel):
    id: int
    assessment_code: str
    project_id: int
    project_name: str
    reporting_period: str
    assessment_version: str
    overall_readiness_score: float
    readiness_band: str  # NOT_READY, PARTIALLY_READY, READY_FOR_METHODOLOGY_REVIEW
    status: str  # DRAFT, GENERATED, NEEDS_REVIEW, READY_FOR_METHODOLOGY_REVIEW, FINALIZED
    methodology_status: str  # READY, PARTIAL, MISSING, NEEDS_REVIEW
    standard_status: str  # READY, PARTIAL, MISSING, NEEDS_REVIEW
    notes: Optional[str] = None
    generated_at: Optional[datetime] = None
    finalized_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    # Summary counts
    total_requirements: int = 0
    supported_requirements: int = 0
    partial_requirements: int = 0
    missing_requirements_count: int = 0
    needs_review_requirements: int = 0

    disclaimer: str = (
        "This assessment measures project documentation and evidence readiness. "
        "It does not issue, verify, guarantee, or estimate tradable carbon credits."
    )

    # Scoped project details snapshot
    project_category: Optional[str] = None
    project_scope: Optional[str] = None
    project_owner: Optional[str] = None
    project_status: Optional[str] = None
    baseline_period: Optional[str] = None
    baseline_co2e: Optional[float] = None
    baseline_co2e_unit: Optional[str] = None
    target_description: Optional[str] = None

    accounting_summary: Optional[CarbonCreditAccountingSummary] = None
    dimensions: List[CarbonCreditDimensionSummary] = Field(default_factory=list)
    missing_requirements: List[CarbonCreditMissingRequirement] = Field(default_factory=list)
    next_actions: List[CarbonCreditNextAction] = Field(default_factory=list)
    checklist: List[CarbonCreditChecklistItem] = Field(default_factory=list)
    methodology: Optional[CarbonCreditMethodologyReadiness] = None
    requirements: List[CarbonCreditRequirementResponse] = Field(default_factory=list)
    events: List[CarbonCreditAssessmentEventResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class CarbonCreditAssessmentList(BaseModel):
    total: int
    items: List[CarbonCreditAssessmentResponse] = Field(default_factory=list)
