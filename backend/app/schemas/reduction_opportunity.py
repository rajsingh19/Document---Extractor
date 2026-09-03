"""
schemas/reduction_opportunity.py — Pydantic Schemas for Carbon Reduction Opportunities (Step 16).
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class OpportunityStatusUpdateRequest(BaseModel):
    status: str  # OPEN, ACKNOWLEDGED, IN_PROGRESS, COMPLETED, DISMISSED
    note: Optional[str] = None


class ReductionOpportunityResponse(BaseModel):
    id: int
    opportunity_code: str
    title: str
    description: str
    category: str
    activity_type: Optional[str] = None
    scope: Optional[str] = None
    priority: str
    trigger_type: str
    status: str
    evidence_document_id: Optional[int] = None
    evidence_metric_id: Optional[int] = None
    evidence_ledger_entry_id: Optional[int] = None
    current_value: Optional[float] = None
    current_unit: Optional[str] = None
    previous_value: Optional[float] = None
    previous_unit: Optional[str] = None
    change_absolute: Optional[float] = None
    change_percentage: Optional[float] = None
    calculated_co2e: Optional[float] = None
    calculated_co2e_unit: str = "kgCO2e"
    calculated_co2e_t: Optional[float] = None
    rationale: str
    recommended_action: str
    limitations: str
    detection_version: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReductionOpportunityList(BaseModel):
    total: int
    items: List[ReductionOpportunityResponse] = Field(default_factory=list)


class ReductionOpportunitySummary(BaseModel):
    total_opportunities: int = 0
    open_count: int = 0
    acknowledged_count: int = 0
    in_progress_count: int = 0
    completed_count: int = 0
    dismissed_count: int = 0
    high_priority_count: int = 0
    medium_priority_count: int = 0
    low_priority_count: int = 0
    by_category: Dict[str, int] = Field(default_factory=dict)
    by_scope: Dict[str, int] = Field(default_factory=dict)
