from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, field_validator, model_validator

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

class RAGMetric(BaseModel):
    metric_id: Optional[int] = None
    metric_name: str
    metric_type: str
    category: str
    value: float
    unit: str
    period: Optional[str] = None
    document_id: int
    document_name: str
    source_field: str
    source_text: Optional[str] = None
    verification_status: str = "AI_EXTRACTED"
    confidence: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

class RAGContext(BaseModel):
    query: str
    intent: str
    retrieval_mode: str
    document_id: Optional[int] = None
    chunks: List[Any] = Field(default_factory=list)
    rag_metrics: List[RAGMetric] = Field(default_factory=list)
    sources: List[SourceContext] = Field(default_factory=list)
    insights: List[InsightContext] = Field(default_factory=list)
    recommendations: List[Any] = Field(default_factory=list)
    attention_items: List[Any] = Field(default_factory=list)
    review_items: List[ReviewContext] = Field(default_factory=list)
    documents: List[DocumentContext] = Field(default_factory=list)
    historical_comparisons: List[Dict[str, Any]] = Field(default_factory=list)
    summary: CopilotSummary = Field(default_factory=CopilotSummary)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

class CopilotAction(BaseModel):
    type: str = Field(default="VIEW_DOCUMENT", description="Action type: VIEW_DOCUMENT, VIEW_METRIC")
    label: str = Field(..., description="Action button label")
    target: Optional[str] = Field(default=None, description="Navigation target URL or route")

class CopilotRequest(BaseModel):
    message: Optional[str] = Field(default=None, description="User question or prompt for Copilot")
    question: Optional[str] = Field(default=None, description="Alternative field for user question")
    document_id: Optional[int] = Field(default=None, description="Target document ID for document-scoped contextual Q&A")
    history: Optional[List[Dict[str, str]]] = Field(default_factory=list, description="Recent conversation turns for follow-up resolution")

    @model_validator(mode="before")
    @classmethod
    def validate_payload(cls, values: Any) -> Any:
        if isinstance(values, dict):
            msg = values.get("message") if "message" in values else values.get("question")
            if msg is None:
                raise ValueError("Message cannot be empty or whitespace only.")
            cleaned = str(msg).strip()
            if not cleaned:
                raise ValueError("Message cannot be empty or whitespace only.")
            if len(cleaned) > 2000:
                raise ValueError("Message exceeds maximum allowed length of 2000 characters.")
            values["message"] = cleaned
        return values

class RecommendationItem(BaseModel):
    id: str = Field(..., description="Unique deterministic identifier for the recommendation")
    category: str = Field(..., description="Allowed: ENERGY, FUEL, WATER, WASTE, EMISSIONS, DATA_QUALITY")
    priority: str = Field(..., description="Allowed: HIGH, MEDIUM, LOW")
    title: str = Field(..., description="Clear operational focus area title")
    reason: str = Field(..., description="Factual underlying reason supported by data")
    metric_type: Optional[str] = Field(default=None, description="Associated metric type")
    current_value: Optional[float] = Field(default=None, description="Current metric value")
    previous_value: Optional[float] = Field(default=None, description="Previous period metric value")
    unit: Optional[str] = Field(default=None, description="Unit of measurement")
    percentage_change: Optional[float] = Field(default=None, description="Percentage change period-over-period")
    source_document_id: Optional[int] = Field(default=None, description="Source document ID")
    evidence: Optional[str] = Field(default=None, description="Verbatim source text excerpt")
    suggested_actions: List[str] = Field(default_factory=list, description="List of conservative, non-prescriptive next steps")
    limitations: Optional[str] = Field(default=None, description="Transparent limitation or assumption disclaimer")

class CopilotResponse(BaseModel):
    answer: str = Field(..., description="Assistant response text")
    intent: Optional[str] = Field(default=None, description="Identified user query intent")
    sources: List[SourceContext] = Field(default_factory=list, description="Referenced document or metric sources")
    actions: List[Any] = Field(default_factory=list, description="Suggested follow-up actions or navigation targets")
    recommendations: List[RecommendationItem] = Field(default_factory=list, description="Structured actionable recommendation items")
    context_available: bool = Field(default=False, description="Whether grounded context was built")
    summary: Optional[CopilotSummary] = Field(default=None, description="High level metric summary counts")

class AttentionItem(BaseModel):
    id: str = Field(..., description="Unique deterministic identifier for the attention item")
    type: str = Field(..., description="Allowed: DOCUMENT_REVIEW, MISSING_DATA, METRIC_CHANGE, EVIDENCE_ISSUE, LOW_CONFIDENCE, CLASSIFICATION_CONFLICT, UNVERIFIED_DATA")
    severity: str = Field(..., description="Allowed: HIGH, MEDIUM, LOW")
    title: str = Field(..., description="Short clear title")
    message: str = Field(..., description="Calm, operational explanation")
    reason: Optional[str] = Field(default=None, description="Specific underlying operational or extraction reason")
    company_name: Optional[str] = Field(default=None, description="Company or business name")
    document_id: Optional[int] = Field(default=None, description="Associated document ID")
    metric_type: Optional[str] = Field(default=None, description="Associated metric type")
    current_value: Optional[float] = Field(default=None, description="Current metric value")
    previous_value: Optional[float] = Field(default=None, description="Previous period metric value")
    unit: Optional[str] = Field(default=None, description="Unit of measurement")
    percentage_change: Optional[float] = Field(default=None, description="Percentage change period-over-period")
    source_document_id: Optional[int] = Field(default=None, description="Source document ID")
    action_type: str = Field(default="VIEW_DOCUMENT", description="Action type: VIEW_DOCUMENT, VIEW_METRIC, VIEW_EVIDENCE")
    action_label: str = Field(default="Review Document", description="Action button label")
    action_target: Optional[str] = Field(default=None, description="Navigation target URL or route")

class AttentionSummary(BaseModel):
    total: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    documents_needing_review: int = 0
    missing_data_items: int = 0
    metric_changes: int = 0

class AttentionResponse(BaseModel):
    items: List[AttentionItem] = Field(default_factory=list, description="Sorted list of proactive attention items")
    summary: AttentionSummary = Field(default_factory=AttentionSummary, description="Summary counts by severity and category")



