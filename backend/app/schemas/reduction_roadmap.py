"""
schemas/reduction_roadmap.py — Pydantic Schemas for Personalized Reduction Roadmap Engine (Step 22B).

Defines strict request/response validation for roadmap targets, phased action items,
progress tracking, and event history.
"""
from datetime import datetime
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from backend.app.config.reduction_roadmap import (
    VALID_ROADMAP_STATUSES,
    VALID_ITEM_STATUSES,
    VALID_ACTION_TYPES,
)


class RoadmapCreateRequest(BaseModel):
    """
    Request payload to initialize and generate a personalized reduction roadmap.
    """
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(None, description="Custom name for the roadmap")
    document_id: Optional[int] = Field(None, description="Filter/scope baseline to a specific document")
    reporting_year: Optional[int] = Field(None, description="Target reporting year if applicable")
    baseline_period: Optional[str] = Field(None, description="Explicit reporting period baseline, or auto-selected")
    target_reduction_percent: Decimal = Field(..., description="Target emissions reduction percentage (0 to 100)")
    target_year: Optional[int] = Field(None, description="Optional target achievement year")
    target_period: Optional[str] = Field(None, description="Optional target achievement reporting period")

    @field_validator("target_reduction_percent")
    @classmethod
    def validate_target_reduction_percent(cls, v: Decimal) -> Decimal:
        if v < Decimal("0.0"):
            raise ValueError("target_reduction_percent cannot be negative")
        if v > Decimal("100.0"):
            raise ValueError("target_reduction_percent cannot exceed 100%")
        return v

    @field_validator("target_year")
    @classmethod
    def validate_target_year(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 2000 or v > 2100):
            raise ValueError("target_year must be a valid year between 2000 and 2100")
        return v


class RoadmapUpdateRequest(BaseModel):
    """
    Request payload to update roadmap status, metadata, or target years.
    """
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = None
    status: Optional[str] = None
    confidence: Optional[str] = None
    target_year: Optional[int] = None
    target_period: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_ROADMAP_STATUSES:
            raise ValueError(f"Invalid status '{v}'. Must be one of {sorted(VALID_ROADMAP_STATUSES)}")
        return v


class RoadmapItemStatusUpdateRequest(BaseModel):
    """
    Request payload to update the status of a specific roadmap item.
    """
    model_config = ConfigDict(extra="forbid")

    status: str = Field(..., description="New status for the roadmap item")
    notes: Optional[str] = Field(None, description="Optional audit note or reason for change")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_ITEM_STATUSES:
            raise ValueError(f"Invalid item status '{v}'. Must be one of {sorted(VALID_ITEM_STATUSES)}")
        return v


class RoadmapItemResponse(BaseModel):
    """
    DTO for an individual phased roadmap action item.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    roadmap_id: int
    priority_id: Optional[int] = None
    opportunity_id: Optional[int] = None
    project_id: Optional[int] = None
    sequence: int
    phase: str
    title: str
    action_type: str
    category: Optional[str] = None
    scope: Optional[str] = None
    current_emissions_kgco2e: Optional[float] = None
    current_emissions_tco2e: Optional[float] = None
    target_contribution_kgco2e: Optional[float] = None
    target_contribution_tco2e: Optional[float] = None
    contribution_status: str
    priority: str
    effort_level: str
    dependency: Optional[str] = None
    prerequisite: Optional[str] = None
    required_data: Optional[str] = None
    measurement_method: Optional[str] = None
    verification_method: Optional[str] = None
    status: str
    evidence_reference: Optional[str] = None
    reason: Optional[str] = None
    limitation: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class RoadmapEventResponse(BaseModel):
    """
    DTO for roadmap audit events.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    roadmap_id: int
    event_type: str
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    actor: str
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


class ReductionRoadmapResponse(BaseModel):
    """
    DTO for reduction roadmap summary.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    roadmap_code: str
    name: str
    document_id: Optional[int] = None
    reporting_year: Optional[int] = None
    baseline_period: str
    baseline_emissions_kgco2e: float
    baseline_emissions_tco2e: float
    target_reduction_percent: float
    target_year: Optional[int] = None
    target_period: Optional[str] = None
    target_emissions_kgco2e: float
    target_emissions_tco2e: float
    reduction_gap_kgco2e: float
    reduction_gap_tco2e: float
    target_status: str
    status: str
    confidence: str
    feasibility_explanation: Optional[str] = None
    roadmap_version: str
    calculation_version: str
    items_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ReductionRoadmapDetail(ReductionRoadmapResponse):
    """
    Full roadmap detail including phased items and event history.
    """
    items: List[RoadmapItemResponse] = []
    events: List[RoadmapEventResponse] = []


class RoadmapProgressResponse(BaseModel):
    """
    Detailed progress breakdown distinguishing Roadmap Progress (actions completed)
    from Emissions Reduction Progress (actual ledger changes).
    """
    model_config = ConfigDict(from_attributes=True)

    roadmap_id: int
    roadmap_code: str
    target_reduction_percent: float
    baseline_emissions_tco2e: float
    target_emissions_tco2e: float
    reduction_gap_tco2e: float
    total_items: int
    completed_items: int
    in_progress_items: int
    blocked_items: int
    not_started_items: int
    roadmap_progress_percent: float
    emissions_progress_status: str
    actual_change_percent: Optional[float] = None
    actual_change_tco2e: Optional[float] = None
    latest_actual_period: Optional[str] = None
    latest_actual_emissions_tco2e: Optional[float] = None
    feasibility_status: str
    feasibility_explanation: str


class RoadmapListResponse(BaseModel):
    """
    Paginated/filtered list of roadmaps.
    """
    model_config = ConfigDict(from_attributes=True)

    total: int
    items: List[ReductionRoadmapResponse]
