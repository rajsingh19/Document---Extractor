"""
services/emission_forecasting.py — Deterministic Predictive Emissions Analytics Engine (Step 21).

Analyzes historical POSTED CarbonLedgerEntry data and estimates future emissions when
sufficient historical accounting data exists.

CRITICAL PRODUCT BOUNDARIES:
- CarbonLedgerEntry is historical accounting truth.
- Forecasts are analytical estimates, NOT accounting truth.
- Never modifies or overwrites CarbonLedgerEntry.
- Does NOT fabricate historical periods or treat missing periods as zero.
- Does NOT claim causality, guaranteed reductions, carbon credits, or financial outcomes.
- Does NOT use LLMs for numerical forecasting.
"""
import math
import logging
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.models.carbon_ledger import CarbonLedgerEntry
from backend.app.models.emission_forecast import EmissionForecast
from backend.app.schemas.emission_forecast import (
    ForecastRequest,
    DataQualityReport,
    ForecastBacktestResult,
    EmissionForecastPoint,
    EmissionForecastResponse,
    ForecastModelMetadata,
)

logger = logging.getLogger("senseible-emission-forecasting")

FORECAST_DISCLAIMER = (
    "This forecast is a statistical projection based on historical accounting data. "
    "It is an estimate, not a guaranteed future value or carbon accounting truth."
)

MIN_PERIODS_INSUFFICIENT = 3
MIN_PERIODS_BASELINE = 6
MIN_PERIODS_SEASONAL = 12

AVAILABLE_MODELS = [
    ForecastModelMetadata(
        name="Linear Trend",
        code="LINEAR_TREND",
        description="Fits a deterministic linear regression trend over historical actual periods.",
        min_periods_required=3,
    ),
    ForecastModelMetadata(
        name="Moving Average",
        code="MOVING_AVERAGE",
        description="Forecasts future periods using recent historical period rolling window average.",
        min_periods_required=3,
    ),
    ForecastModelMetadata(
        name="Naive Baseline",
        code="NAIVE",
        description="Baseline model setting future forecast to the latest observed actual period value.",
        min_periods_required=1,
    ),
    ForecastModelMetadata(
        name="Simple Exponential Smoothing",
        code="EXPONENTIAL_SMOOTHING",
        description="Weighted exponential smoothing prioritizing recent historical emissions trends.",
        min_periods_required=3,
    ),
]


class EmissionForecastingService:
    """
    Deterministic Forecasting Service for Predictive Emissions Analytics (Step 21).
    """

    def generate_forecast_code(self, db: Session) -> str:
        """
        Generate unique forecast code: FCST-YYYY-NNNN.
        """
        year_str = datetime.utcnow().strftime("%Y")
        prefix = f"FCST-{year_str}-"
        last = (
            db.query(EmissionForecast)
            .filter(EmissionForecast.forecast_code.like(f"{prefix}%"))
            .order_by(desc(EmissionForecast.id))
            .first()
        )
        if last and last.forecast_code:
            try:
                num = int(last.forecast_code.split("-")[-1]) + 1
            except ValueError:
                num = 1
        else:
            num = 1
        return f"{prefix}{num:04d}"

    def get_posted_ledger_series(
        self,
        db: Session,
        scope: Optional[str] = None,
        category: Optional[str] = None,
        activity_type: Optional[str] = None,
        reporting_year: Optional[str] = None,
    ) -> Tuple[List[Tuple[str, float]], int]:
        """
        Extract chronological time-series from POSTED CarbonLedgerEntry records.
        Returns: ([(period_str, value_tco2e), ...], total_source_records)
        """
        query = db.query(CarbonLedgerEntry)

        # Filter strictly POSTED entries
        # Check both status and accounting_status attributes safely
        entries = query.all()
        posted_entries = [
            e for e in entries
            if getattr(e, "accounting_status", getattr(e, "status", None)) == "POSTED"
        ]

        if scope and scope.upper() != "ALL":
            norm_scope = scope.upper().replace(" ", "_")
            posted_entries = [
                e for e in posted_entries
                if getattr(e, "scope", "").upper() == norm_scope
                or getattr(e, "scope", "").upper().replace(" ", "_") == norm_scope
            ]

        if category:
            norm_cat = category.upper()
            posted_entries = [
                e for e in posted_entries
                if (getattr(e, "category", "") or "").upper() == norm_cat
            ]

        if activity_type:
            norm_act = activity_type.upper()
            posted_entries = [
                e for e in posted_entries
                if (getattr(e, "activity_type", "") or "").upper() == norm_act
            ]

        if reporting_year:
            posted_entries = [
                e for e in posted_entries
                if str(getattr(e, "reporting_period", "")).startswith(reporting_year)
            ]

        if not posted_entries:
            return [], 0

        # Group by reporting_period and aggregate tCO2e
        period_totals: Dict[str, Decimal] = {}
        for e in posted_entries:
            period = str(getattr(e, "reporting_period", "UNKNOWN"))
            val_tco2e = getattr(
                e,
                "emissions_quantity_tco2e",
                Decimal(str(getattr(e, "calculated_co2e", 0) or 0)) / Decimal("1000")
            )
            if isinstance(val_tco2e, float):
                val_tco2e = Decimal(str(val_tco2e))
            
            period_totals[period] = period_totals.get(period, Decimal("0.0")) + val_tco2e

        # Sort periods chronologically
        sorted_periods = sorted(period_totals.keys())
        series = [(p, float(period_totals[p])) for p in sorted_periods]
        return series, len(posted_entries)

    def validate_data_quality(self, series: List[Tuple[str, float]]) -> DataQualityReport:
        """
        Validate historical series for data quality, missing periods, duplicates, and outliers.
        """
        n = len(series)
        warnings: List[str] = []

        if n < MIN_PERIODS_INSUFFICIENT:
            warnings.append(f"Only {n} actual period(s) available. At least 3 periods are required for reliable forecasting.")
            return DataQualityReport(
                historical_periods=n,
                missing_periods=0,
                outliers_detected=0,
                duplicate_periods=0,
                zero_or_negative_values=0,
                quality="INSUFFICIENT",
                warnings=warnings,
            )

        # Check for missing periods (gap detection for YYYY-MM format)
        missing_count = 0
        periods = [s[0] for s in series]
        for i in range(len(periods) - 1):
            p1, p2 = periods[i], periods[i + 1]
            try:
                if len(p1) == 7 and len(p2) == 7 and p1[4] == "-" and p2[4] == "-":
                    y1, m1 = int(p1[:4]), int(p1[5:7])
                    y2, m2 = int(p2[:4]), int(p2[5:7])
                    diff_months = (y2 - y1) * 12 + (m2 - m1)
                    if diff_months > 1:
                        missing_count += (diff_months - 1)
            except ValueError:
                pass

        if missing_count > 0:
            warnings.append(f"Historical series contains {missing_count} missing period(s). Missing periods are not treated as zero.")

        # Check for zero or negative values
        vals = [s[1] for s in series]
        zero_neg_count = sum(1 for v in vals if v <= 0)
        if zero_neg_count > 0:
            warnings.append(f"Found {zero_neg_count} non-positive emissions value(s) in historical series.")

        # Check outliers (>3 std dev from mean)
        outliers_count = 0
        if n >= 4:
            mean_v = sum(vals) / n
            variance = sum((v - mean_v) ** 2 for v in vals) / n
            std_v = math.sqrt(variance)
            if std_v > 0:
                outliers_count = sum(1 for v in vals if abs(v - mean_v) > 2 * std_v)
                if outliers_count > 0:
                    warnings.append(f"Detected {outliers_count} extreme outlier value(s) in historical data.")

        if n >= MIN_PERIODS_SEASONAL and missing_count == 0 and outliers_count == 0:
            quality = "EXCELLENT"
        elif n >= MIN_PERIODS_BASELINE and missing_count <= 1:
            quality = "GOOD"
        elif n >= MIN_PERIODS_INSUFFICIENT:
            quality = "FAIR" if missing_count == 0 else "POOR"
        else:
            quality = "INSUFFICIENT"

        return DataQualityReport(
            historical_periods=n,
            missing_periods=missing_count,
            outliers_detected=outliers_count,
            duplicate_periods=0,
            zero_or_negative_values=zero_neg_count,
            quality=quality,
            warnings=warnings,
        )

    # -------------------------------------------------------------------------
    # FORECAST MODELS
    # -------------------------------------------------------------------------

    def forecast_naive(self, vals: List[float], horizon: int) -> Tuple[List[float], List[float]]:
        """
        NAIVE baseline: forecast next h periods using the latest observed actual value.
        """
        last_val = vals[-1]
        preds = [last_val] * horizon
        # Training residuals: y_t - y_{t-1}
        residuals = [vals[i] - vals[i - 1] for i in range(1, len(vals))]
        return preds, residuals

    def forecast_moving_average(self, vals: List[float], horizon: int, window: int = 3) -> Tuple[List[float], List[float]]:
        """
        MOVING AVERAGE: forecast using recent k-period rolling average.
        """
        w = min(window, len(vals))
        ma_val = sum(vals[-w:]) / w
        preds = [ma_val] * horizon

        residuals = []
        for i in range(w, len(vals)):
            hist_ma = sum(vals[i - w:i]) / w
            residuals.append(vals[i] - hist_ma)
        if not residuals:
            residuals = [0.0]
        return preds, residuals

    def forecast_linear_trend(self, vals: List[float], horizon: int) -> Tuple[List[float], List[float]]:
        """
        LINEAR TREND: Fit linear regression y = m*x + c over time indices x = 1..N.
        """
        n = len(vals)
        x = list(range(1, n + 1))
        x_mean = sum(x) / n
        y_mean = sum(vals) / n

        num = sum((x[i] - x_mean) * (vals[i] - y_mean) for i in range(n))
        den = sum((x[i] - x_mean) ** 2 for i in range(n))

        m = num / den if den != 0 else 0.0
        c = y_mean - m * x_mean

        preds = []
        for h in range(1, horizon + 1):
            future_x = n + h
            pred_y = max(0.0, m * future_x + c)
            preds.append(pred_y)

        residuals = [vals[i] - (m * x[i] + c) for i in range(n)]
        return preds, residuals

    def forecast_exponential_smoothing(self, vals: List[float], horizon: int, alpha: float = 0.3) -> Tuple[List[float], List[float]]:
        """
        EXPONENTIAL SMOOTHING: Simple Exponential Smoothing (SES).
        """
        s = vals[0]
        smoothed = [s]
        for i in range(1, len(vals)):
            s = alpha * vals[i] + (1 - alpha) * s
            smoothed.append(s)

        forecast_val = max(0.0, smoothed[-1])
        preds = [forecast_val] * horizon

        residuals = [vals[i] - smoothed[i - 1] for i in range(1, len(vals))]
        if not residuals:
            residuals = [0.0]
        return preds, residuals

    # -------------------------------------------------------------------------
    # WALK-FORWARD BACKTESTING & MODEL SELECTION
    # -------------------------------------------------------------------------

    def backtest_models(self, vals: List[float]) -> List[ForecastBacktestResult]:
        """
        Perform walk-forward backtesting across candidate models.
        """
        n = len(vals)
        results: List[ForecastBacktestResult] = []
        if n < 4:
            return results

        candidate_models = ["LINEAR_TREND", "MOVING_AVERAGE", "EXPONENTIAL_SMOOTHING", "NAIVE"]

        for model_code in candidate_models:
            errors: List[float] = []
            mapes: List[float] = []
            success_count = 0

            # Walk-forward starting from period 3 up to n-1
            for t in range(3, n):
                train = vals[:t]
                actual = vals[t]

                if model_code == "LINEAR_TREND":
                    preds, _ = self.forecast_linear_trend(train, horizon=1)
                elif model_code == "MOVING_AVERAGE":
                    preds, _ = self.forecast_moving_average(train, horizon=1)
                elif model_code == "EXPONENTIAL_SMOOTHING":
                    preds, _ = self.forecast_exponential_smoothing(train, horizon=1)
                else:  # NAIVE
                    preds, _ = self.forecast_naive(train, horizon=1)

                pred = preds[0]
                err = abs(actual - pred)
                errors.append(err)
                success_count += 1

                # Calculate MAPE only for non-zero denominator
                if actual != 0:
                    mapes.append(abs(actual - pred) / abs(actual) * 100.0)

            if errors:
                mae = sum(errors) / len(errors)
                rmse = math.sqrt(sum(e ** 2 for e in errors) / len(errors))
                mape = (sum(mapes) / len(mapes)) if mapes else None
            else:
                mae = rmse = mape = None

            results.append(
                ForecastBacktestResult(
                    model=model_code,
                    periods_tested=len(errors),
                    mae=round(mae, 4) if mae is not None else None,
                    rmse=round(rmse, 4) if rmse is not None else None,
                    mape=round(mape, 4) if mape is not None else None,
                    successful_predictions=success_count,
                )
            )

        return results

    def select_best_model(
        self,
        vals: List[float],
        preference: Optional[str] = None,
    ) -> Tuple[str, List[ForecastBacktestResult]]:
        """
        Select best model deterministically using walk-forward backtest MAE.
        """
        backtest_results = self.backtest_models(vals)

        valid_codes = ["LINEAR_TREND", "MOVING_AVERAGE", "EXPONENTIAL_SMOOTHING", "NAIVE"]
        if preference and preference.upper() in valid_codes:
            return preference.upper(), backtest_results

        if backtest_results:
            # Sort by lowest MAE
            valid_b = [b for b in backtest_results if b.mae is not None]
            if valid_b:
                sorted_b = sorted(valid_b, key=lambda x: x.mae)
                return sorted_b[0].model, backtest_results

        if len(vals) >= 3:
            return "LINEAR_TREND", backtest_results
        return "NAIVE", backtest_results

    # -------------------------------------------------------------------------
    # MAIN FORECAST GENERATION
    # -------------------------------------------------------------------------

    def generate_forecast(
        self,
        db: Session,
        req: ForecastRequest,
        save_to_db: bool = True,
    ) -> EmissionForecastResponse:
        """
        Generate deterministic emission forecast from POSTED CarbonLedgerEntry history.
        """
        # Scope 3 guard: If Scope 3 requested and no data available
        if req.scope and req.scope.upper().replace(" ", "_") == "SCOPE_3":
            series, count = self.get_posted_ledger_series(
                db=db,
                scope="SCOPE_3",
                category=req.category,
                activity_type=req.activity_type,
                reporting_year=req.reporting_year,
            )
            if not series or len(series) < MIN_PERIODS_INSUFFICIENT:
                return self._build_insufficient_data_response(
                    req=req,
                    series=series,
                    reason="Scope 3 cannot be forecast because sufficient historical accounting data is unavailable.",
                )

        series, total_source_records = self.get_posted_ledger_series(
            db=db,
            scope=req.scope,
            category=req.category,
            activity_type=req.activity_type,
            reporting_year=req.reporting_year,
        )

        quality_report = self.validate_data_quality(series)

        if len(series) < MIN_PERIODS_INSUFFICIENT:
            return self._build_insufficient_data_response(
                req=req,
                series=series,
                reason=f"At least {MIN_PERIODS_INSUFFICIENT} actual reporting periods are required for forecasting. Currently available: {len(series)} period(s).",
            )

        vals = [s[1] for s in series]
        periods = [s[0] for s in series]

        # Select model and perform backtest
        model_code, backtest_results = self.select_best_model(vals, preference=req.model_preference)

        # Generate forecast predictions & residuals
        if model_code == "LINEAR_TREND":
            preds, residuals = self.forecast_linear_trend(vals, horizon=req.horizon)
        elif model_code == "MOVING_AVERAGE":
            preds, residuals = self.forecast_moving_average(vals, horizon=req.horizon)
        elif model_code == "EXPONENTIAL_SMOOTHING":
            preds, residuals = self.forecast_exponential_smoothing(vals, horizon=req.horizon)
        else:  # NAIVE
            preds, residuals = self.forecast_naive(vals, horizon=req.horizon)

        # Main predicted value (for horizon 1 or requested horizon)
        predicted_value = round(preds[req.horizon - 1], 4)

        # Compute uncertainty bounds based on residual error standard deviation
        res_sq = [r ** 2 for r in residuals]
        variance = sum(res_sq) / max(1, len(residuals))
        std_err = math.sqrt(variance)

        # If variance is 0 (e.g. constant data), default small uncertainty cushion
        if std_err == 0:
            std_err = 0.05 * predicted_value if predicted_value > 0 else 0.5

        # Interval width scales with sqrt(horizon)
        multiplier = 1.96 * math.sqrt(req.horizon)
        lower_bound = round(max(0.0, predicted_value - multiplier * std_err), 4)
        upper_bound = round(predicted_value + multiplier * std_err, 4)

        # Determine confidence label
        selected_b = next((b for b in backtest_results if b.model == model_code), None)
        mae_val = selected_b.mae if selected_b else None
        rmse_val = selected_b.rmse if selected_b else None
        mape_val = selected_b.mape if selected_b else None

        if len(series) >= MIN_PERIODS_BASELINE and (mape_val is not None and mape_val < 15.0) and quality_report.missing_periods == 0:
            confidence_label = "HIGH"
            confidence_level = 90.00
        elif len(series) >= MIN_PERIODS_INSUFFICIENT and quality_report.missing_periods <= 1:
            confidence_label = "MODERATE"
            confidence_level = 75.00
        else:
            confidence_label = "LOW"
            confidence_level = 50.00

        # Next forecast period name calculation (e.g., 2024-10 -> 2024-11)
        last_period = periods[-1]
        next_periods = self._calculate_future_period_names(last_period, req.horizon)
        forecast_period_name = next_periods[-1]

        # Determine proactive signal & growth rate
        last_actual = vals[-1]
        growth_rate_pct = None
        if last_actual > 0:
            growth_rate_pct = round(((predicted_value - last_actual) / last_actual) * 100.0, 2)

        if confidence_label == "LOW" or quality_report.quality in ("POOR", "INSUFFICIENT"):
            proactive_signal = "FORECAST_UNCERTAIN"
        elif predicted_value > last_actual * 1.02:
            proactive_signal = "FORECAST_INCREASE"
        elif predicted_value < last_actual * 0.98:
            proactive_signal = "FORECAST_DECREASE"
        else:
            proactive_signal = "FORECAST_UNCERTAIN"

        # Build unified time-series
        time_series: List[EmissionForecastPoint] = []
        for p, v in series:
            time_series.append(
                EmissionForecastPoint(
                    period=p,
                    type="ACTUAL",
                    value=round(v, 4),
                    lower_bound=None,
                    upper_bound=None,
                    confidence_label=None,
                )
            )

        for idx, (fp, pv) in enumerate(zip(next_periods, preds), start=1):
            h_mult = 1.96 * math.sqrt(idx)
            lb = round(max(0.0, pv - h_mult * std_err), 4)
            ub = round(pv + h_mult * std_err, 4)
            time_series.append(
                EmissionForecastPoint(
                    period=fp,
                    type="FORECAST",
                    value=round(pv, 4),
                    lower_bound=lb,
                    upper_bound=ub,
                    confidence_label=confidence_label,
                )
            )

        # Deterministic explanation string
        model_names_map = {
            "LINEAR_TREND": "Linear Trend",
            "MOVING_AVERAGE": "Moving Average",
            "EXPONENTIAL_SMOOTHING": "Simple Exponential Smoothing",
            "NAIVE": "Naive Baseline",
        }
        m_display = model_names_map.get(model_code, model_code)
        
        if mae_val is not None:
            explanation = (
                f"{m_display} selected because it produced the lowest walk-forward MAE "
                f"({mae_val:.4f} tCO2e) among evaluated models across {len(series)} historical periods."
            )
        else:
            explanation = f"{m_display} selected for emission forecasting over {len(series)} historical periods."

        forecast_code = self.generate_forecast_code(db)
        
        db_obj = None
        if save_to_db:
            db_obj = EmissionForecast(
                forecast_code=forecast_code,
                scope=req.scope or "ALL",
                category=req.category,
                activity_type=req.activity_type,
                reporting_year=req.reporting_year,
                forecast_period=forecast_period_name,
                horizon=req.horizon,
                model_name=model_code,
                model_version="1.0",
                forecast_version="forecast_v1",
                training_start_period=periods[0],
                training_end_period=periods[-1],
                historical_period_count=len(series),
                predicted_value=Decimal(str(predicted_value)),
                lower_bound=Decimal(str(lower_bound)) if lower_bound is not None else None,
                upper_bound=Decimal(str(upper_bound)) if upper_bound is not None else None,
                confidence_level=Decimal(str(confidence_level)) if confidence_level is not None else None,
                confidence_label=confidence_label,
                data_quality=quality_report.quality,
                forecast_status="GENERATED",
                backtest_mae=Decimal(str(mae_val)) if mae_val is not None else None,
                backtest_rmse=Decimal(str(rmse_val)) if rmse_val is not None else None,
                backtest_mape=Decimal(str(mape_val)) if mape_val is not None else None,
                source_count=total_source_records,
                explanation=explanation,
                proactive_signal=proactive_signal,
                generated_at=datetime.utcnow(),
            )
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)

        return EmissionForecastResponse(
            id=db_obj.id if db_obj else None,
            forecast_code=forecast_code,
            scope=req.scope or "ALL",
            category=req.category,
            activity_type=req.activity_type,
            forecast_period=forecast_period_name,
            horizon=req.horizon,
            model_name=model_code,
            model_version="1.0",
            forecast_version="forecast_v1",
            training_start_period=periods[0],
            training_end_period=periods[-1],
            historical_period_count=len(series),
            predicted_value=predicted_value,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            confidence_level=confidence_level,
            confidence_label=confidence_label,
            data_quality=quality_report.quality,
            forecast_status="GENERATED",
            backtest_mae=mae_val,
            backtest_rmse=rmse_val,
            backtest_mape=mape_val,
            source_count=total_source_records,
            time_series=time_series,
            backtest_results=backtest_results,
            data_quality_report=quality_report,
            explanation=explanation,
            disclaimer=FORECAST_DISCLAIMER,
            proactive_signal=proactive_signal,
            growth_rate_pct=growth_rate_pct,
            dominant_scope=req.scope or "SCOPE_2",
            generated_at=db_obj.generated_at if db_obj else datetime.utcnow(),
        )

    def _build_insufficient_data_response(
        self,
        req: ForecastRequest,
        series: List[Tuple[str, float]],
        reason: str,
    ) -> EmissionForecastResponse:
        """
        Build standardized response when historical data is insufficient.
        """
        time_series = [
            EmissionForecastPoint(
                period=p,
                type="ACTUAL",
                value=round(v, 4),
                lower_bound=None,
                upper_bound=None,
                confidence_label=None,
            )
            for p, v in series
        ]

        quality_report = DataQualityReport(
            historical_periods=len(series),
            missing_periods=0,
            outliers_detected=0,
            duplicate_periods=0,
            zero_or_negative_values=0,
            quality="INSUFFICIENT",
            warnings=[reason],
        )

        return EmissionForecastResponse(
            forecast_code=f"FCST-{datetime.utcnow().strftime('%Y')}-0000",
            scope=req.scope or "ALL",
            category=req.category,
            activity_type=req.activity_type,
            forecast_period="PENDING",
            horizon=req.horizon,
            model_name="NONE",
            model_version="1.0",
            forecast_version="forecast_v1",
            training_start_period=series[0][0] if series else None,
            training_end_period=series[-1][0] if series else None,
            historical_period_count=len(series),
            predicted_value=0.0,
            lower_bound=None,
            upper_bound=None,
            confidence_level=None,
            confidence_label="INSUFFICIENT_DATA",
            data_quality="INSUFFICIENT",
            forecast_status="INSUFFICIENT_DATA",
            time_series=time_series,
            backtest_results=[],
            data_quality_report=quality_report,
            explanation=reason,
            disclaimer=FORECAST_DISCLAIMER,
            proactive_signal="FORECAST_DATA_INSUFFICIENT",
            notes=reason,
            generated_at=datetime.utcnow(),
        )

    def _calculate_future_period_names(self, last_period: str, horizon: int) -> List[str]:
        """
        Derive future period strings (e.g. 2024-10 -> 2024-11, 2024-12, 2025-01).
        """
        future: List[str] = []
        try:
            if len(last_period) == 7 and last_period[4] == "-":
                y, m = int(last_period[:4]), int(last_period[5:7])
                for h in range(1, horizon + 1):
                    m_new = m + h
                    y_new = y + (m_new - 1) // 12
                    m_final = ((m_new - 1) % 12) + 1
                    future.append(f"{y_new:04d}-{m_final:02d}")
                return future
        except ValueError:
            pass

        # Fallback if non-standard string
        for h in range(1, horizon + 1):
            future.append(f"{last_period}+H{h}")
        return future

    def list_forecasts(self, db: Session, limit: int = 20) -> List[EmissionForecast]:
        return db.query(EmissionForecast).order_by(desc(EmissionForecast.created_at)).limit(limit).all()

    def get_forecast_by_id(self, db: Session, forecast_id: int) -> Optional[EmissionForecast]:
        return db.query(EmissionForecast).filter(EmissionForecast.id == forecast_id).first()


emission_forecasting_service = EmissionForecastingService()
