"""
schemas/proactive_agent.py — Pydantic Schemas for Proactive AI Sustainability Agent (Step 23 & Improvement Patches).
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AgentActionResponse(BaseModel):
    id: int
    document_id: Optional[int] = None
    action_type: str
    category: str
    queue_type: str = "REDUCTION"
    action_queue: Optional[str] = "REDUCTION"
    priority: str
    priority_level: Optional[str] = None
    priority_score: float = 0.0
    priority_source: str = "REDUCTION_INTELLIGENCE"
    deterministic_score: Optional[float] = None
    title: str
    summary: str
    description: Optional[str] = None
    why_it_matters: str
    recommended_action: str

    # Structured Explanation Contract (Patch 5)
    what: Optional[str] = None
    why: Optional[str] = None
    next: Optional[str] = None
    evidence: Optional[str] = None
    follow_up: Optional[str] = None
    limitation: Optional[str] = None

    # Dependency Graph (Patch 3)
    parent_action_id: Optional[int] = None
    blocks_action_id: Optional[int] = None
    dependency_status: str = "NONE"

    # Provenance Lineage
    source_type: str
    source_id: Optional[str] = None
    source_document_id: Optional[int] = None
    reporting_period: Optional[str] = None
    metric_value: Optional[float] = None
    metric_unit: Optional[str] = None
    evidence_reference: Optional[str] = None

    status: str
    due_context: Optional[str] = None
    dedup_key: str
    agent_version: str = "1.0"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AgentActionListResponse(BaseModel):
    actions: List[AgentActionResponse]
    items: Optional[List[AgentActionResponse]] = None
    total: int
    open_count: int
    in_progress_count: int
    completed_count: int
    dismissed_count: int
    reduction_count: int
    data_quality_count: int

    def __init__(self, **kwargs):
        if "items" not in kwargs and "actions" in kwargs:
            kwargs["items"] = kwargs["actions"]
        elif "actions" not in kwargs and "items" in kwargs:
            kwargs["actions"] = kwargs["items"]
        super().__init__(**kwargs)


class AgentActionUpdate(BaseModel):
    status: Optional[str] = None
    due_context: Optional[str] = None
    recommended_action: Optional[str] = None
    next_step: Optional[str] = None


class AgentActionEventResponse(BaseModel):
    id: int
    action_id: int
    event_type: str
    previous_status: Optional[str] = None
    new_status: str
    actor_type: str = "SYSTEM"
    reason: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AgentActionEventListResponse(BaseModel):
    events: List[AgentActionEventResponse]
    total: int


class AgentBriefResponse(BaseModel):
    """
    Structured AI Sustainability Brief (Patch 4 & Patch 8).
    Strictly separates Actuals, Forecasts (FORECAST — NOT ACTUAL), and Scenarios (SCENARIO — NOT ACTUAL).
    """
    title: str = "AI Sustainability Brief"
    generated_at: datetime
    agent_version: str = "1.0"
    current_period: Optional[str] = None
    latest_actual_reporting_period: Optional[str] = None
    current_posted_footprint: Optional[float] = None  # in tCO2e
    actual_footprint_tco2e: Optional[float] = None
    period_to_period_delta_tco2e: Optional[float] = None
    last_evaluated: Optional[datetime] = None
    open_action_count: int = 0
    attention_count: int = 0
    queue_a_count: int = 0
    queue_b_count: int = 0
    ready_actions_count: int = 0
    critical_count: int = 0
    high_count: int = 0

    def __init__(self, **kwargs):
        if "actual_footprint_tco2e" not in kwargs and "current_posted_footprint" in kwargs:
            kwargs["actual_footprint_tco2e"] = kwargs["current_posted_footprint"]
        elif "current_posted_footprint" not in kwargs and "actual_footprint_tco2e" in kwargs:
            kwargs["current_posted_footprint"] = kwargs["actual_footprint_tco2e"]
        if "latest_actual_reporting_period" not in kwargs and "current_period" in kwargs:
            kwargs["latest_actual_reporting_period"] = kwargs["current_period"]
        super().__init__(**kwargs)

    # Queue A: Reduction Actions (Top 3-5)
    top_actions: List[AgentActionResponse] = Field(default_factory=list)

    # Queue B: Data Quality Blockers (Patch 2)
    data_quality_blockers: List[AgentActionResponse] = Field(default_factory=list)

    # Dependency Graph: Next Ready Actions (Patch 3)
    ready_actions: List[AgentActionResponse] = Field(default_factory=list)

    # Verified Period Changes (no manufactured change if no prior actual)
    recent_changes: List[Dict[str, Any]] = Field(default_factory=list)

    # Forecast Signal (Labeled: FORECAST — NOT ACTUAL)
    forecast_signal: Dict[str, Any] = Field(default_factory=dict)

    # Roadmap Progress
    roadmap_status: Dict[str, Any] = Field(default_factory=dict)

    # Scenario Status (Labeled: SCENARIO — NOT ACTUAL)
    scenario_status: Dict[str, Any] = Field(default_factory=dict)


class AgentRunRequest(BaseModel):
    document_id: Optional[int] = None
    force_recalculate: bool = False


class AgentRunResponse(BaseModel):
    status: str
    actions_evaluated: int
    new_actions_created: int
    updated_actions: int
    active_actions_count: int
    last_evaluated: datetime
    timestamp: Optional[datetime] = None
    agent_version: str = "1.0"

    def __init__(self, **kwargs):
        if "timestamp" not in kwargs and "last_evaluated" in kwargs:
            kwargs["timestamp"] = kwargs["last_evaluated"]
        super().__init__(**kwargs)


class AgentStatusResponse(BaseModel):
    agent_version: str = "1.0"
    engine_version: str = "1.0"
    last_evaluated: Optional[datetime] = None
    total_actions: int = 0
    open_actions: int = 0
    in_progress_actions: int = 0
    completed_actions: int = 0
    active_actions_count: int = 0
    reduction_queue_count: int = 0
    data_quality_queue_count: int = 0
    ready_actions_count: int = 0


class AgentExplanationResponse(BaseModel):
    action_id: int
    title: str
    what: str
    why: str
    next: str
    evidence: Optional[str] = None
    follow_up: Optional[str] = None
    limitation: Optional[str] = None
