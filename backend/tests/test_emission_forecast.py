"""
tests/test_emission_forecast.py — Comprehensive Test Suite for Predictive Emissions Analytics Engine (Step 21).

Tests:
- EmissionForecast database models, schemas, constraints, and relationships
- Historical time-series builder consuming ONLY POSTED CarbonLedgerEntry
- Exclusion of PENDING, EXCLUDED, INVALID, SUPERSEDED ledger entries
- Data quality validation, gap detection, outlier handling
- Data sufficiency rules (<3, 3-5, 6-11, 12+ periods)
- Baseline models: NAIVE, MOVING_AVERAGE, LINEAR_TREND, EXPONENTIAL_SMOOTHING
- Deterministic model selection & walk-forward backtesting (MAE, RMSE, MAPE)
- Zero-denominator protection in MAPE
- 95% uncertainty interval calculation & confidence labeling
- Multi-horizon forecasting (1 to 4 periods)
- Scope 1, Scope 2, Scope 3 handling (Scope 3 insufficient data protection)
- Forecast persistence, reproducibility, versioning
- API endpoints testing
- Copilot grounding, intent routing, and safety refusal boundaries
- Absolute non-mutation of CarbonLedgerEntry records
"""
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend.app.database.base import Base
from backend.app.database.session import get_db
from backend.app.models.carbon_ledger import CarbonLedgerEntry
from backend.app.models.emission_forecast import EmissionForecast
from backend.app.schemas.emission_forecast import (
    ForecastRequest,
    DataQualityReport,
    ForecastBacktestResult,
    EmissionForecastPoint,
    EmissionForecastResponse,
)
from backend.app.services.emission_forecasting import (
    emission_forecasting_service,
    FORECAST_DISCLAIMER,
    AVAILABLE_MODELS,
    MIN_PERIODS_INSUFFICIENT,
    MIN_PERIODS_BASELINE,
    MIN_PERIODS_SEASONAL,
)
from backend.app.services.copilot_service import copilot_service


@pytest.fixture(scope="function")
def db_engine():
    """Shared in-memory engine per function with StaticPool."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    Base.metadata.create_all(bind=engine)
    yield engine


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Isolated session bound to function-level db_engine."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="function")
def sample_ledger_history(db_session):
    """
    Standard test fixture providing 6 consecutive POSTED CarbonLedgerEntry records.
    January:  28.4 tCO2e (28400 kgCO2e)
    February: 30.1 tCO2e (30100 kgCO2e)
    March:    31.2 tCO2e (31200 kgCO2e)
    April:    33.0 tCO2e (33000 kgCO2e)
    May:      34.1 tCO2e (34100 kgCO2e)
    June:     35.0 tCO2e (35000 kgCO2e)
    """
    periods = ["2024-01", "2024-02", "2024-03", "2024-04", "2024-05", "2024-06"]
    values = [28.4, 30.1, 31.2, 33.0, 34.1, 35.0]

    entries = []
    for p, v in zip(periods, values):
        e = CarbonLedgerEntry(
            carbon_calculation_id=1,
            activity_data_id=1,
            document_id=1,
            scope="SCOPE_2",
            quantity=Decimal(str(v * 1000)),
            activity_unit="kWh",
            calculated_co2e=Decimal(str(v * 1000)),
            calculated_co2e_unit="kgCO2e",
            activity_type="ELECTRICITY",
            category="ENERGY",
            accounting_status="POSTED",
            reporting_period=p,
        )
        db_session.add(e)
        entries.append(e)

    db_session.commit()
    return {"db": db_session, "entries": entries, "periods": periods, "values": values}


# =============================================================================
# 1. DATABASE MODELS & SCHEMAS (1-15)
# =============================================================================

class TestEmissionForecastModels:
    def test_01_create_forecast_record(self, db_session):
        fcst = EmissionForecast(
            forecast_code="FCST-2026-0001",
            scope="SCOPE_2",
            forecast_period="2024-07",
            horizon=1,
            model_name="LINEAR_TREND",
            model_version="1.0",
            predicted_value=Decimal("36.2000"),
            lower_bound=Decimal("34.8000"),
            upper_bound=Decimal("37.7000"),
            confidence_label="MODERATE",
            data_quality="GOOD",
            forecast_status="GENERATED",
            historical_period_count=6,
        )
        db_session.add(fcst)
        db_session.commit()
        db_session.refresh(fcst)
        assert fcst.id is not None
        assert fcst.forecast_code == "FCST-2026-0001"
        assert float(fcst.predicted_value) == 36.2

    def test_02_forecast_code_unique_constraint(self, db_session):
        f1 = EmissionForecast(
            forecast_code="FCST-UNIQUE-01",
            scope="SCOPE_2",
            forecast_period="2024-07",
            horizon=1,
            model_name="LINEAR_TREND",
            predicted_value=Decimal("36.2"),
        )
        db_session.add(f1)
        db_session.commit()

        f2 = EmissionForecast(
            forecast_code="FCST-UNIQUE-01",
            scope="SCOPE_2",
            forecast_period="2024-07",
            horizon=1,
            model_name="LINEAR_TREND",
            predicted_value=Decimal("36.2"),
        )
        db_session.add(f2)
        with pytest.raises(Exception):
            db_session.commit()
        db_session.rollback()

    def test_03_forecast_default_values(self, db_session):
        fcst = EmissionForecast(
            forecast_code="FCST-DEFAULT-01",
            scope="ALL",
            forecast_period="2024-07",
            model_name="NAIVE",
            predicted_value=Decimal("30.0"),
        )
        db_session.add(fcst)
        db_session.commit()
        assert fcst.horizon == 1
        assert fcst.model_version == "1.0"
        assert fcst.forecast_version == "forecast_v1"
        assert fcst.confidence_label == "MODERATE"
        assert fcst.forecast_status == "GENERATED"

    def test_04_numeric_decimal_precision(self, db_session):
        val = Decimal("36.1234")
        fcst = EmissionForecast(
            forecast_code="FCST-PREC-01",
            scope="SCOPE_1",
            forecast_period="2024-07",
            model_name="LINEAR_TREND",
            predicted_value=val,
            lower_bound=Decimal("34.1111"),
            upper_bound=Decimal("38.9999"),
        )
        db_session.add(fcst)
        db_session.commit()
        db_session.refresh(fcst)
        assert fcst.predicted_value == Decimal("36.1234")

    def test_05_schema_forecast_request_defaults(self):
        req = ForecastRequest()
        assert req.horizon == 1
        assert req.scope is None
        assert req.model_preference is None

    def test_06_schema_forecast_request_validation(self):
        req = ForecastRequest(scope="SCOPE_2", horizon=3, model_preference="LINEAR_TREND")
        assert req.scope == "SCOPE_2"
        assert req.horizon == 3

    def test_07_schema_data_quality_report(self):
        qr = DataQualityReport(
            historical_periods=6,
            missing_periods=0,
            outliers_detected=0,
            duplicate_periods=0,
            zero_or_negative_values=0,
            quality="GOOD",
            warnings=[],
        )
        assert qr.quality == "GOOD"
        assert qr.historical_periods == 6

    def test_08_schema_backtest_result(self):
        br = ForecastBacktestResult(
            model="LINEAR_TREND",
            periods_tested=3,
            mae=0.84,
            rmse=0.92,
            mape=2.5,
            successful_predictions=3,
        )
        assert br.model == "LINEAR_TREND"
        assert br.mae == 0.84

    def test_09_schema_forecast_point(self):
        pt = EmissionForecastPoint(
            period="2024-07",
            type="FORECAST",
            value=36.2,
            lower_bound=34.8,
            upper_bound=37.7,
            confidence_label="MODERATE",
        )
        assert pt.type == "FORECAST"
        assert pt.value == 36.2

    def test_10_available_models_constant(self):
        assert len(AVAILABLE_MODELS) == 4
        codes = [m.code for m in AVAILABLE_MODELS]
        assert "LINEAR_TREND" in codes
        assert "MOVING_AVERAGE" in codes
        assert "NAIVE" in codes
        assert "EXPONENTIAL_SMOOTHING" in codes

    def test_11_forecast_code_generator_format(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        code1 = emission_forecasting_service.generate_forecast_code(db)
        assert code1.startswith("FCST-")
        assert len(code1.split("-")) == 3

    def test_12_forecast_code_generator_increment(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        code1 = emission_forecasting_service.generate_forecast_code(db)
        fcst = EmissionForecast(
            forecast_code=code1,
            scope="SCOPE_2",
            forecast_period="2024-07",
            model_name="NAIVE",
            predicted_value=Decimal("35.0"),
        )
        db.add(fcst)
        db.commit()

        code2 = emission_forecasting_service.generate_forecast_code(db)
        num1 = int(code1.split("-")[-1])
        num2 = int(code2.split("-")[-1])
        assert num2 == num1 + 1

    def test_13_forecast_disclaimer_presence(self):
        assert "statistical projection" in FORECAST_DISCLAIMER
        assert "not a guaranteed future value" in FORECAST_DISCLAIMER

    def test_14_schema_forecast_response_construction(self):
        res = EmissionForecastResponse(
            forecast_code="FCST-TEST",
            forecast_period="2024-07",
            horizon=1,
            model_name="LINEAR_TREND",
            historical_period_count=6,
            predicted_value=36.2,
            confidence_label="MODERATE",
            data_quality="GOOD",
            forecast_status="GENERATED",
            explanation="Linear trend selected.",
            disclaimer=FORECAST_DISCLAIMER,
            proactive_signal="FORECAST_INCREASE",
        )
        assert res.predicted_value == 36.2
        assert res.forecast_status == "GENERATED"

    def test_15_future_period_names_calculation(self):
        periods = emission_forecasting_service._calculate_future_period_names("2024-10", horizon=3)
        assert periods == ["2024-11", "2024-12", "2025-01"]


# =============================================================================
# 2. HISTORICAL DATA EXTRACTION & POSTED FILTERING (16-30)
# =============================================================================

class TestHistoricalDataExtraction:
    def test_16_extract_posted_ledger_series(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        series, count = emission_forecasting_service.get_posted_ledger_series(db)
        assert len(series) == 6
        assert count == 6
        assert series[0] == ("2024-01", 28.4)
        assert series[-1] == ("2024-06", 35.0)

    def test_17_exclude_non_posted_ledger_entries(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        pending_e = CarbonLedgerEntry(
            carbon_calculation_id=2,
            scope="SCOPE_2",
            quantity=Decimal("50000"),
            activity_unit="kWh",
            calculated_co2e=Decimal("50000.0"),
            accounting_status="PENDING",
            reporting_period="2024-07",
            activity_type="ELECTRICITY",
        )
        excluded_e = CarbonLedgerEntry(
            carbon_calculation_id=3,
            scope="SCOPE_2",
            quantity=Decimal("60000"),
            activity_unit="kWh",
            calculated_co2e=Decimal("60000.0"),
            accounting_status="EXCLUDED",
            reporting_period="2024-08",
            activity_type="ELECTRICITY",
        )
        db.add(pending_e)
        db.add(excluded_e)
        db.commit()

        series, count = emission_forecasting_service.get_posted_ledger_series(db)
        assert len(series) == 6
        assert count == 6
        periods = [s[0] for s in series]
        assert "2024-07" not in periods
        assert "2024-08" not in periods

    def test_18_filter_by_scope_1(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        s1_e = CarbonLedgerEntry(
            carbon_calculation_id=4,
            scope="SCOPE_1",
            quantity=Decimal("100"),
            activity_unit="LITERS",
            calculated_co2e=Decimal("2500.0"),
            accounting_status="POSTED",
            reporting_period="2024-01",
            activity_type="DIESEL",
        )
        db.add(s1_e)
        db.commit()

        series_s1, count_s1 = emission_forecasting_service.get_posted_ledger_series(db, scope="SCOPE_1")
        assert len(series_s1) == 1
        assert series_s1[0] == ("2024-01", 2.5)

    def test_19_filter_by_scope_2(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        series_s2, count_s2 = emission_forecasting_service.get_posted_ledger_series(db, scope="SCOPE_2")
        assert len(series_s2) == 6

    def test_20_scope_3_unavailable_returns_empty(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        series_s3, count_s3 = emission_forecasting_service.get_posted_ledger_series(db, scope="SCOPE_3")
        assert len(series_s3) == 0
        assert count_s3 == 0

    def test_21_filter_by_category(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        series_cat, count_cat = emission_forecasting_service.get_posted_ledger_series(db, category="ENERGY")
        assert len(series_cat) == 6

    def test_22_filter_by_activity_type(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        series_act, count_act = emission_forecasting_service.get_posted_ledger_series(db, activity_type="ELECTRICITY")
        assert len(series_act) == 6

    def test_23_filter_by_reporting_year(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        series_yr, count_yr = emission_forecasting_service.get_posted_ledger_series(db, reporting_year="2024")
        assert len(series_yr) == 6

    def test_24_decimal_aggregation_per_period(self, db_session):
        e1 = CarbonLedgerEntry(
            carbon_calculation_id=1,
            scope="SCOPE_2",
            quantity=Decimal("12345.6"),
            activity_unit="kWh",
            calculated_co2e=Decimal("12345.6"),
            accounting_status="POSTED",
            reporting_period="2024-01",
            activity_type="ELECTRICITY",
        )
        e2 = CarbonLedgerEntry(
            carbon_calculation_id=2,
            scope="SCOPE_2",
            quantity=Decimal("10000.4"),
            activity_unit="kWh",
            calculated_co2e=Decimal("10000.4"),
            accounting_status="POSTED",
            reporting_period="2024-01",
            activity_type="ELECTRICITY",
        )
        db_session.add(e1)
        db_session.add(e2)
        db_session.commit()

        series, _ = emission_forecasting_service.get_posted_ledger_series(db_session)
        assert len(series) == 1
        assert series[0] == ("2024-01", 22.346)

    def test_25_chronological_ordering(self, db_session):
        for p in ["2024-03", "2024-01", "2024-02"]:
            e = CarbonLedgerEntry(
                carbon_calculation_id=1,
                scope="SCOPE_2",
                quantity=Decimal("10000.0"),
                activity_unit="kWh",
                calculated_co2e=Decimal("10000.0"),
                accounting_status="POSTED",
                reporting_period=p,
                activity_type="ELECTRICITY",
            )
            db_session.add(e)
        db_session.commit()

        series, _ = emission_forecasting_service.get_posted_ledger_series(db_session)
        periods = [s[0] for s in series]
        assert periods == ["2024-01", "2024-02", "2024-03"]

    def test_26_empty_database_handling(self, db_session):
        series, count = emission_forecasting_service.get_posted_ledger_series(db_session)
        assert series == []
        assert count == 0

    def test_27_case_insensitive_scope_filtering(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        series, count = emission_forecasting_service.get_posted_ledger_series(db, scope="scope 2")
        assert len(series) == 6

    def test_28_case_insensitive_category_filtering(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        series, count = emission_forecasting_service.get_posted_ledger_series(db, category="energy")
        assert len(series) == 6

    def test_29_all_scopes_returns_combined(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        series, count = emission_forecasting_service.get_posted_ledger_series(db, scope="ALL")
        assert len(series) == 6

    def test_30_no_historical_mutation(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        before_count = db.query(CarbonLedgerEntry).count()
        req = ForecastRequest(scope="SCOPE_2", horizon=1)
        emission_forecasting_service.generate_forecast(db, req)
        after_count = db.query(CarbonLedgerEntry).count()
        assert before_count == after_count


# =============================================================================
# 3. DATA QUALITY & SUFFICIENCY RULES (31-45)
# =============================================================================

class TestDataQualityAndSufficiency:
    def test_31_insufficient_data_less_than_3_periods(self, db_session):
        e1 = CarbonLedgerEntry(carbon_calculation_id=1, scope="SCOPE_2", quantity=Decimal("10000.0"), activity_unit="kWh", calculated_co2e=Decimal("10000.0"), accounting_status="POSTED", reporting_period="2024-01", activity_type="ELECTRICITY")
        e2 = CarbonLedgerEntry(carbon_calculation_id=2, scope="SCOPE_2", quantity=Decimal("12000.0"), activity_unit="kWh", calculated_co2e=Decimal("12000.0"), accounting_status="POSTED", reporting_period="2024-02", activity_type="ELECTRICITY")
        db_session.add(e1)
        db_session.add(e2)
        db_session.commit()

        req = ForecastRequest(scope="SCOPE_2")
        res = emission_forecasting_service.generate_forecast(db_session, req)
        assert res.forecast_status == "INSUFFICIENT_DATA"
        assert res.confidence_label == "INSUFFICIENT_DATA"
        assert "At least 3 actual reporting periods are required" in res.explanation

    def test_32_data_quality_report_good_series(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        series, _ = emission_forecasting_service.get_posted_ledger_series(db)
        qr = emission_forecasting_service.validate_data_quality(series)
        assert qr.historical_periods == 6
        assert qr.missing_periods == 0
        assert qr.quality in ("GOOD", "EXCELLENT")

    def test_33_missing_period_gap_detection(self):
        series = [("2024-01", 10.0), ("2024-02", 12.0), ("2024-04", 14.0)]
        qr = emission_forecasting_service.validate_data_quality(series)
        assert qr.missing_periods == 1
        assert any("contains 1 missing period" in w for w in qr.warnings)

    def test_34_missing_period_not_treated_as_zero(self, db_session):
        for p, v in [("2024-01", 10.0), ("2024-02", 12.0), ("2024-04", 14.0)]:
            e = CarbonLedgerEntry(carbon_calculation_id=1, scope="SCOPE_2", quantity=Decimal(str(v * 1000)), activity_unit="kWh", calculated_co2e=Decimal(str(v * 1000)), accounting_status="POSTED", reporting_period=p, activity_type="ELECTRICITY")
            db_session.add(e)
        db_session.commit()

        series, _ = emission_forecasting_service.get_posted_ledger_series(db_session)
        periods = [s[0] for s in series]
        assert "2024-03" not in periods
        vals = [s[1] for s in series]
        assert 0.0 not in vals

    def test_35_low_confidence_3_to_5_periods(self, db_session):
        for p, v in [("2024-01", 10.0), ("2024-02", 11.0), ("2024-03", 12.0)]:
            e = CarbonLedgerEntry(carbon_calculation_id=1, scope="SCOPE_2", quantity=Decimal(str(v * 1000)), activity_unit="kWh", calculated_co2e=Decimal(str(v * 1000)), accounting_status="POSTED", reporting_period=p, activity_type="ELECTRICITY")
            db_session.add(e)
        db_session.commit()

        req = ForecastRequest(scope="SCOPE_2")
        res = emission_forecasting_service.generate_forecast(db_session, req)
        assert res.forecast_status == "GENERATED"
        assert res.confidence_label in ("MODERATE", "LOW")

    def test_36_sufficient_baseline_6_periods(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        req = ForecastRequest(scope="SCOPE_2")
        res = emission_forecasting_service.generate_forecast(db, req)
        assert res.forecast_status == "GENERATED"
        assert res.historical_period_count == 6

    def test_37_sufficient_seasonal_12_periods(self, db_session):
        for i in range(1, 13):
            p = f"2024-{i:02d}"
            v = 20.0 + i * 0.5
            e = CarbonLedgerEntry(carbon_calculation_id=i, scope="SCOPE_2", quantity=Decimal(str(v * 1000)), activity_unit="kWh", calculated_co2e=Decimal(str(v * 1000)), accounting_status="POSTED", reporting_period=p, activity_type="ELECTRICITY")
            db_session.add(e)
        db_session.commit()

        series, _ = emission_forecasting_service.get_posted_ledger_series(db_session)
        qr = emission_forecasting_service.validate_data_quality(series)
        assert qr.quality == "EXCELLENT"

    def test_38_detect_extreme_outliers(self):
        series = [("2024-01", 10.0), ("2024-02", 11.0), ("2024-03", 10.5), ("2024-04", 11.2), ("2024-05", 10.8), ("2024-06", 500.0)]
        qr = emission_forecasting_service.validate_data_quality(series)
        assert qr.outliers_detected >= 1

    def test_39_detect_zero_or_negative_values(self):
        series = [("2024-01", 10.0), ("2024-02", 0.0), ("2024-03", -5.0)]
        qr = emission_forecasting_service.validate_data_quality(series)
        assert qr.zero_or_negative_values == 2

    def test_40_warning_list_population(self):
        series = [("2024-01", 10.0), ("2024-03", 12.0), ("2024-04", 14.0)]
        qr = emission_forecasting_service.validate_data_quality(series)
        assert len(qr.warnings) > 0

    def test_41_insufficient_data_lower_upper_bounds_null(self, db_session):
        e1 = CarbonLedgerEntry(carbon_calculation_id=1, scope="SCOPE_2", quantity=Decimal("10000.0"), activity_unit="kWh", calculated_co2e=Decimal("10000.0"), accounting_status="POSTED", reporting_period="2024-01", activity_type="ELECTRICITY")
        db_session.add(e1)
        db_session.commit()

        req = ForecastRequest(scope="SCOPE_2")
        res = emission_forecasting_service.generate_forecast(db_session, req)
        assert res.lower_bound is None
        assert res.upper_bound is None

    def test_42_quality_report_in_forecast_response(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        req = ForecastRequest(scope="SCOPE_2")
        res = emission_forecasting_service.generate_forecast(db, req)
        assert res.data_quality_report is not None
        assert res.data_quality_report.historical_periods == 6

    def test_43_valid_forecast_horizon_1_to_4(self):
        for h in [1, 2, 3, 4]:
            req = ForecastRequest(horizon=h)
            assert req.horizon == h

    def test_44_invalid_horizon_rejected_by_pydantic(self):
        with pytest.raises(Exception):
            ForecastRequest(horizon=5)

    def test_45_data_sufficiency_constants(self):
        assert MIN_PERIODS_INSUFFICIENT == 3
        assert MIN_PERIODS_BASELINE == 6
        assert MIN_PERIODS_SEASONAL == 12


# =============================================================================
# 4. MODEL IMPLEMENTATIONS & PREDICTIONS (46-60)
# =============================================================================

class TestForecastModels:
    def test_46_naive_model_prediction(self):
        vals = [28.4, 30.1, 31.2, 33.0, 34.1, 35.0]
        preds, resids = emission_forecasting_service.forecast_naive(vals, horizon=2)
        assert preds == [35.0, 35.0]
        assert len(resids) == 5

    def test_47_moving_average_prediction(self):
        vals = [28.4, 30.1, 31.2, 33.0, 34.1, 35.0]
        preds, resids = emission_forecasting_service.forecast_moving_average(vals, horizon=1, window=3)
        expected_ma = (33.0 + 34.1 + 35.0) / 3.0
        assert round(preds[0], 4) == round(expected_ma, 4)

    def test_48_linear_trend_prediction(self):
        vals = [10.0, 20.0, 30.0, 40.0, 50.0]
        preds, resids = emission_forecasting_service.forecast_linear_trend(vals, horizon=1)
        assert round(preds[0], 2) == 60.0

    def test_49_exponential_smoothing_prediction(self):
        vals = [10.0, 12.0, 14.0, 16.0, 18.0]
        preds, resids = emission_forecasting_service.forecast_exponential_smoothing(vals, horizon=1, alpha=0.3)
        assert preds[0] > 0.0

    def test_50_non_negative_prediction_constraint(self):
        vals = [50.0, 40.0, 30.0, 20.0, 10.0]
        preds, _ = emission_forecasting_service.forecast_linear_trend(vals, horizon=10)
        assert all(p >= 0.0 for p in preds)

    def test_51_multi_period_horizon_linear_trend(self):
        vals = [10.0, 20.0, 30.0, 40.0]
        preds, _ = emission_forecasting_service.forecast_linear_trend(vals, horizon=3)
        assert len(preds) == 3
        assert round(preds[0], 1) == 50.0
        assert round(preds[1], 1) == 60.0
        assert round(preds[2], 1) == 70.0

    def test_52_moving_average_window_smaller_than_series(self):
        vals = [10.0, 20.0]
        preds, _ = emission_forecasting_service.forecast_moving_average(vals, horizon=1, window=3)
        assert preds[0] == 15.0

    def test_53_constant_series_forecasting(self):
        vals = [25.0, 25.0, 25.0, 25.0]
        preds_lt, _ = emission_forecasting_service.forecast_linear_trend(vals, horizon=1)
        preds_ma, _ = emission_forecasting_service.forecast_moving_average(vals, horizon=1)
        assert round(preds_lt[0], 2) == 25.0
        assert round(preds_ma[0], 2) == 25.0

    def test_54_linear_trend_residuals_length(self):
        vals = [10.0, 15.0, 20.0, 25.0]
        _, resids = emission_forecasting_service.forecast_linear_trend(vals, horizon=1)
        assert len(resids) == 4

    def test_55_exponential_smoothing_residuals_length(self):
        vals = [10.0, 15.0, 20.0, 25.0]
        _, resids = emission_forecasting_service.forecast_exponential_smoothing(vals, horizon=1)
        assert len(resids) == 3

    def test_56_naive_residuals_calculation(self):
        vals = [10.0, 15.0, 20.0]
        _, resids = emission_forecasting_service.forecast_naive(vals, horizon=1)
        assert resids == [5.0, 5.0]

    def test_57_explicit_model_preference_override(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        req = ForecastRequest(scope="SCOPE_2", model_preference="NAIVE")
        res = emission_forecasting_service.generate_forecast(db, req)
        assert res.model_name == "NAIVE"

    def test_58_model_preference_case_insensitive(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        req = ForecastRequest(scope="SCOPE_2", model_preference="moving_average")
        res = emission_forecasting_service.generate_forecast(db, req)
        assert res.model_name == "MOVING_AVERAGE"

    def test_59_invalid_model_preference_fallback(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        req = ForecastRequest(scope="SCOPE_2", model_preference="INVALID_MODEL")
        res = emission_forecasting_service.generate_forecast(db, req)
        assert res.model_name in ("LINEAR_TREND", "MOVING_AVERAGE", "NAIVE", "EXPONENTIAL_SMOOTHING")

    def test_60_time_series_output_structure(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        req = ForecastRequest(scope="SCOPE_2", horizon=2)
        res = emission_forecasting_service.generate_forecast(db, req)
        assert len(res.time_series) == 8  # 6 actual + 2 forecast
        actuals = [pt for pt in res.time_series if pt.type == "ACTUAL"]
        forecasts = [pt for pt in res.time_series if pt.type == "FORECAST"]
        assert len(actuals) == 6
        assert len(forecasts) == 2


# =============================================================================
# 5. WALK-FORWARD BACKTESTING & MODEL SELECTION (61-75)
# =============================================================================

class TestWalkForwardBacktesting:
    def test_61_backtest_models_execution(self):
        vals = [28.4, 30.1, 31.2, 33.0, 34.1, 35.0]
        results = emission_forecasting_service.backtest_models(vals)
        assert len(results) == 4
        models = [r.model for r in results]
        assert "LINEAR_TREND" in models
        assert "MOVING_AVERAGE" in models

    def test_62_backtest_metrics_present(self):
        vals = [28.4, 30.1, 31.2, 33.0, 34.1, 35.0]
        results = emission_forecasting_service.backtest_models(vals)
        for r in results:
            assert r.mae is not None
            assert r.rmse is not None
            assert r.mape is not None
            assert r.periods_tested == 3

    def test_63_mape_zero_denominator_protection(self):
        vals = [10.0, 0.0, 15.0, 20.0, 25.0]
        results = emission_forecasting_service.backtest_models(vals)
        for r in results:
            assert r.mae is not None

    def test_64_model_selection_lowest_mae(self):
        vals = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0]
        best_model, results = emission_forecasting_service.select_best_model(vals)
        assert best_model == "LINEAR_TREND"

    def test_65_backtest_insufficient_history(self):
        vals = [10.0, 12.0]
        results = emission_forecasting_service.backtest_models(vals)
        assert results == []

    def test_66_chronological_splitting_no_data_leakage(self):
        vals = [10.0, 20.0, 30.0, 40.0]
        results = emission_forecasting_service.backtest_models(vals)
        assert results[0].periods_tested == 1

    def test_67_backtest_rmse_greater_or_equal_mae(self):
        vals = [10.0, 15.0, 12.0, 18.0, 25.0, 20.0]
        results = emission_forecasting_service.backtest_models(vals)
        for r in results:
            if r.mae is not None and r.rmse is not None:
                assert r.rmse >= r.mae - 1e-6

    def test_68_model_selection_persistence(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        req = ForecastRequest(scope="SCOPE_2")
        res = emission_forecasting_service.generate_forecast(db, req)
        assert res.backtest_mae is not None
        assert res.backtest_results is not None

    def test_69_backtest_successful_predictions_count(self):
        vals = [28.4, 30.1, 31.2, 33.0, 34.1, 35.0]
        results = emission_forecasting_service.backtest_models(vals)
        for r in results:
            assert r.successful_predictions == 3

    def test_70_explanation_mentions_mae(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        req = ForecastRequest(scope="SCOPE_2")
        res = emission_forecasting_service.generate_forecast(db, req)
        assert "MAE" in res.explanation

    def test_71_backtest_results_dto_serialization(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        req = ForecastRequest(scope="SCOPE_2")
        res = emission_forecasting_service.generate_forecast(db, req)
        assert len(res.backtest_results) > 0

    def test_72_reproducible_model_selection(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        req = ForecastRequest(scope="SCOPE_2")
        res1 = emission_forecasting_service.generate_forecast(db, req, save_to_db=False)
        res2 = emission_forecasting_service.generate_forecast(db, req, save_to_db=False)
        assert res1.model_name == res2.model_name
        assert res1.predicted_value == res2.predicted_value

    def test_73_moving_average_selected_for_volatile_series(self):
        vals = [10.0, 50.0, 10.0, 50.0, 10.0, 50.0]
        best_model, _ = emission_forecasting_service.select_best_model(vals)
        assert best_model in ("MOVING_AVERAGE", "EXPONENTIAL_SMOOTHING", "NAIVE")

    def test_74_backtest_with_missing_mape(self):
        vals = [0.0, 0.0, 0.0, 0.0, 0.0]
        results = emission_forecasting_service.backtest_models(vals)
        for r in results:
            assert r.mape is None

    def test_75_selected_model_in_available_models(self):
        vals = [28.4, 30.1, 31.2, 33.0, 34.1, 35.0]
        best_model, _ = emission_forecasting_service.select_best_model(vals)
        available_codes = [m.code for m in AVAILABLE_MODELS]
        assert best_model in available_codes


# =============================================================================
# 6. UNCERTAINTY BOUNDS & CONFIDENCE LABELS (76-85)
# =============================================================================

class TestUncertaintyAndConfidence:
    def test_76_lower_and_upper_bounds_calculated(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        req = ForecastRequest(scope="SCOPE_2")
        res = emission_forecasting_service.generate_forecast(db, req)
        assert res.lower_bound is not None
        assert res.upper_bound is not None
        assert res.lower_bound <= res.predicted_value <= res.upper_bound

    def test_77_lower_bound_non_negative(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        req = ForecastRequest(scope="SCOPE_2")
        res = emission_forecasting_service.generate_forecast(db, req)
        assert res.lower_bound >= 0.0

    def test_78_uncertainty_widens_with_horizon(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        req1 = ForecastRequest(scope="SCOPE_2", horizon=1)
        res1 = emission_forecasting_service.generate_forecast(db, req1, save_to_db=False)

        req4 = ForecastRequest(scope="SCOPE_2", horizon=4)
        res4 = emission_forecasting_service.generate_forecast(db, req4, save_to_db=False)

        width1 = res1.upper_bound - res1.lower_bound
        width4 = res4.upper_bound - res4.lower_bound
        assert width4 >= width1

    def test_79_confidence_label_values(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        req = ForecastRequest(scope="SCOPE_2")
        res = emission_forecasting_service.generate_forecast(db, req)
        assert res.confidence_label in ("HIGH", "MODERATE", "LOW", "INSUFFICIENT_DATA")

    def test_80_null_bounds_for_insufficient_data(self, db_session):
        req = ForecastRequest(scope="SCOPE_2")
        res = emission_forecasting_service.generate_forecast(db_session, req)
        assert res.lower_bound is None
        assert res.upper_bound is None

    def test_81_confidence_level_percentage(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        req = ForecastRequest(scope="SCOPE_2")
        res = emission_forecasting_service.generate_forecast(db, req)
        assert res.confidence_level in (90.0, 75.0, 50.0)

    def test_82_proactive_signal_increase(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        req = ForecastRequest(scope="SCOPE_2")
        res = emission_forecasting_service.generate_forecast(db, req)
        assert res.proactive_signal in ("FORECAST_INCREASE", "FORECAST_UNCERTAIN")

    def test_83_proactive_signal_insufficient(self, db_session):
        req = ForecastRequest(scope="SCOPE_2")
        res = emission_forecasting_service.generate_forecast(db_session, req)
        assert res.proactive_signal == "FORECAST_DATA_INSUFFICIENT"

    def test_84_growth_rate_percentage_calculated(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        req = ForecastRequest(scope="SCOPE_2")
        res = emission_forecasting_service.generate_forecast(db, req)
        assert res.growth_rate_pct is not None

    def test_85_uncertainty_with_zero_variance(self):
        vals = [20.0, 20.0, 20.0, 20.0]
        preds, resids = emission_forecasting_service.forecast_linear_trend(vals, horizon=1)
        assert preds[0] == 20.0


# =============================================================================
# 7. SCOPE 3 & TOTAL FORECAST SAFEGUARDS (86-95)
# =============================================================================

class TestScope3AndTotalSafeguards:
    def test_86_scope_3_insufficient_data_protection(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        req = ForecastRequest(scope="SCOPE_3")
        res = emission_forecasting_service.generate_forecast(db, req)
        assert res.forecast_status == "INSUFFICIENT_DATA"
        assert "Scope 3 cannot be forecast" in res.explanation
        assert res.predicted_value == 0.0

    def test_87_scope_3_not_treated_as_zero(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        req = ForecastRequest(scope="SCOPE_3")
        res = emission_forecasting_service.generate_forecast(db, req)
        assert res.confidence_label == "INSUFFICIENT_DATA"

    def test_88_scope_1_forecasting_when_available(self, db_session):
        for p, v in [("2024-01", 5.0), ("2024-02", 6.0), ("2024-03", 7.0)]:
            e = CarbonLedgerEntry(carbon_calculation_id=1, scope="SCOPE_1", quantity=Decimal(str(v * 1000)), activity_unit="LITERS", calculated_co2e=Decimal(str(v * 1000)), accounting_status="POSTED", reporting_period=p, activity_type="DIESEL")
            db_session.add(e)
        db_session.commit()

        req = ForecastRequest(scope="SCOPE_1")
        res = emission_forecasting_service.generate_forecast(db_session, req)
        assert res.forecast_status == "GENERATED"
        assert res.predicted_value > 0.0

    def test_89_all_scopes_aggregated_total(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        req = ForecastRequest(scope="ALL")
        res = emission_forecasting_service.generate_forecast(db, req)
        assert res.forecast_status == "GENERATED"

    def test_90_category_forecasting(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        req = ForecastRequest(category="ENERGY")
        res = emission_forecasting_service.generate_forecast(db, req)
        assert res.forecast_status == "GENERATED"

    def test_91_activity_forecasting(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        req = ForecastRequest(activity_type="ELECTRICITY")
        res = emission_forecasting_service.generate_forecast(db, req)
        assert res.forecast_status == "GENERATED"

    def test_92_forecast_persistence_record_creation(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        req = ForecastRequest(scope="SCOPE_2")
        res = emission_forecasting_service.generate_forecast(db, req, save_to_db=True)
        assert res.id is not None
        rec = db.query(EmissionForecast).filter(EmissionForecast.id == res.id).first()
        assert rec is not None
        assert rec.forecast_code == res.forecast_code

    def test_93_forecast_versioning_fields(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        req = ForecastRequest(scope="SCOPE_2")
        res = emission_forecasting_service.generate_forecast(db, req, save_to_db=True)
        assert res.model_version == "1.0"
        assert res.forecast_version == "forecast_v1"

    def test_94_list_forecast_history(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        req = ForecastRequest(scope="SCOPE_2")
        emission_forecasting_service.generate_forecast(db, req, save_to_db=True)
        history = emission_forecasting_service.list_forecasts(db)
        assert len(history) >= 1

    def test_95_get_forecast_by_id(self, sample_ledger_history):
        db = sample_ledger_history["db"]
        req = ForecastRequest(scope="SCOPE_2")
        res = emission_forecasting_service.generate_forecast(db, req, save_to_db=True)
        rec = emission_forecasting_service.get_forecast_by_id(db, res.id)
        assert rec is not None
        assert rec.id == res.id


# =============================================================================
# 8. API ENDPOINTS (96-105)
# =============================================================================

@pytest.fixture
def api_db(sample_ledger_history):
    db = sample_ledger_history["db"]
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield db
    app.dependency_overrides.clear()


@pytest.fixture
def client(api_db):
    return TestClient(app)


class TestAPIEndpoints:
    def test_96_api_get_forecast(self, client: TestClient):
        res = client.get("/api/emissions/forecast?scope=SCOPE_2&horizon=1")
        assert res.status_code == 200
        data = res.json()
        assert "predicted_value" in data
        assert data["forecast_status"] == "GENERATED"

    def test_97_api_post_forecast(self, client: TestClient):
        payload = {"scope": "SCOPE_2", "horizon": 2, "model_preference": "LINEAR_TREND"}
        res = client.post("/api/emissions/forecast", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["horizon"] == 2
        assert data["model_name"] == "LINEAR_TREND"

    def test_98_api_get_forecast_models(self, client: TestClient):
        res = client.get("/api/emissions/forecast/models")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 4

    def test_99_api_get_data_quality(self, client: TestClient):
        res = client.get("/api/emissions/forecast/data-quality?scope=SCOPE_2")
        assert res.status_code == 200
        data = res.json()
        assert data["historical_periods"] == 6

    def test_100_api_get_backtest(self, client: TestClient):
        res = client.get("/api/emissions/forecast/backtest?scope=SCOPE_2")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 4

    def test_101_api_get_history(self, client: TestClient):
        client.post("/api/emissions/forecast", json={"scope": "SCOPE_2"})
        res = client.get("/api/emissions/forecast/history")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1

    def test_102_api_get_forecast_by_id(self, client: TestClient, api_db):
        create_res = client.post("/api/emissions/forecast", json={"scope": "SCOPE_2"})
        f_id = create_res.json()["id"]
        res = client.get(f"/api/emissions/forecast/{f_id}")
        assert res.status_code == 200
        assert res.json()["id"] == f_id

    def test_103_api_get_forecast_not_found(self, client: TestClient):
        res = client.get("/api/emissions/forecast/999999")
        assert res.status_code == 404

    def test_104_api_insufficient_data_endpoint(self, client: TestClient):
        res = client.get("/api/emissions/forecast?scope=SCOPE_3")
        assert res.status_code == 200
        data = res.json()
        assert data["forecast_status"] == "INSUFFICIENT_DATA"

    def test_105_api_no_carbon_ledger_mutation(self, client: TestClient, api_db):
        entries_before = api_db.query(CarbonLedgerEntry).count()
        client.get("/api/emissions/forecast?scope=SCOPE_2")
        entries_after = api_db.query(CarbonLedgerEntry).count()
        assert entries_before == entries_after


# =============================================================================
# 9. COPILOT INTEGRATION & SAFETY REFUSALS (106-115)
# =============================================================================

class TestCopilotIntegrationAndSafety:
    def test_106_copilot_intent_forecast_query(self, db_session):
        res = copilot_service.chat(db_session, message="What will my Scope 2 emissions be next month?")
        assert res.intent in ("EMISSION_FORECAST", "EMISSION_FORECAST_EXPLAIN")
        assert "Predictive Emissions Analytics Engine" in res.answer or "estimates future emissions" in res.answer

    def test_107_copilot_safety_why_will_emissions_increase(self, db_session):
        res = copilot_service.chat(db_session, message="Why will Scope 2 increase next month?")
        assert res.intent == "EMISSION_FORECAST_EXPLAIN"
        assert "statistical projection, not proof of the cause" in res.answer
        assert "available data does not establish why" in res.answer

    def test_108_copilot_intent_forecast_confidence(self, db_session):
        res = copilot_service.chat(db_session, message="How reliable is this prediction?")
        assert res.intent == "EMISSION_FORECAST_CONFIDENCE"
        assert "Forecast reliability depends on historical sample size" in res.answer

    def test_109_copilot_intent_forecast_explain(self, db_session):
        res = copilot_service.chat(db_session, message="What does the forecast mean?")
        assert res.intent == "EMISSION_FORECAST_EXPLAIN"
        assert "builds a deterministic time-series" in res.answer

    def test_110_copilot_intent_forecast_trend(self, db_session):
        res = copilot_service.chat(db_session, message="Will my emissions increase next quarter?")
        assert res.intent == "EMISSION_FORECAST_TREND"
        assert "statistical forecast trend evaluates historical POSTED ledger trajectory" in res.answer

    def test_111_copilot_refusal_no_causality_claim(self, db_session):
        res = copilot_service.chat(db_session, message="Why is next month's emission projected to increase?")
        assert "not proof of the cause" in res.answer

    def test_112_copilot_actions_view_forecast(self, db_session):
        res = copilot_service.chat(db_session, message="Show me my predicted emissions.")
        assert res.intent == "EMISSION_FORECAST"
        assert any((a.get("target") if isinstance(a, dict) else getattr(a, "target", "")) == "/forecast" for a in res.actions)

    def test_113_copilot_safety_no_guaranteed_reduction_promise(self, db_session):
        res = copilot_service.chat(db_session, message="Will my emissions definitely decrease next month?")
        assert "statistical" in res.answer.lower()

    def test_114_copilot_context_availability(self, db_session):
        res = copilot_service.chat(db_session, message="What is my emission forecast?")
        assert res.context_available is True

    def test_115_copilot_safety_no_fake_credit_prediction(self, db_session):
        res = copilot_service.chat(db_session, message="How many carbon credits will I get next month?")
        assert "does not predict or issue carbon credits" in res.answer
