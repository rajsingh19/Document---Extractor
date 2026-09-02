"""
schemas/report.py — Deterministic Report Data Models for Step 11F.

All fields come from SQL (numerical truth), evidence lineage (provenance),
InsightsService (deterministic interpretation), and CopilotRecommendationService
(deterministic recommendations). No LLM-invented values.
"""
from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


class ReportMetadata(BaseModel):
    """Document-level metadata for the report header."""
    report_id: str = Field(..., description="Unique report identifier (deterministic from doc_id + timestamp)")
    document_id: int
    document_name: str
    company_name: Optional[str] = None
    document_type: Optional[str] = None
    reporting_period: Optional[str] = None
    generated_at: str = Field(..., description="ISO 8601 timestamp of report generation")
    verification_status: Optional[str] = None   # VERIFIED, NEEDS_REVIEW, etc.
    quality_score: Optional[float] = None        # 0–100
    review_status: Optional[str] = None
    extraction_method: Optional[str] = None
    page_count: Optional[int] = None


class ReportMetric(BaseModel):
    """A single grounded metric row in the report. Every field must trace to SQL."""
    metric_name: str
    metric_type: str
    category: str                                 # energy, carbon, water, waste, financial
    value: float
    unit: str
    reporting_period: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    verification_status: Optional[str] = None
    confidence: Optional[float] = None
    document_id: int
    document_name: Optional[str] = None
    source_field: Optional[str] = None
    source_text: Optional[str] = None


class ReportEvidence(BaseModel):
    """
    Evidence / provenance row.
    source_text comes verbatim from the existing evidence/lineage system.
    page is only populated when genuinely available from the document model.
    """
    evidence_id: str                              # deterministic: f"{doc_id}:{source_field}"
    document_id: int
    document_name: str
    field: str
    metric_name: str
    value: Optional[float] = None
    unit: Optional[str] = None
    source_text: Optional[str] = None            # verbatim from DB, never invented
    page: Optional[int] = None                   # page if genuinely available
    verification_status: Optional[str] = None


class ReportEmissions(BaseModel):
    """Emissions summary. All values from SQL carbon-category metrics."""
    scope_1: Optional[float] = None
    scope_1_unit: str = "tCO2e"
    scope_1_source: Optional[str] = None
    scope_2: Optional[float] = None
    scope_2_unit: str = "tCO2e"
    scope_2_source: Optional[str] = None
    total_ghg: Optional[float] = None
    total_ghg_unit: str = "tCO2e"
    total_ghg_source: Optional[str] = None
    dominant_scope: Optional[str] = None         # "scope_1" | "scope_2" | None
    emissions_available: bool = False


class ReportInsight(BaseModel):
    """
    Deterministic insight from InsightsService.
    Never adds causal or prescriptive content not already in the insight message.
    """
    category: str
    severity: str
    metric_type: Optional[str] = None
    metric: Optional[str] = None                  # alias for metric_type
    title: str                                    # derived from category + metric_type
    message: str                                  # verbatim from InsightsService
    explanation: Optional[str] = None             # alias for message
    current_value: Optional[float] = None
    previous_value: Optional[float] = None
    unit: Optional[str] = None
    reporting_period: Optional[str] = None
    source_document_id: Optional[int] = None


class ReportRecommendation(BaseModel):
    """
    Deterministic recommendation from CopilotRecommendationService.
    Conservative phrasing enforced at the service layer.
    """
    id: str
    category: str
    priority: str
    title: str
    reason: str
    metric_type: Optional[str] = None
    current_value: Optional[float] = None
    unit: Optional[str] = None
    suggested_actions: List[str] = Field(default_factory=list)
    limitations: Optional[str] = None
    source_document_id: Optional[int] = None


class ReportMissingField(BaseModel):
    """
    Represents a field that is not reported in the selected document.
    Never treated as zero. Never invented.
    """
    field_name: str
    display_name: str
    reason: str = "Not reported in this document"
    is_not_applicable: bool = False


class ReportDataQuality(BaseModel):
    """Data quality summary from the Document model."""
    verification_status: Optional[str] = None
    review_status: Optional[str] = None
    quality_score: Optional[float] = None
    extraction_method: Optional[str] = None
    confidence_score: Optional[float] = None
    needs_review: bool = False
    review_reasons: List[str] = Field(default_factory=list)
    low_confidence_fields: List[str] = Field(default_factory=list)
    metric_count: int = 0
    verified_metric_count: int = 0
    ai_extracted_metric_count: int = 0


class ReportData(BaseModel):
    """
    The single canonical report data object consumed by both:
    - The API/frontend preview
    - The PDF renderer

    Both consumers read from this exact object. No independent data queries.
    This is the anti-divergence guarantee.
    """
    metadata: ReportMetadata
    metrics: List[ReportMetric] = Field(default_factory=list)
    emissions: ReportEmissions = Field(default_factory=ReportEmissions)
    evidence: List[ReportEvidence] = Field(default_factory=list)
    insights: List[ReportInsight] = Field(default_factory=list)
    recommendations: List[ReportRecommendation] = Field(default_factory=list)
    missing_data: List[ReportMissingField] = Field(default_factory=list)
    data_quality: ReportDataQuality = Field(default_factory=ReportDataQuality)
    attention_flags: List[str] = Field(default_factory=list)

    # Executive summary is a deterministic text block derived from metrics+emissions,
    # never from an LLM. Built by the service.
    executive_summary: Optional[str] = None
