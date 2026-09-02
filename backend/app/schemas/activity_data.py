"""
schemas/activity_data.py — Pydantic Schemas for Activity Data (Step 12C).
"""
from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, Field


class ActivityDataNormalizeRequest(BaseModel):
    """
    Request payload to preview/test normalization of raw activity inputs.
    """
    activity_type: Optional[str] = Field(default=None, description="Raw or extracted activity name")
    quantity: Optional[Any] = Field(default=None, description="Raw numeric string or number")
    unit: Optional[str] = Field(default=None, description="Raw unit string")
    geography: Optional[str] = Field(default=None, description="Explicit geographic boundary")
    reporting_period: Optional[str] = Field(default=None, description="Raw reporting period string")
    reporting_year: Optional[int] = Field(default=None, description="Explicit reporting year")
    scope: Optional[str] = Field(default=None, description="Associated Scope (SCOPE_1, SCOPE_2, etc.)")
    source_field: Optional[str] = Field(default=None, description="Originating document field")
    source_text: Optional[str] = Field(default=None, description="Verbatim source sentence / chunk")
    page: Optional[int] = Field(default=None, description="Document page number")
    activity_role: Optional[str] = Field(default=None, description="Suggested role: TOTAL, COMPONENT, SUPPORTING")


class NormalizationPreviewResponse(BaseModel):
    """
    Structured preview response for raw activity normalization.
    """
    status: str = Field(..., description="VALID, NEEDS_REVIEW, INVALID")
    activity_type: Optional[str] = None
    category: Optional[str] = None
    activity_role: str = "TOTAL"
    calculation_eligible: bool = True
    activity_group_id: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    geography: Optional[str] = None
    reporting_period: Optional[str] = None
    reporting_year: Optional[int] = None
    scope: Optional[str] = None
    reasons: List[str] = Field(default_factory=list)
    normalization_version: str = "1.0"


class ActivityDataResponse(BaseModel):
    """
    Serializable canonical ActivityData record.
    """
    id: int
    document_id: Optional[int] = None
    metric_id: Optional[int] = None
    activity_type: str
    category: str
    activity_role: str
    calculation_eligible: bool
    activity_group_id: Optional[str] = None
    quantity: float
    unit: str
    geography: Optional[str] = None
    reporting_period: Optional[str] = None
    reporting_year: Optional[int] = None
    scope: Optional[str] = None
    source_field: Optional[str] = None
    source_text: Optional[str] = None
    page: Optional[int] = None
    verification_status: str = "UNVERIFIED"
    normalization_status: str = "VALID"
    normalization_reasons: Optional[str] = None
    normalization_version: str = "1.0"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ActivityDataListResponse(BaseModel):
    total: int
    items: List[ActivityDataResponse]
