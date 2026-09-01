from typing import Optional
from pydantic import BaseModel, Field

class MetricInsight(BaseModel):
    metric_type: Optional[str] = Field(None, description="Type of metric analyzed, e.g. electricity_consumption")
    category: str = Field(..., description="INCREASE, DECREASE, NEW_DATA, MISSING_DATA, NEEDS_REVIEW, TREND, PORTFOLIO")
    severity: str = Field(..., description="INFO, ATTENTION, REVIEW")
    company_name: Optional[str] = Field(None, description="Company or business name")
    period: Optional[str] = Field(None, description="Current reporting period, e.g. 2024-11")
    current_value: Optional[float] = Field(None, description="Current period metric value")
    previous_value: Optional[float] = Field(None, description="Previous period metric value")
    unit: Optional[str] = Field(None, description="Unit of measurement, e.g. kWh, kL, tCO2e, kg")
    percentage_change: Optional[float] = Field(None, description="Percentage change period-over-period")
    message: str = Field(..., description="Deterministic, explainable factual insight message")
    source_document_id: Optional[int] = Field(None, description="Current source document ID")
    previous_source_document_id: Optional[int] = Field(None, description="Previous period source document ID")
    threshold_note: Optional[str] = Field(None, description="Operational explanation if threshold triggered")
    quality_score: Optional[float] = Field(None, description="Extraction quality score if applicable")
