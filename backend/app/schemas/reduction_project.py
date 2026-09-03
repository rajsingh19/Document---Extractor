"""
schemas/reduction_project.py — Pydantic Schemas for Carbon Reduction Projects & Audit Trail (Step 16).
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ReductionProjectCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category: str
    scope: Optional[str] = None
    opportunity_id: Optional[int] = None
    activity_type: Optional[str] = None
    owner: Optional[str] = None
    start_date: Optional[datetime] = None
    target_date: Optional[datetime] = None
    baseline_period: Optional[str] = None
    baseline_co2e: Optional[float] = None
    baseline_co2e_unit: str = "kgCO2e"
    target_description: Optional[str] = None
    notes: Optional[str] = None


class ReductionProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    scope: Optional[str] = None
    owner: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    target_date: Optional[datetime] = None
    baseline_period: Optional[str] = None
    baseline_co2e: Optional[float] = None
    baseline_co2e_unit: Optional[str] = None
    target_description: Optional[str] = None
    actual_post_project_co2e: Optional[float] = None
    actual_post_project_unit: Optional[str] = None
    notes: Optional[str] = None


class ReductionProjectStatusUpdate(BaseModel):
    status: str  # PLANNED, IN_PROGRESS, ON_HOLD, COMPLETED, CANCELLED
    note: Optional[str] = None


class ReductionProjectEventResponse(BaseModel):
    id: int
    project_id: int
    event_type: str
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReductionProjectResponse(BaseModel):
    id: int
    project_code: str
    title: str
    description: Optional[str] = None
    category: str
    scope: Optional[str] = None
    opportunity_id: Optional[int] = None
    activity_type: Optional[str] = None
    status: str
    owner: Optional[str] = None
    start_date: Optional[datetime] = None
    target_date: Optional[datetime] = None
    baseline_period: Optional[str] = None
    baseline_co2e: Optional[float] = None
    baseline_co2e_unit: str = "kgCO2e"
    baseline_co2e_t: Optional[float] = None
    target_description: Optional[str] = None
    actual_post_project_co2e: Optional[float] = None
    actual_post_project_unit: str = "kgCO2e"
    actual_post_project_t: Optional[float] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    events: List[ReductionProjectEventResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ReductionProjectList(BaseModel):
    total: int
    items: List[ReductionProjectResponse] = Field(default_factory=list)
