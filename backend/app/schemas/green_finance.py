"""
schemas/green_finance.py — Pydantic Schemas for Green Finance Readiness Engine (Step 19).
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class GreenFinanceAssessmentCreate(BaseModel):
    reporting_period: str  # e.g. '2024-10'
    reporting_year: Optional[int] = None
    business_name: Optional[str] = "TARA ENGINEERING WORKS"
    notes: Optional[str] = None


class GreenFinanceAssessmentStatusUpdate(BaseModel):
    status: str  # DRAFT, GENERATED, NEEDS_REVIEW, READY_FOR_APPLICATION, FINALIZED
    notes: Optional[str] = None


class GreenFinanceEvidenceResponse(BaseModel):
    id: int
    assessment_id: int
    requirement_id: int
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


class GreenFinanceRequirementResponse(BaseModel):
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
    evidence_items: List[GreenFinanceEvidenceResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class GreenFinanceDimensionSummary(BaseModel):
    category: str
    title: str
    score: float
    max_weight: float
    status: str  # SUPPORTED, PARTIAL, MISSING, NEEDS_REVIEW
    supported_count: int
    total_count: int
    explanation: str


class GreenFinanceMissingRequirement(BaseModel):
    requirement_code: str
    requirement_name: str
    category: str
    priority: str  # HIGH, MEDIUM, LOW
    reason: str
    what_is_needed: str
    evidence_currently_available: str
    source_reference: Optional[str] = None


class GreenFinanceNextAction(BaseModel):
    action: str
    priority: str  # HIGH, MEDIUM, LOW
    reason: str
    category: str
    source: Optional[str] = None
    expected_readiness_impact: str


class GreenFinanceChecklistItem(BaseModel):
    category: str
    item_code: str
    title: str
    status: str  # READY, PARTIAL, MISSING, NEEDS_REVIEW, NOT_APPLICABLE
    description: str
    evidence_ref: Optional[str] = None


class GreenFinanceAssessmentEventResponse(BaseModel):
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


class GreenFinanceAssessmentResponse(BaseModel):
    id: int
    assessment_code: str
    business_name: str
    reporting_period: str
    reporting_year: Optional[int] = None
    assessment_version: str
    overall_readiness_score: float
    readiness_band: str  # NOT_READY, PARTIALLY_READY, READY_FOR_REVIEW
    status: str  # DRAFT, GENERATED, NEEDS_REVIEW, READY_FOR_APPLICATION, FINALIZED
    notes: Optional[str] = None
    generated_at: Optional[datetime] = None
    finalized_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    # Summary statistics
    total_requirements: int = 0
    supported_requirements: int = 0
    partial_requirements: int = 0
    missing_requirements_count: int = 0
    needs_review_requirements: int = 0

    disclaimer: str = (
        "This score measures the completeness and quality of sustainability-related application evidence available in Senseible. "
        "It is not a lender credit score, loan eligibility score, approval prediction, or financing guarantee."
    )

    dimensions: List[GreenFinanceDimensionSummary] = Field(default_factory=list)
    missing_requirements: List[GreenFinanceMissingRequirement] = Field(default_factory=list)
    next_actions: List[GreenFinanceNextAction] = Field(default_factory=list)
    checklist: List[GreenFinanceChecklistItem] = Field(default_factory=list)
    requirements: List[GreenFinanceRequirementResponse] = Field(default_factory=list)
    events: List[GreenFinanceAssessmentEventResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class GreenFinanceAssessmentList(BaseModel):
    total: int
    items: List[GreenFinanceAssessmentResponse] = Field(default_factory=list)
