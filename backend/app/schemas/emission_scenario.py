"""
schemas/emission_scenario.py — Pydantic Schemas for Emissions Scenario Engine (Step 22C).

Defines strict request and response validation for what-if scenarios, input assumptions,
source-level results with factor snapshots, and target comparison summaries.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from backend.app.config.emission_scenario import (
    VALID_SCENARIO_TYPES,
    VALID_SCENARIO_STATUSES,
    VALID_QUANTIFICATION_STATUSES,
    VALID_TARGET_STATUSES,
    SCENARIO_TYPE_REDUCE_ACTIVITY,
    SCENARIO_TYPE_INCREASE_ACTIVITY,
    SCENARIO_TYPE_REPLACE_SOURCE,
    SCENARIO_TYPE_SHIFT_SOURCE,
    SCENARIO_TYPE_ADD_SOURCE,
    SCENARIO_TYPE_REMOVE_SOURCE,
)


class ScenarioInputCreate(BaseModel):
    """
    Detailed assumption line item specifying a modeled activity or source change.
    """
    model_config = ConfigDict(extra="forbid")

    activity_data_id: Optional[int] = Field(None, description="Linked ActivityData ID from verified baseline")
    source_ledger_entry_id: Optional[int] = Field(None, description="Linked CarbonLedgerEntry ID")
    activity_type: Optional[str] = Field(None, description="Activity type (e.g. purchased_electricity, diesel)")
    change_type: str = Field(..., description="Change type (REDUCE_ACTIVITY, REPLACE_SOURCE, etc.)")
    change_percent: Optional[Decimal] = Field(None, description="Percentage change (0-100% for reduction/replacement)")
    replacement_source: Optional[str] = Field(None, description="Replacement source name or activity type (e.g. solar_electricity)")
    replacement_activity_data_id: Optional[int] = Field(None, description="Existing ActivityData ID for replacement source")
    assumption: Optional[str] = Field(None, description="Explanatory text for the assumption")
    evidence_reference: Optional[str] = Field(None, description="Evidence reference or documentation citation")

    @field_validator("change_type")
    @classmethod
    def validate_change_type(cls, v: str) -> str:
        if v not in VALID_SCENARIO_TYPES:
            raise ValueError(f"Invalid change_type '{v}'. Must be one of: {sorted(VALID_SCENARIO_TYPES)}")
        return v

    @field_validator("change_percent")
    @classmethod
    def validate_change_percent(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None:
            if v < Decimal("0.0"):
                raise ValueError("change_percent cannot be negative")
        return v

    @model_validator(mode="after")
    def validate_input_rules(self):
        # 1. Bounds check for reduction/replacement/shift/removal
        if self.change_type in (SCENARIO_TYPE_REDUCE_ACTIVITY, SCENARIO_TYPE_REPLACE_SOURCE, SCENARIO_TYPE_SHIFT_SOURCE, SCENARIO_TYPE_REMOVE_SOURCE):
            if self.change_percent is not None and self.change_percent > Decimal("100.0"):
                raise ValueError(f"change_percent cannot exceed 100% for {self.change_type}")

        # 2. Refinement 1: Safeguard on ADD_SOURCE — Must link to existing ActivityData
        if self.change_type == SCENARIO_TYPE_ADD_SOURCE:
            if not self.activity_data_id and not self.activity_type:
                raise ValueError("ADD_SOURCE requires an existing ActivityData ID or a verified activity_type to prevent ungrounded assumptions.")

        # 3. REPLACE_SOURCE / SHIFT_SOURCE require a replacement source specification
        if self.change_type in (SCENARIO_TYPE_REPLACE_SOURCE, SCENARIO_TYPE_SHIFT_SOURCE):
            if not self.replacement_source and not self.replacement_activity_data_id:
                raise ValueError(f"{self.change_type} requires a replacement_source or replacement_activity_data_id")

        return self


class ScenarioCreateRequest(BaseModel):
    """
    Request payload to initialize and execute a what-if decarbonization scenario.
    """
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=255, description="Descriptive name for the scenario")
    description: Optional[str] = Field(None, description="Scenario assumptions narrative")
    document_id: Optional[int] = Field(None, description="Document scope for baseline")
    roadmap_id: Optional[int] = Field(None, description="Linked ReductionRoadmap ID for target comparison")
    scenario_type: str = Field(..., description="Primary scenario type")
    baseline_period: Optional[str] = Field(None, description="Explicit baseline period (optional)")

    # Structured inputs array
    inputs: Optional[List[ScenarioInputCreate]] = Field(None, description="List of detailed input modifications")

    # Convenience shortcut fields for single-action scenarios
    target_activity_data_id: Optional[int] = Field(None, description="Convenience: target activity ID to modify")
    source_activity_data_id: Optional[int] = Field(None, description="Convenience: source activity ID for replacement")
    change_percent: Optional[Decimal] = Field(None, description="Convenience: change percentage")
    replacement_activity_type: Optional[str] = Field(None, description="Convenience: replacement activity type")
    replacement_percent: Optional[Decimal] = Field(None, description="Convenience: replacement percentage")

    @field_validator("scenario_type")
    @classmethod
    def validate_scenario_type(cls, v: str) -> str:
        if v not in VALID_SCENARIO_TYPES:
            raise ValueError(f"Invalid scenario_type '{v}'. Must be one of: {sorted(VALID_SCENARIO_TYPES)}")
        return v

    @field_validator("change_percent", "replacement_percent")
    @classmethod
    def validate_percent_non_negative(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < Decimal("0.0"):
            raise ValueError("Percentage change cannot be negative")
        return v


class ScenarioUpdateRequest(BaseModel):
    """
    Update scenario metadata or status.
    """
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_SCENARIO_STATUSES:
            raise ValueError(f"Invalid status '{v}'. Must be one of: {sorted(VALID_SCENARIO_STATUSES)}")
        return v


class ScenarioInputResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scenario_id: int
    activity_data_id: Optional[int] = None
    source_ledger_entry_id: Optional[int] = None
    activity_type: str
    category: str
    scope: Optional[str] = None
    baseline_quantity: float
    baseline_unit: str
    scenario_quantity: float
    scenario_unit: str
    change_type: str
    change_percent: Optional[float] = None
    replacement_source: Optional[str] = None
    replacement_activity_data_id: Optional[int] = None
    emission_factor_id: Optional[int] = None
    replacement_emission_factor_id: Optional[int] = None
    assumption: Optional[str] = None
    evidence_reference: Optional[str] = None
    created_at: Optional[datetime] = None


class ScenarioResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scenario_id: int
    source_name: str
    scope: Optional[str] = None
    category: str
    activity_type: str
    baseline_quantity: float
    scenario_quantity: float
    unit: str
    baseline_emissions_kgco2e: float
    scenario_emissions_kgco2e: Optional[float] = None
    reduction_kgco2e: Optional[float] = None
    baseline_factor: Optional[float] = None
    scenario_factor: Optional[float] = None
    factor_unit: Optional[str] = None
    factor_source: Optional[str] = None
    factor_version: Optional[str] = None
    factor_code: Optional[str] = None
    calculation_formula: Optional[str] = None
    status: str
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


class EmissionScenarioDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scenario_code: str
    document_id: Optional[int] = None
    roadmap_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    scenario_type: str
    status: str
    baseline_period: Optional[str] = None
    baseline_emissions_kgco2e: float
    baseline_emissions_tco2e: float
    scenario_emissions_kgco2e: Optional[float] = None
    scenario_emissions_tco2e: Optional[float] = None
    reduction_kgco2e: Optional[float] = None
    reduction_tco2e: Optional[float] = None
    reduction_percent: Optional[float] = None
    remaining_target_gap_kgco2e: Optional[float] = None
    remaining_target_gap_tco2e: Optional[float] = None
    target_status: str
    quantification_status: str
    assumption_summary: Optional[str] = None
    limitation_summary: Optional[str] = None
    calculation_version: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    inputs: List[ScenarioInputResponse] = []
    results: List[ScenarioResultResponse] = []


class EmissionScenarioListResponse(BaseModel):
    total: int
    items: List[EmissionScenarioDetailResponse]
