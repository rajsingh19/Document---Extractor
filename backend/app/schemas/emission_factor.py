"""
schemas/emission_factor.py — Pydantic Schemas for Emission Factors (Step 12A).
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class EmissionFactorBase(BaseModel):
    factor_code: str = Field(..., description="Unique alphanumeric factor identifier")
    factor_name: str = Field(..., description="Human-readable descriptive factor name")
    activity_type: str = Field(..., description="Activity type: purchased_electricity, diesel, petrol, natural_gas, lpg, water, waste, freight, other")
    category: str = Field(..., description="Category: ENERGY, FUEL, TRANSPORT, WATER, WASTE, OTHER")
    scope: str = Field(..., description="Scope: SCOPE_1, SCOPE_2, SCOPE_3, NOT_APPLICABLE")
    factor_value: float = Field(..., description="Numerical emission factor value. Must be positive.")
    factor_unit: str = Field(..., description="Factor unit: e.g. kgCO2e/kWh, kgCO2e/L, kgCO2e/tonne_km")
    activity_unit: str = Field(..., description="Expected activity unit: e.g. kWh, L, scm, tonne_km")
    geography: str = Field(default="GLOBAL", description="Geographic boundary: e.g. India, IN, Global")
    applicable_year: Optional[int] = Field(default=None, description="Applicable year: e.g. 2024, 2025")
    source_name: str = Field(..., description="Source authority or dataset name")
    source_reference: Optional[str] = Field(default=None, description="Specific report, table, or URL reference")
    methodology: Optional[str] = Field(default=None, description="Calculation methodology or tier description")
    version: str = Field(default="1.0", description="Dataset or factor version")
    effective_from: Optional[str] = Field(default=None, description="Start date of validity (YYYY-MM-DD)")
    effective_to: Optional[str] = Field(default=None, description="End date of validity (YYYY-MM-DD)")
    status: str = Field(default="ACTIVE", description="Status: ACTIVE, INACTIVE, DRAFT")
    notes: Optional[str] = Field(default=None, description="Audit or compliance notes")

    @field_validator("factor_value")
    @classmethod
    def validate_factor_value(cls, v: float) -> float:
        if v < 0:
            raise ValueError("factor_value must be a non-negative number")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        upper_v = v.upper().strip()
        if upper_v not in ("ACTIVE", "INACTIVE", "DRAFT"):
            raise ValueError("status must be one of: ACTIVE, INACTIVE, DRAFT")
        return upper_v

    @field_validator("scope")
    @classmethod
    def validate_scope(cls, v: str) -> str:
        upper_v = v.upper().strip()
        if upper_v not in ("SCOPE_1", "SCOPE_2", "SCOPE_3", "NOT_APPLICABLE"):
            raise ValueError("scope must be one of: SCOPE_1, SCOPE_2, SCOPE_3, NOT_APPLICABLE")
        return upper_v


class EmissionFactorCreate(EmissionFactorBase):
    pass


class EmissionFactorUpdate(BaseModel):
    factor_name: Optional[str] = None
    factor_value: Optional[float] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class EmissionFactorResponse(EmissionFactorBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class EmissionFactorListResponse(BaseModel):
    total: int
    factors: List[EmissionFactorResponse]


class CandidateMatchResponse(BaseModel):
    status: str = Field(..., description="Matching status: MATCHED, NO_MATCH, MULTIPLE_MATCHES, INVALID_REQUEST")
    message: str = Field(..., description="Deterministic explanation of the match outcome")
    matched_factor: Optional[EmissionFactorResponse] = None
    candidate_factors: List[EmissionFactorResponse] = Field(default_factory=list)
    match_count: int = 0
