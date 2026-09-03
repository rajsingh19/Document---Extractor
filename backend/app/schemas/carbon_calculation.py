"""
schemas/carbon_calculation.py — Pydantic Schemas for Carbon Calculations (Step 13).
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class CarbonCalculationRequest(BaseModel):
    """
    Request payload to calculate emissions for a single ActivityData record.
    Strictly accepts only activity_data_id and force_recalculate (NO geography override).
    """
    activity_data_id: int = Field(..., description="ID of the canonical ActivityData record to calculate")
    force_recalculate: bool = Field(default=False, description="Whether to recalculate if an existing calculation exists")


class CarbonCalculationResponse(BaseModel):
    """
    Full serializable representation of a CarbonCalculation record.
    """
    id: int
    activity_data_id: int
    document_id: Optional[int] = None
    metric_id: Optional[int] = None
    activity_type: str
    activity_role: str
    activity_group_id: Optional[str] = None
    quantity: float
    activity_unit: str
    emission_factor_id: Optional[int] = None
    factor_code: Optional[str] = None
    factor_name: Optional[str] = None
    factor_value: Optional[float] = None
    factor_unit: Optional[str] = None
    factor_version: Optional[str] = None
    factor_source: Optional[str] = None
    geography: Optional[str] = None
    reporting_period: Optional[str] = None
    reporting_year: Optional[int] = None
    scope: Optional[str] = None
    calculated_co2e: Optional[float] = None
    calculated_co2e_unit: str = "kgCO2e"
    formula: Optional[str] = None
    calculation_version: str = "1.0"
    status: str
    calculation_reason: Optional[str] = None
    source_field: Optional[str] = None
    source_text: Optional[str] = None
    page: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CarbonCalculationListResponse(BaseModel):
    total: int
    items: List[CarbonCalculationResponse]


class DocumentCarbonCalculationSummary(BaseModel):
    """
    Aggregated document-level carbon calculation summary with double-counting protection.
    """
    document_id: int
    total_activity_records: int = 0
    calculated_records: int = 0
    ineligible_records: int = 0
    no_factor_records: int = 0
    multiple_factor_records: int = 0
    invalid_records: int = 0
    total_calculated_co2e: Optional[float] = None
    total_calculated_co2e_unit: str = "kgCO2e"
    scope_1_calculated_co2e: Optional[float] = None
    scope_2_calculated_co2e: Optional[float] = None
    scope_3_calculated_co2e: Optional[float] = None
    calculations: List[CarbonCalculationResponse] = Field(default_factory=list)
