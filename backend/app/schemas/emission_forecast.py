"""
schemas/emission_forecast.py — Pydantic Schemas for Predictive Emissions Analytics Engine (Step 21).
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ForecastRequest(BaseModel):
    """
    User request to generate an emissions forecast.
    Historical data MUST come from CarbonLedgerEntry in the database, not user input.
    """
    scope: Optional[str] = Field(None, description="Scope filter: SCOPE_1, SCOPE_2, SCOPE_3, or None for total")
    category: Optional[str] = Field(None, description="Emissions category filter")
    activity_type: Optional[str] = Field(None, description="Activity type filter")
    reporting_year: Optional[str] = Field(None, description="Reporting year filter")
    horizon: int = Field(1, ge=1, le=4, description="Forecast horizon in periods ahead (1 to 4)")
    model_preference: Optional[str] = Field(None, description="Optional preferred model: NAIVE, MOVING_AVERAGE, LINEAR_TREND, EXPONENTIAL_SMOOTHING")


class DataQualityReport(BaseModel):
    """
    Data quality assessment report for historical CarbonLedgerEntry series.
    """
    historical_periods: int
    missing_periods: int
    outliers_detected: int
    duplicate_periods: int
    zero_or_negative_values: int
    quality: str  # EXCELLENT, GOOD, FAIR, POOR, INSUFFICIENT
    warnings: List[str] = []


class ForecastBacktestResult(BaseModel):
    """
    Walk-forward backtest result for a model evaluated against historical periods.
    """
    model: str
    periods_tested: int
    mae: Optional[float] = None
    rmse: Optional[float] = None
    mape: Optional[float] = None
    successful_predictions: int = 0


class EmissionForecastPoint(BaseModel):
    """
    Individual period point in actual vs forecast unified time-series.
    """
    period: str
    type: str  # ACTUAL or FORECAST
    value: float
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    confidence_label: Optional[str] = None


class EmissionForecastResponse(BaseModel):
    """
    Complete forecast response DTO.
    """
    id: Optional[int] = None
    forecast_code: str
    scope: Optional[str] = None
    category: Optional[str] = None
    activity_type: Optional[str] = None
    forecast_period: str
    horizon: int
    model_name: str
    model_version: str = "1.0"
    forecast_version: str = "forecast_v1"
    training_start_period: Optional[str] = None
    training_end_period: Optional[str] = None
    historical_period_count: int
    predicted_value: float
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    confidence_level: Optional[float] = None
    confidence_label: str  # HIGH, MODERATE, LOW, INSUFFICIENT_DATA
    data_quality: str  # EXCELLENT, GOOD, FAIR, POOR, INSUFFICIENT
    forecast_status: str  # GENERATED, INSUFFICIENT_DATA, NEEDS_REVIEW, FAILED
    backtest_mae: Optional[float] = None
    backtest_rmse: Optional[float] = None
    backtest_mape: Optional[float] = None
    source_count: int = 0
    time_series: List[EmissionForecastPoint] = []
    backtest_results: List[ForecastBacktestResult] = []
    data_quality_report: Optional[DataQualityReport] = None
    explanation: str
    disclaimer: str
    proactive_signal: str  # FORECAST_INCREASE, FORECAST_DECREASE, FORECAST_UNCERTAIN, FORECAST_DATA_INSUFFICIENT
    growth_rate_pct: Optional[float] = None
    dominant_scope: Optional[str] = None
    notes: Optional[str] = None
    generated_at: Optional[datetime] = None


class ForecastModelMetadata(BaseModel):
    """
    Available model metadata item.
    """
    name: str
    code: str
    description: str
    min_periods_required: int
