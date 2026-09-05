"""
models/emission_forecast.py — Database Models for Predictive Emissions Analytics Engine (Step 21).

Stores deterministic forecast records generated from POSTED CarbonLedgerEntry history.

CRITICAL PRODUCT BOUNDARIES:
- Forecasts are analytical estimates, NOT accounting truth.
- Never modifies or overwrites CarbonLedgerEntry.
- Does NOT claim guaranteed future emissions or operational causality.
- Does NOT predict carbon credits or financial values.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text
from backend.app.database.base import Base


class EmissionForecast(Base):
    """
    Persisted record of a deterministic emission forecast.
    Uses Numeric/Decimal for numerical precision.
    """
    __tablename__ = "emission_forecasts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    forecast_code = Column(String(100), unique=True, nullable=False, index=True)
    
    # Scope, category, activity filters
    scope = Column(String(50), nullable=True, index=True)  # SCOPE_1, SCOPE_2, SCOPE_3, ALL
    category = Column(String(100), nullable=True, index=True)
    activity_type = Column(String(100), nullable=True, index=True)
    reporting_year = Column(String(50), nullable=True, index=True)

    # Forecast target and horizon
    forecast_period = Column(String(100), nullable=False, index=True)  # e.g., 2024-11
    horizon = Column(Integer, nullable=False, default=1)  # 1 to 4 periods ahead

    # Model metadata & versioning
    model_name = Column(String(100), nullable=False)  # NAIVE, MOVING_AVERAGE, LINEAR_TREND, EXPONENTIAL_SMOOTHING
    model_version = Column(String(50), nullable=False, default="1.0")
    forecast_version = Column(String(50), nullable=False, default="forecast_v1")
    training_start_period = Column(String(100), nullable=True)
    training_end_period = Column(String(100), nullable=True)
    historical_period_count = Column(Integer, nullable=False, default=0)

    # Predicted value & uncertainty interval (tCO2e)
    predicted_value = Column(Numeric(14, 4), nullable=False)
    lower_bound = Column(Numeric(14, 4), nullable=True)
    upper_bound = Column(Numeric(14, 4), nullable=True)

    # Confidence and quality
    confidence_level = Column(Numeric(5, 2), nullable=True)  # e.g., 95.00
    confidence_label = Column(String(50), nullable=False, default="MODERATE")  # HIGH, MODERATE, LOW, INSUFFICIENT_DATA
    data_quality = Column(String(50), nullable=False, default="GOOD")  # EXCELLENT, GOOD, FAIR, POOR, INSUFFICIENT
    forecast_status = Column(String(50), nullable=False, default="GENERATED", index=True)  # GENERATED, INSUFFICIENT_DATA, NEEDS_REVIEW, FAILED

    # Backtest metrics
    backtest_mae = Column(Numeric(14, 4), nullable=True)
    backtest_rmse = Column(Numeric(14, 4), nullable=True)
    backtest_mape = Column(Numeric(10, 4), nullable=True)

    source_count = Column(Integer, nullable=False, default=0)
    notes = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    proactive_signal = Column(String(50), nullable=True)  # FORECAST_INCREASE, FORECAST_DECREASE, FORECAST_UNCERTAIN, FORECAST_DATA_INSUFFICIENT

    generated_at = Column(DateTime, nullable=True, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
