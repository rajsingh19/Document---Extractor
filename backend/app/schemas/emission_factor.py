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


# ── STEP 12B RESOLUTION SCHEMAS ───────────────────────────────────────────────

class FactorResolutionRequest(BaseModel):
    """
    Structured resolution request for deterministic emission factor candidate resolution.
    Arbitrary extra fields are strictly forbidden.
    """
    model_config = {"extra": "forbid"}

    activity_type: str = Field(..., description="Activity identifier (e.g. purchased_electricity, diesel)")
    activity_unit: str = Field(..., description="Activity unit of measurement (e.g. kWh, L, scm, tonne_km)")
    geography: Optional[str] = Field(default=None, description="Geographic boundary (e.g. India, Global)")
    year: Optional[int] = Field(default=None, description="Applicable calendar year (e.g. 2024, 2025)")
    scope: Optional[str] = Field(default=None, description="Target scope filter (SCOPE_1, SCOPE_2, SCOPE_3)")
    category: Optional[str] = Field(default=None, description="Optional category filter (ENERGY, FUEL, etc.)")
    preferred_factor_code: Optional[str] = Field(default=None, description="Optional specific factor code to test")

    @field_validator("activity_type", "activity_unit")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty or whitespace only")
        return cleaned


class FactorResolutionCandidate(BaseModel):
    """
    Candidate emission factor with transparent explanation of why it was matched or rejected.
    """
    factor_id: int
    factor_code: str
    factor_name: str
    activity_type: str
    activity_unit: str
    factor_unit: str
    geography: str
    applicable_year: Optional[int] = None
    scope: str
    factor_value: float
    version: str
    status: str
    source_name: str
    source_reference: Optional[str] = None
    match_reasons: List[str] = Field(default_factory=list)
    rejection_reasons: List[str] = Field(default_factory=list)


class FactorResolutionResponse(BaseModel):
    """
    Deterministic response from the EmissionFactorResolver.
    Never guesses; provides auditable reasons for factor selection or rejection.
    """
    status: str = Field(..., description="MATCHED, NO_MATCH, MULTIPLE_MATCHES, INVALID_REQUEST")
    message: str = Field(..., description="Human-readable summary of the resolution decision")
    selected_factor: Optional[FactorResolutionCandidate] = None
    candidates: List[FactorResolutionCandidate] = Field(default_factory=list)
    rejected_candidates: List[FactorResolutionCandidate] = Field(default_factory=list)
    resolution_reasons: List[str] = Field(default_factory=list)
    resolution_version: str = Field(default="1.0", description="Resolver algorithm version for auditability")

