"""
schemas/reduction_intelligence.py — Pydantic Schemas for Reduction Opportunity Intelligence Engine (Step 22A).

CRITICAL BOUNDARIES:
- Strictly formats and validates deterministic priority calculations.
- Never accepts arbitrary hallucinated LLM reduction percentages or savings.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ReductionPriorityResponse(BaseModel):
    """
    Standard DTO for a deterministic reduction priority item.
    """
    id: Optional[int] = None
    priority_code: str
    document_id: Optional[int] = None
    opportunity_id: Optional[int] = None
    project_id: Optional[int] = None
    scope: Optional[str] = None
    category: Optional[str] = None
    activity_type: Optional[str] = None
    priority_rank: Optional[int] = None
    priority_score: float
    priority_level: str  # CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL

    # Transparent score breakdown
    impact_score: float
    trend_score: float
    forecast_score: float
    persistence_score: float
    actionability_score: float
    data_quality_score: float
    blocker_score: float

    title: str
    reason: str

    current_emissions_kgco2e: float
    current_emissions_tco2e: float
    previous_emissions_kgco2e: Optional[float] = None
    change_percent: Optional[float] = None
    forecast_emissions_kgco2e: Optional[float] = None

    source_reference: Optional[str] = None
    evidence_reference: Optional[str] = None
    calculation_version: str = "1.0"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ReductionPriorityDetail(ReductionPriorityResponse):
    """
    Extended DTO with audit lineage, linked entities, and transparent calculation limits.
    """
    percentage_of_total: Optional[float] = None
    trend_description: Optional[str] = None
    forecast_status: Optional[str] = None
    existing_project_status: Optional[str] = None
    is_data_quality_issue: bool = False
    action_type: str = "CONCRETE"  # CONCRETE, DATA_GAP, ANALYSIS_REQUIRED
    limitations: Optional[str] = None
    score_breakdown: Optional[Dict[str, Any]] = None


class ReductionPriorityList(BaseModel):
    """
    Paginated/Filtered list of reduction priorities.
    """
    total: int
    items: List[ReductionPriorityResponse] = []


class ReductionIntelligenceSummary(BaseModel):
    """
    Top-level executive summary KPIs for the reduction intelligence dashboard.
    """
    total_priorities: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    informational: int = 0
    top_priority: Optional[str] = None
    top_priority_score: Optional[float] = None
    top_emitting_source: Optional[str] = None
    largest_increasing_source: Optional[str] = None
    forecast_available: bool = False
    forecast_concern: Optional[str] = None
    data_quality_blockers: Optional[str] = None
    existing_project_coverage: Optional[str] = None


class RecalculateResponse(BaseModel):
    """
    Response returned when deterministic recalculation is triggered.
    """
    status: str = "SUCCESS"
    message: str
    priorities_generated: int
    version: str = "1.0"
    generated_at: datetime = Field(default_factory=datetime.utcnow)
