"""
schemas/reduction_measurement.py — Pydantic Schemas for Reduction Measurement & Verification (Step 17).
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ReductionMeasurementCreate(BaseModel):
    reference_period: str  # e.g., '2024-10'
    measurement_period: str  # e.g., '2025-10'
    measurement_scope_type: str = "TOTAL"  # TOTAL, SCOPE, CATEGORY, ACTIVITY
    measurement_scope: Optional[str] = None
    measurement_category: Optional[str] = None
    measurement_activity_type: Optional[str] = None
    methodology_note: Optional[str] = None


class ReductionMeasurementStatusUpdate(BaseModel):
    status: str  # DRAFT, READY, MEASURED, NEEDS_REVIEW, FINALIZED
    note: Optional[str] = None


class ReductionMeasurementEventResponse(BaseModel):
    id: int
    measurement_id: int
    event_type: str
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReductionMeasurementResponse(BaseModel):
    id: int
    project_id: int
    measurement_scope_type: str
    measurement_scope: Optional[str] = None
    measurement_category: Optional[str] = None
    measurement_activity_type: Optional[str] = None
    reference_period: str
    measurement_period: str
    reference_year: Optional[int] = None
    measurement_year: Optional[int] = None
    reference_co2e: Optional[float] = None
    measurement_co2e: Optional[float] = None
    reference_co2e_unit: str = "kgCO2e"
    measurement_co2e_unit: str = "kgCO2e"
    reference_co2e_t: Optional[float] = None
    measurement_co2e_t: Optional[float] = None
    observed_change: Optional[float] = None
    observed_change_t: Optional[float] = None
    observed_change_percentage: Optional[float] = None
    measurement_status: str
    evidence_status: str
    verification_status: str
    methodology_note: Optional[str] = None
    limitations: str
    measurement_version: int
    calculated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    events: List[ReductionMeasurementEventResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ReductionMeasurementList(BaseModel):
    total: int
    items: List[ReductionMeasurementResponse] = Field(default_factory=list)


class ReductionMeasurementComparison(BaseModel):
    measurement_id: int
    project_id: int
    reference_period: str
    measurement_period: str
    reference_co2e_t: Optional[float] = None
    measurement_co2e_t: Optional[float] = None
    observed_change_t: Optional[float] = None
    observed_change_percentage: Optional[float] = None
    measurement_status: str
    evidence_status: str
    verification_status: str
    is_comparable: bool
    reason: Optional[str] = None
    limitations: str
