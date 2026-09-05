"""
api/emission_forecast.py — FastAPI Endpoints for Predictive Emissions Analytics Engine (Step 21).

CRITICAL BOUNDARIES:
- Calculates analytical forecasts from POSTED CarbonLedgerEntry history.
- Never modifies or overwrites CarbonLedgerEntry records.
- Does NOT claim guaranteed future emissions or operational causality.
- Does NOT predict carbon credits or financial values.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.schemas.emission_forecast import (
    ForecastRequest,
    EmissionForecastResponse,
    ForecastModelMetadata,
    DataQualityReport,
    ForecastBacktestResult,
)
from backend.app.services.emission_forecasting import (
    emission_forecasting_service,
    AVAILABLE_MODELS,
    FORECAST_DISCLAIMER,
)

router = APIRouter(prefix="/emissions/forecast", tags=["Predictive Emissions Analytics"])


@router.get("", response_model=EmissionForecastResponse)
def get_emissions_forecast(
    scope: Optional[str] = Query(None, description="Filter scope: SCOPE_1, SCOPE_2, SCOPE_3, or ALL"),
    category: Optional[str] = Query(None, description="Filter category"),
    activity_type: Optional[str] = Query(None, description="Filter activity type"),
    reporting_year: Optional[str] = Query(None, description="Filter reporting year"),
    horizon: int = Query(1, ge=1, le=4, description="Forecast horizon in periods (1 to 4)"),
    model_preference: Optional[str] = Query(None, description="Preferred model"),
    db: Session = Depends(get_db)
):
    """
    Generate or retrieve deterministic emission forecast based on POSTED carbon ledger history.
    """
    req = ForecastRequest(
        scope=scope,
        category=category,
        activity_type=activity_type,
        reporting_year=reporting_year,
        horizon=horizon,
        model_preference=model_preference,
    )
    return emission_forecasting_service.generate_forecast(db=db, req=req, save_to_db=True)


@router.post("", response_model=EmissionForecastResponse, status_code=status.HTTP_201_CREATED)
def create_emissions_forecast(
    data: ForecastRequest,
    db: Session = Depends(get_db)
):
    """
    Generate and persist a new emission forecast.
    Historical data comes strictly from CarbonLedgerEntry in the database.
    """
    return emission_forecasting_service.generate_forecast(db=db, req=data, save_to_db=True)


@router.get("/models", response_model=List[ForecastModelMetadata])
def get_forecast_models():
    """
    List available baseline forecasting models and metadata.
    """
    return AVAILABLE_MODELS


@router.get("/data-quality", response_model=DataQualityReport)
def get_forecast_data_quality(
    scope: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    activity_type: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get data quality validation report for the POSTED carbon ledger series.
    """
    series, _ = emission_forecasting_service.get_posted_ledger_series(
        db=db, scope=scope, category=category, activity_type=activity_type
    )
    return emission_forecasting_service.validate_data_quality(series)


@router.get("/backtest", response_model=List[ForecastBacktestResult])
def get_forecast_backtest(
    scope: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    activity_type: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get walk-forward backtest results across models for historical carbon ledger series.
    """
    series, _ = emission_forecasting_service.get_posted_ledger_series(
        db=db, scope=scope, category=category, activity_type=activity_type
    )
    vals = [s[1] for s in series]
    return emission_forecasting_service.backtest_models(vals)


@router.get("/history")
def list_forecast_history(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    List historical forecast records persisted in database.
    """
    records = emission_forecasting_service.list_forecasts(db=db, limit=limit)
    items = []
    for r in records:
        items.append({
            "id": r.id,
            "forecast_code": r.forecast_code,
            "scope": r.scope,
            "category": r.category,
            "activity_type": r.activity_type,
            "forecast_period": r.forecast_period,
            "horizon": r.horizon,
            "model_name": r.model_name,
            "predicted_value": float(r.predicted_value),
            "lower_bound": float(r.lower_bound) if r.lower_bound is not None else None,
            "upper_bound": float(r.upper_bound) if r.upper_bound is not None else None,
            "confidence_label": r.confidence_label,
            "data_quality": r.data_quality,
            "forecast_status": r.forecast_status,
            "backtest_mae": float(r.backtest_mae) if r.backtest_mae is not None else None,
            "generated_at": r.generated_at,
        })
    return {"total": len(items), "items": items}


@router.get("/{forecast_id}", response_model=EmissionForecastResponse)
def get_forecast_by_id(
    forecast_id: int,
    db: Session = Depends(get_db)
):
    """
    Get persisted forecast by ID.
    """
    record = emission_forecasting_service.get_forecast_by_id(db=db, forecast_id=forecast_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Emission forecast with id {forecast_id} not found.")

    req = ForecastRequest(
        scope=record.scope,
        category=record.category,
        activity_type=record.activity_type,
        reporting_year=record.reporting_year,
        horizon=record.horizon,
        model_preference=record.model_name,
    )
    dto = emission_forecasting_service.generate_forecast(db=db, req=req, save_to_db=False)
    dto.id = record.id
    return dto
