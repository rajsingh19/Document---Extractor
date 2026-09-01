from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, field_validator

class DocumentContext(BaseModel):
    document_id: int
    filename: str
    document_type: Optional[str] = None
    company_name: Optional[str] = None
    reporting_period: Optional[str] = None
    status: str
    quality_score: float
    verification_status: str

class MetricContext(BaseModel):
    metric_type: str
    category: str
    value: float
    unit: str
    period: Optional[str] = None
    confidence: Optional[float] = None
    verification_status: str
    source_document_id: int

class InsightContext(BaseModel):
    category: str
    severity: str
    metric_type: Optional[str] = None
    message: str
    current_value: Optional[float] = None
    previous_value: Optional[float] = None
    percentage_change: Optional[float] = None
    source_document_id: Optional[int] = None

class ReviewContext(BaseModel):
    document_id: int
    filename: str
    reason: str
    quality_score: float
    affected_fields: List[str] = Field(default_factory=list)

class SourceContext(BaseModel):
    document_id: int
    document_name: str
    field: str
    value: Optional[Any] = None
    unit: Optional[str] = None
    source_text: Optional[str] = None

class CopilotSummary(BaseModel):
    document_count: int = 0
    documents_needing_review: int = 0
    verified_documents: int = 0
    metric_count: int = 0
    active_attention_items: int = 0

class CopilotContext(BaseModel):
    intent: str
    query: str
    summary: CopilotSummary
    documents: List[DocumentContext] = Field(default_factory=list)
    metrics: List[MetricContext] = Field(default_factory=list)
    insights: List[InsightContext] = Field(default_factory=list)
    review_items: List[ReviewContext] = Field(default_factory=list)
    sources: List[SourceContext] = Field(default_factory=list)
    historical_comparisons: List[Dict[str, Any]] = Field(default_factory=list)

class CopilotRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User question or prompt for Copilot")

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Message cannot be empty or whitespace only.")
        return cleaned

class CopilotResponse(BaseModel):
    answer: str = Field(..., description="Assistant response text")
    intent: Optional[str] = Field(default=None, description="Identified user query intent")
    sources: List[SourceContext] = Field(default_factory=list, description="Referenced document or metric sources")
    actions: List[str] = Field(default_factory=list, description="Suggested follow-up actions")
    context_available: bool = Field(default=False, description="Whether grounded context was built")
    summary: Optional[CopilotSummary] = Field(default=None, description="High level metric summary counts")
