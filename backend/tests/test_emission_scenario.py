"""
tests/test_emission_scenario.py — Comprehensive Test Suite for Step 22C (Emissions Scenario Engine).

Tests:
1. Model persistence & relationships
2. Decimal arithmetic precision
3. Scenario creation (REDUCE_ACTIVITY, INCREASE_ACTIVITY, REPLACE_SOURCE, SHIFT_SOURCE, ADD_SOURCE, REMOVE_SOURCE)
4. Baseline extraction strictly from POSTED CarbonLedgerEntry
5. Unresolved factor protection (SCENARIO_NOT_QUANTIFIABLE, NULL reduction, NO_ZERO fallback)
6. Target comparison against active ReductionRoadmap (TARGET_MET, TARGET_NOT_MET, TARGET_NOT_DEFINED)
7. Immutable factor snapshots in ScenarioResult
8. Safeguard Refinement 1: ADD_SOURCE requires existing ActivityData + verified factor
9. Safeguard Refinement 2: Soft archival preservation on delete
10. Safeguard Refinement 3: Unresolved components keep total reduction NULL
11. Immutability of ledger, calculations, activity data, and documents
12. API endpoints and error validation
13. Copilot intent detection and safety refusal boundaries
"""
import pytest
from decimal import Decimal
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from backend.app.database.base import Base
from backend.app.database import get_db
from backend.app.main import app
from backend.app.models.document import Document
from backend.app.models.activity_data import ActivityData
from backend.app.models.emission_factor import EmissionFactor
from backend.app.models.carbon_calculation import CarbonCalculation
from backend.app.models.carbon_ledger import CarbonLedgerEntry
from backend.app.models.reduction_roadmap import ReductionRoadmap
from backend.app.models.emission_scenario import (
    EmissionScenario,
    ScenarioInput,
    ScenarioResult,
)
from backend.app.schemas.emission_scenario import (
    ScenarioCreateRequest,
    ScenarioInputCreate,
    ScenarioUpdateRequest,
)
from backend.app.services.emission_scenario import EmissionScenarioService
from backend.app.services.copilot_context import classify_intent
from backend.app.config.emission_scenario import (
    SCENARIO_TYPE_REDUCE_ACTIVITY,
    SCENARIO_TYPE_INCREASE_ACTIVITY,
    SCENARIO_TYPE_REPLACE_SOURCE,
    SCENARIO_TYPE_SHIFT_SOURCE,
    SCENARIO_TYPE_ADD_SOURCE,
    SCENARIO_TYPE_REMOVE_SOURCE,
    QUANTIFICATION_STATUS_QUANTIFIED,
    QUANTIFICATION_STATUS_NOT_QUANTIFIABLE,
    TARGET_STATUS_MET,
    TARGET_STATUS_NOT_MET,
    TARGET_STATUS_NOT_DEFINED,
    TARGET_STATUS_SCENARIO_NOT_QUANTIFIABLE,
    SCENARIO_STATUS_DRAFT,
    SCENARIO_STATUS_CALCULATED,
    SCENARIO_STATUS_ARCHIVED,
    RESULT_STATUS_QUANTIFIED,
    RESULT_STATUS_UNRESOLVED_FACTOR,
)


from sqlalchemy.pool import StaticPool

# ── TEST FIXTURES ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def db_session():
    """Isolated in-memory SQLite database for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_client(db_session):
    """FastAPI TestClient with overridden get_db dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def seeded_db(db_session):
    """
    Seeds a standard Document (#1), ActivityData, EmissionFactors, CarbonCalculations,
    and POSTED CarbonLedgerEntry actuals mirroring Tara Engineering Works:
    - Grid Electricity: 44,900 kWh @ 0.71 = 31,879.00 kgCO2e (31.879 tCO2e)
    - Diesel Fuel: 420 L @ 2.68 = 1,125.60 kgCO2e (1.1256 tCO2e)
    - Total Baseline: 33,004.60 kgCO2e (33.0046 tCO2e)
    - Note: Solar electricity factor is intentionally NOT seeded to test unresolved factor handling!
    """
    doc = Document(
        id=1,
        filename="tara_engineering_invoice.pdf",
        original_filename="tara_engineering_invoice.pdf",
        file_path="/tmp/tara_engineering_invoice.pdf",
        document_type="UTILITY_BILL",
        company_name="Tara Engineering Works",
        reporting_period="FY2024-Q3",
        file_size=1024,
        mime_type="application/pdf",
        created_at=datetime.utcnow(),
    )
    db_session.add(doc)
    db_session.flush()

    # Factor: Grid Electricity
    grid_factor = EmissionFactor(
        id=1,
        factor_code="EF-IN-ELEC-GRID-2024",
        activity_type="purchased_electricity",
        category="ENERGY",
        factor_name="India National Grid Electricity Average",
        factor_value=0.710000,
        factor_unit="kgCO2e/kWh",
        activity_unit="kWh",
        scope="SCOPE_2",
        geography="India",
        applicable_year=2024,
        source_name="CEA 2024",
        version="1.0",
        status="ACTIVE",
        created_at=datetime.utcnow(),
    )
    # Factor: Diesel
    diesel_factor = EmissionFactor(
        id=2,
        factor_code="EF-IN-DIESEL-STATIONARY",
        activity_type="diesel",
        category="FUEL",
        factor_name="Diesel Fuel Combustion (Stationary DG)",
        factor_value=2.680000,
        factor_unit="kgCO2e/L",
        activity_unit="L",
        scope="SCOPE_1",
        geography="India",
        applicable_year=2024,
        source_name="IPCC / India GHG",
        version="1.0",
        status="ACTIVE",
        created_at=datetime.utcnow(),
    )
    db_session.add_all([grid_factor, diesel_factor])
    db_session.flush()

    # ActivityData: Grid Electricity
    act_grid = ActivityData(
        id=1,
        document_id=1,
        activity_type="purchased_electricity",
        category="ENERGY",
        quantity=Decimal("44900.000000"),
        unit="kWh",
        scope="Scope 2",
        created_at=datetime.utcnow(),
    )
    # ActivityData: Diesel
    act_diesel = ActivityData(
        id=2,
        document_id=1,
        activity_type="diesel",
        category="FUEL",
        quantity=Decimal("420.000000"),
        unit="L",
        scope="Scope 1",
        created_at=datetime.utcnow(),
    )
    db_session.add_all([act_grid, act_diesel])
    db_session.flush()

    # CarbonCalculations
    calc_grid = CarbonCalculation(
        id=1,
        document_id=1,
        activity_data_id=1,
        scope="Scope 2",
        activity_type="purchased_electricity",
        quantity=Decimal("44900.000000"),
        activity_unit="kWh",
        calculated_co2e=Decimal("31879.000000"),
        status="CALCULATED",
        created_at=datetime.utcnow(),
    )
    calc_diesel = CarbonCalculation(
        id=2,
        document_id=1,
        activity_data_id=2,
        scope="Scope 1",
        activity_type="diesel",
        quantity=Decimal("420.000000"),
        activity_unit="L",
        calculated_co2e=Decimal("1125.600000"),
        status="CALCULATED",
        created_at=datetime.utcnow(),
    )
    db_session.add_all([calc_grid, calc_diesel])
    db_session.flush()

    # POSTED CarbonLedgerEntries
    ledger_grid = CarbonLedgerEntry(
        id=1,
        document_id=1,
        activity_data_id=1,
        carbon_calculation_id=1,
        activity_type="purchased_electricity",
        category="ENERGY",
        quantity=Decimal("44900.000000"),
        activity_unit="kWh",
        calculated_co2e=Decimal("31879.000000"),
        emission_factor_id=1,
        factor_code="EF-IN-ELEC-GRID-2024",
        factor_name="India National Grid Electricity Average",
        factor_value=Decimal("0.710000"),
        factor_unit="kgCO2e/kWh",
        factor_source="CEA 2024",
        factor_version="1.0",
        geography="India",
        reporting_period="FY2024-Q3",
        reporting_year=2024,
        scope="Scope 2",
        accounting_status="POSTED",
        created_at=datetime.utcnow(),
    )
    ledger_diesel = CarbonLedgerEntry(
        id=2,
        document_id=1,
        activity_data_id=2,
        carbon_calculation_id=2,
        activity_type="diesel",
        category="FUEL",
        quantity=Decimal("420.000000"),
        activity_unit="L",
        calculated_co2e=Decimal("1125.600000"),
        emission_factor_id=2,
        factor_code="EF-IN-DIESEL-STATIONARY",
        factor_name="Diesel Fuel Combustion (Stationary DG)",
        factor_value=Decimal("2.680000"),
        factor_unit="kgCO2e/L",
        factor_source="IPCC / India GHG",
        factor_version="1.0",
        geography="India",
        reporting_period="FY2024-Q3",
        reporting_year=2024,
        scope="Scope 1",
        accounting_status="POSTED",
        created_at=datetime.utcnow(),
    )
    db_session.add_all([ledger_grid, ledger_diesel])
    db_session.commit()
    return db_session


# ==============================================================================
# 1. MODEL PERSISTENCE & BASIC STRUCTURE (10 Tests)
# ==============================================================================

def test_01_scenario_model_instantiation(seeded_db):
    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Test Scenario",
        scenario_type=SCENARIO_TYPE_REDUCE_ACTIVITY,
        document_id=1,
        target_activity_data_id=2,
        change_percent=Decimal("20.0"),
    )
    scenario = service.create_and_calculate_scenario(seeded_db, req)
    assert scenario.id is not None
    assert scenario.scenario_code.startswith("SCEN-DOC_1-")
    assert scenario.name == "Test Scenario"
    assert scenario.status == SCENARIO_STATUS_CALCULATED


def test_02_scenario_to_dict_contains_all_keys(seeded_db):
    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Diesel -20%",
        scenario_type=SCENARIO_TYPE_REDUCE_ACTIVITY,
        document_id=1,
        target_activity_data_id=2,
        change_percent=Decimal("20.0"),
    )
    sc = service.create_and_calculate_scenario(seeded_db, req)
    d = sc.to_dict()
    assert "scenario_code" in d
    assert "baseline_emissions_kgco2e" in d
    assert "scenario_emissions_kgco2e" in d
    assert "reduction_kgco2e" in d
    assert "target_status" in d


def test_03_scenario_input_persistence(seeded_db):
    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Diesel -20%",
        scenario_type=SCENARIO_TYPE_REDUCE_ACTIVITY,
        document_id=1,
        target_activity_data_id=2,
        change_percent=Decimal("20.0"),
    )
    sc = service.create_and_calculate_scenario(seeded_db, req)
    assert len(sc.inputs) == 1
    inp = sc.inputs[0]
    assert inp.activity_type == "diesel"
    assert inp.baseline_quantity == Decimal("420.000000")
    assert inp.scenario_quantity == Decimal("336.000000")
    assert inp.change_percent == Decimal("20.0000")


def test_04_scenario_result_persistence(seeded_db):
    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Diesel -20%",
        scenario_type=SCENARIO_TYPE_REDUCE_ACTIVITY,
        document_id=1,
        target_activity_data_id=2,
        change_percent=Decimal("20.0"),
    )
    sc = service.create_and_calculate_scenario(seeded_db, req)
    assert len(sc.results) == 2  # Diesel (modified) + Grid Electricity (untouched baseline)
    diesel_res = next((r for r in sc.results if r.activity_type == "diesel"), None)
    assert diesel_res is not None
    assert diesel_res.baseline_emissions_kgco2e == Decimal("1125.600000")
    assert diesel_res.scenario_emissions_kgco2e == Decimal("900.480000")
    assert diesel_res.reduction_kgco2e == Decimal("225.120000")


def test_05_decimal_precision_preserved(seeded_db):
    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Diesel -15.5555%",
        scenario_type=SCENARIO_TYPE_REDUCE_ACTIVITY,
        document_id=1,
        target_activity_data_id=2,
        change_percent=Decimal("15.5555"),
    )
    sc = service.create_and_calculate_scenario(seeded_db, req)
    assert isinstance(sc.baseline_emissions_kgco2e, Decimal)
    assert isinstance(sc.scenario_emissions_kgco2e, Decimal)
    assert isinstance(sc.reduction_kgco2e, Decimal)


def test_06_baseline_sourced_strictly_from_posted_ledger(seeded_db):
    # Add an EXCLUDED entry that should NOT be included in baseline
    excluded_entry = CarbonLedgerEntry(
        document_id=1,
        carbon_calculation_id=2,
        activity_type="diesel",
        quantity=Decimal("100.0"),
        activity_unit="L",
        calculated_co2e=Decimal("268.0"),
        accounting_status="EXCLUDED",
        created_at=datetime.utcnow(),
    )
    seeded_db.add(excluded_entry)
    seeded_db.commit()

    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Diesel -20%",
        scenario_type=SCENARIO_TYPE_REDUCE_ACTIVITY,
        document_id=1,
        target_activity_data_id=2,
        change_percent=Decimal("20.0"),
    )
    sc = service.create_and_calculate_scenario(seeded_db, req)
    assert sc.baseline_emissions_kgco2e == Decimal("33004.600000")


def test_07_baseline_zero_when_no_posted_entries(db_session):
    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Empty Baseline Scenario",
        scenario_type=SCENARIO_TYPE_REDUCE_ACTIVITY,
        document_id=999,
        change_percent=Decimal("20.0"),
    )
    sc = service.create_and_calculate_scenario(db_session, req)
    assert sc.baseline_emissions_kgco2e == Decimal("0.0")
    assert sc.baseline_emissions_tco2e == Decimal("0.0")


def test_08_immutable_factor_snapshots_stored(seeded_db):
    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Diesel -20%",
        scenario_type=SCENARIO_TYPE_REDUCE_ACTIVITY,
        document_id=1,
        target_activity_data_id=2,
        change_percent=Decimal("20.0"),
    )
    sc = service.create_and_calculate_scenario(seeded_db, req)
    diesel_res = next((r for r in sc.results if r.activity_type == "diesel"), None)
    assert diesel_res.factor_code == "EF-IN-DIESEL-STATIONARY"
    assert diesel_res.factor_source == "IPCC / India GHG"
    assert diesel_res.factor_version == "1.0"
    assert diesel_res.baseline_factor == Decimal("2.680000")


def test_09_calculation_formula_stored_in_result(seeded_db):
    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Diesel -20%",
        scenario_type=SCENARIO_TYPE_REDUCE_ACTIVITY,
        document_id=1,
        target_activity_data_id=2,
        change_percent=Decimal("20.0"),
    )
    sc = service.create_and_calculate_scenario(seeded_db, req)
    diesel_res = next((r for r in sc.results if r.activity_type == "diesel"), None)
    assert "336" in diesel_res.calculation_formula
    assert "2.68" in diesel_res.calculation_formula
    assert "900.48" in diesel_res.calculation_formula


def test_10_assumptions_summary_recorded(seeded_db):
    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Diesel -20%",
        scenario_type=SCENARIO_TYPE_REDUCE_ACTIVITY,
        document_id=1,
        target_activity_data_id=2,
        change_percent=Decimal("20.0"),
    )
    sc = service.create_and_calculate_scenario(seeded_db, req)
    assert "Reduced diesel from 420.000000 L to 336.000000 L (-20.0%)" in sc.assumption_summary


# ==============================================================================
# 2. SCENARIO A — DIESEL 20% REDUCTION (10 Tests)
# ==============================================================================

def test_11_manual_qa_scenario_a_diesel_quantities(seeded_db):
    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Scenario A: Reduce Diesel by 20%",
        scenario_type=SCENARIO_TYPE_REDUCE_ACTIVITY,
        document_id=1,
        target_activity_data_id=2,
        change_percent=Decimal("20.0"),
    )
    sc = service.create_and_calculate_scenario(seeded_db, req)
    inp = sc.inputs[0]
    assert inp.baseline_quantity == Decimal("420.000000")
    assert inp.scenario_quantity == Decimal("336.000000")


def test_12_manual_qa_scenario_a_diesel_emissions(seeded_db):
    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Scenario A: Reduce Diesel by 20%",
        scenario_type=SCENARIO_TYPE_REDUCE_ACTIVITY,
        document_id=1,
        target_activity_data_id=2,
        change_percent=Decimal("20.0"),
    )
    sc = service.create_and_calculate_scenario(seeded_db, req)
    diesel_res = next((r for r in sc.results if r.activity_type == "diesel"), None)
    assert diesel_res.baseline_emissions_kgco2e == Decimal("1125.600000")
    assert diesel_res.scenario_emissions_kgco2e == Decimal("900.480000")
    assert diesel_res.reduction_kgco2e == Decimal("225.120000")


def test_13_manual_qa_scenario_a_total_reduction_tco2e(seeded_db):
    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Scenario A: Reduce Diesel by 20%",
        scenario_type=SCENARIO_TYPE_REDUCE_ACTIVITY,
        document_id=1,
        target_activity_data_id=2,
        change_percent=Decimal("20.0"),
    )
    sc = service.create_and_calculate_scenario(seeded_db, req)
    assert sc.reduction_kgco2e == Decimal("225.120000")
    assert sc.reduction_tco2e == Decimal("0.225120")
    assert sc.quantification_status == QUANTIFICATION_STATUS_QUANTIFIED


def test_14_manual_qa_scenario_a_total_scenario_emissions(seeded_db):
    # Baseline 33004.60 - Reduction 225.12 = 32779.48 kgCO2e
    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Scenario A: Reduce Diesel by 20%",
        scenario_type=SCENARIO_TYPE_REDUCE_ACTIVITY,
        document_id=1,
        target_activity_data_id=2,
        change_percent=Decimal("20.0"),
    )
    sc = service.create_and_calculate_scenario(seeded_db, req)
    assert sc.scenario_emissions_kgco2e == Decimal("32779.480000")
    assert sc.scenario_emissions_tco2e == Decimal("32.779480")


def test_15_manual_qa_scenario_a_reduction_percent_relative_to_portfolio(seeded_db):
    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Scenario A: Reduce Diesel by 20%",
        scenario_type=SCENARIO_TYPE_REDUCE_ACTIVITY,
        document_id=1,
        target_activity_data_id=2,
        change_percent=Decimal("20.0"),
    )
    sc = service.create_and_calculate_scenario(seeded_db, req)
    # (225.12 / 33004.60) * 100 = 0.6821%
    assert sc.reduction_percent == Decimal("0.6821")


def test_16_diesel_100_percent_removal(seeded_db):
    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Remove Diesel completely",
        scenario_type=SCENARIO_TYPE_REMOVE_SOURCE,
        document_id=1,
        target_activity_data_id=2,
        change_percent=Decimal("100.0"),
    )
    sc = service.create_and_calculate_scenario(seeded_db, req)
    diesel_res = next((r for r in sc.results if r.activity_type == "diesel"), None)
    assert diesel_res.scenario_quantity == Decimal("0.000000")
    assert diesel_res.scenario_emissions_kgco2e == Decimal("0.000000")
    assert diesel_res.reduction_kgco2e == Decimal("1125.600000")


def test_17_diesel_0_percent_reduction(seeded_db):
    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Diesel 0% reduction",
        scenario_type=SCENARIO_TYPE_REDUCE_ACTIVITY,
        document_id=1,
        target_activity_data_id=2,
        change_percent=Decimal("0.0"),
    )
    sc = service.create_and_calculate_scenario(seeded_db, req)
    assert sc.reduction_kgco2e == Decimal("0.000000")
    assert sc.scenario_emissions_kgco2e == sc.baseline_emissions_kgco2e


def test_18_diesel_increase_activity(seeded_db):
    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Diesel +50% increase",
        scenario_type=SCENARIO_TYPE_INCREASE_ACTIVITY,
        document_id=1,
        target_activity_data_id=2,
        change_percent=Decimal("50.0"),
    )
    sc = service.create_and_calculate_scenario(seeded_db, req)
    diesel_res = next((r for r in sc.results if r.activity_type == "diesel"), None)
    assert diesel_res.scenario_quantity == Decimal("630.000000")
    assert diesel_res.scenario_emissions_kgco2e == Decimal("1688.400000")
    assert diesel_res.reduction_kgco2e == Decimal("-562.800000")


def test_19_multiple_inputs_diesel_and_grid_reduction(seeded_db):
    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Multi-source reduction",
        scenario_type=SCENARIO_TYPE_REDUCE_ACTIVITY,
        document_id=1,
        inputs=[
            ScenarioInputCreate(
                activity_data_id=1,
                activity_type="purchased_electricity",
                change_type=SCENARIO_TYPE_REDUCE_ACTIVITY,
                change_percent=Decimal("10.0"),
            ),
            ScenarioInputCreate(
                activity_data_id=2,
                activity_type="diesel",
                change_type=SCENARIO_TYPE_REDUCE_ACTIVITY,
                change_percent=Decimal("20.0"),
            ),
        ]
    )
    sc = service.create_and_calculate_scenario(seeded_db, req)
    assert sc.quantification_status == QUANTIFICATION_STATUS_QUANTIFIED
    # Grid 10% reduction: 3187.90 kgCO2e. Diesel 20% reduction: 225.12 kgCO2e. Total: 3413.02 kgCO2e
    assert sc.reduction_kgco2e == Decimal("3413.020000")


def test_20_recalculate_scenario_matches_original(seeded_db):
    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Diesel -20%",
        scenario_type=SCENARIO_TYPE_REDUCE_ACTIVITY,
        document_id=1,
        target_activity_data_id=2,
        change_percent=Decimal("20.0"),
    )
    sc = service.create_and_calculate_scenario(seeded_db, req)
    orig_red = sc.reduction_kgco2e

    sc_recalc = service.recalculate_scenario(seeded_db, sc.id)
    assert sc_recalc.reduction_kgco2e == orig_red


# ==============================================================================
# 3. SCENARIO B — SOLAR 30% REPLACEMENT (UNRESOLVED FACTOR) (10 Tests)
# ==============================================================================

def test_21_manual_qa_scenario_b_solar_quantities(seeded_db):
    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Scenario B: 30% Solar Replacement",
        scenario_type=SCENARIO_TYPE_REPLACE_SOURCE,
        document_id=1,
        source_activity_data_id=1,
        replacement_activity_type="solar_electricity",
        replacement_percent=Decimal("30.0"),
    )
    sc = service.create_and_calculate_scenario(seeded_db, req)
    # Remaining grid: 44,900 * 0.70 = 31,430 kWh. Solar: 13,470 kWh.
    rem_grid = next((r for r in sc.results if "Remaining" in r.source_name), None)
    solar_res = next((r for r in sc.results if "solar" in r.source_name.lower()), None)
    assert rem_grid.scenario_quantity == Decimal("31430.000000")
    assert solar_res.scenario_quantity == Decimal("13470.000000")


def test_22_manual_qa_scenario_b_unresolved_solar_factor_emits_not_quantifiable(seeded_db):
    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Scenario B: 30% Solar Replacement",
        scenario_type=SCENARIO_TYPE_REPLACE_SOURCE,
        document_id=1,
        source_activity_data_id=1,
        replacement_activity_type="solar_electricity",
        replacement_percent=Decimal("30.0"),
    )
    sc = service.create_and_calculate_scenario(seeded_db, req)
    assert sc.quantification_status == QUANTIFICATION_STATUS_NOT_QUANTIFIABLE
    assert sc.scenario_emissions_kgco2e is None
    assert sc.scenario_emissions_tco2e is None
    assert sc.reduction_kgco2e is None
    assert sc.reduction_tco2e is None
    assert sc.reduction_percent is None


def test_23_manual_qa_scenario_b_target_status_scenario_not_quantifiable(seeded_db):
    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Scenario B: 30% Solar Replacement",
        scenario_type=SCENARIO_TYPE_REPLACE_SOURCE,
        document_id=1,
        source_activity_data_id=1,
        replacement_activity_type="solar_electricity",
        replacement_percent=Decimal("30.0"),
    )
    sc = service.create_and_calculate_scenario(seeded_db, req)
    assert sc.target_status == TARGET_STATUS_SCENARIO_NOT_QUANTIFIABLE


def test_24_manual_qa_scenario_b_no_zero_substitution_for_missing_factor(seeded_db):
    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Scenario B: 30% Solar Replacement",
        scenario_type=SCENARIO_TYPE_REPLACE_SOURCE,
        document_id=1,
        source_activity_data_id=1,
        replacement_activity_type="solar_electricity",
        replacement_percent=Decimal("30.0"),
    )
    sc = service.create_and_calculate_scenario(seeded_db, req)
    solar_res = next((r for r in sc.results if "solar" in r.source_name.lower()), None)
    assert solar_res.status == RESULT_STATUS_UNRESOLVED_FACTOR
    assert solar_res.scenario_factor is None
    assert solar_res.scenario_emissions_kgco2e is None


def test_25_manual_qa_scenario_b_limitation_summary_disclosed(seeded_db):
    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Scenario B: 30% Solar Replacement",
        scenario_type=SCENARIO_TYPE_REPLACE_SOURCE,
        document_id=1,
        source_activity_data_id=1,
        replacement_activity_type="solar_electricity",
        replacement_percent=Decimal("30.0"),
    )
    sc = service.create_and_calculate_scenario(seeded_db, req)
    assert "Solar/replacement factor for 'solar_electricity' is not currently resolved" in sc.limitation_summary


def test_26_scenario_b_with_resolved_solar_factor_succeeds(seeded_db):
    # Now seed a verified solar emission factor (e.g. 0.000000 kgCO2e/kWh or small lifecycle factor)
    solar_factor = EmissionFactor(
        id=3,
        factor_code="EF-IN-SOLAR-ON-SITE",
        activity_type="solar_electricity",
        category="ENERGY",
        factor_name="On-site Solar PV Generation",
        factor_value=0.000000,
        factor_unit="kgCO2e/kWh",
        activity_unit="kWh",
        scope="SCOPE_2",
        geography="India",
        applicable_year=2024,
        source_name="CEA / India GHG",
        version="1.0",
        status="ACTIVE",
        created_at=datetime.utcnow(),
    )
    seeded_db.add(solar_factor)
    seeded_db.commit()

    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Resolved Solar Scenario",
        scenario_type=SCENARIO_TYPE_REPLACE_SOURCE,
        document_id=1,
        source_activity_data_id=1,
        replacement_activity_type="solar_electricity",
        replacement_percent=Decimal("30.0"),
    )
    sc = service.create_and_calculate_scenario(seeded_db, req)
    assert sc.quantification_status == QUANTIFICATION_STATUS_QUANTIFIED
    # 13,470 kWh grid replaced: 13,470 * 0.71 = 9563.70 kgCO2e reduction
    assert sc.reduction_kgco2e == Decimal("9563.700000")
    assert sc.reduction_tco2e == Decimal("9.563700")


def test_27_shift_source_with_resolved_factors(seeded_db):
    # Shift 25% of diesel to biodiesel (factor 0.50)
    biodiesel_factor = EmissionFactor(
        id=4,
        factor_code="EF-IN-BIODIESEL-STATIONARY",
        activity_type="biodiesel",
        category="FUEL",
        factor_name="Biodiesel Fuel Blend",
        factor_value=0.500000,
        factor_unit="kgCO2e/L",
        activity_unit="L",
        scope="SCOPE_1",
        geography="India",
        applicable_year=2024,
        source_name="India GHG",
        version="1.0",
        status="ACTIVE",
        created_at=datetime.utcnow(),
    )
    seeded_db.add(biodiesel_factor)
    seeded_db.commit()

    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Shift Diesel to Biodiesel 25%",
        scenario_type=SCENARIO_TYPE_SHIFT_SOURCE,
        document_id=1,
        source_activity_data_id=2,
        replacement_activity_type="biodiesel",
        replacement_percent=Decimal("25.0"),
    )
    sc = service.create_and_calculate_scenario(seeded_db, req)
    assert sc.quantification_status == QUANTIFICATION_STATUS_QUANTIFIED
    # 25% of 420 L = 105 L.
    # Diesel savings: 105 * 2.68 = 281.40 kgCO2e.
    # Biodiesel emissions: 105 * 0.50 = 52.50 kgCO2e.
    # Net reduction = 281.40 - 52.50 = 228.90 kgCO2e.
    assert sc.reduction_kgco2e == Decimal("228.900000")


def test_28_safeguard_refinement_1_add_source_requires_verified_link(seeded_db):
    service = EmissionScenarioService()
    # Attempting to add an arbitrary ungrounded source without activity_type or activity_data_id
    with pytest.raises(ValueError):
        ScenarioInputCreate(
            change_type=SCENARIO_TYPE_ADD_SOURCE,
            change_percent=Decimal("50.0"),
        )


def test_29_safeguard_refinement_2_archival_on_delete(seeded_db):
    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Scenario to Archive",
        scenario_type=SCENARIO_TYPE_REDUCE_ACTIVITY,
        document_id=1,
        target_activity_data_id=2,
        change_percent=Decimal("20.0"),
    )
    sc = service.create_and_calculate_scenario(seeded_db, req)
    assert sc.status == SCENARIO_STATUS_CALCULATED

    # Soft delete
    res = service.delete_scenario(seeded_db, sc.id, hard_delete=False)
    assert res is True
    seeded_db.refresh(sc)
    assert sc.status == SCENARIO_STATUS_ARCHIVED


def test_30_safeguard_refinement_3_partial_quantification_keeps_total_null(seeded_db):
    # Scenario with 1 resolved reduction (diesel) and 1 unresolved replacement (solar)
    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Partial Quantification Scenario",
        scenario_type=SCENARIO_TYPE_REDUCE_ACTIVITY,
        document_id=1,
        inputs=[
            ScenarioInputCreate(
                activity_data_id=2,
                activity_type="diesel",
                change_type=SCENARIO_TYPE_REDUCE_ACTIVITY,
                change_percent=Decimal("20.0"),
            ),
            ScenarioInputCreate(
                activity_data_id=1,
                activity_type="purchased_electricity",
                change_type=SCENARIO_TYPE_REPLACE_SOURCE,
                change_percent=Decimal("30.0"),
                replacement_source="solar_electricity",
            ),
        ]
    )
    sc = service.create_and_calculate_scenario(seeded_db, req)
    assert sc.quantification_status == QUANTIFICATION_STATUS_NOT_QUANTIFIABLE
    assert sc.reduction_kgco2e is None
    assert sc.scenario_emissions_kgco2e is None


# ==============================================================================
# 4. TARGET COMPARISON & ROADMAP INTEGRATION (10 Tests)
# ==============================================================================

def test_31_roadmap_target_met(seeded_db):
    # Target: 30 tCO2e (30,000 kgCO2e). Baseline: 33,004.60 kgCO2e.
    roadmap = ReductionRoadmap(
        roadmap_code="RDMP-DOC_1-TEST-MET",
        name="10% Reduction Target Roadmap",
        document_id=1,
        baseline_period="FY2024-Q3",
        baseline_emissions_kgco2e=Decimal("33004.600000"),
        baseline_emissions_tco2e=Decimal("33.004600"),
        target_reduction_percent=Decimal("10.0"),
        target_emissions_kgco2e=Decimal("30000.000000"),
        target_emissions_tco2e=Decimal("30.000000"),
        reduction_gap_kgco2e=Decimal("3004.600000"),
        reduction_gap_tco2e=Decimal("3.004600"),
        created_at=datetime.utcnow(),
    )
    seeded_db.add(roadmap)
    seeded_db.commit()

    # Scenario: 15% grid electricity reduction (4781.85 kgCO2e reduction -> scenario = 28,222.75 kgCO2e <= 30,000)
    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Grid 15% Reduction",
        scenario_type=SCENARIO_TYPE_REDUCE_ACTIVITY,
        document_id=1,
        roadmap_id=roadmap.id,
        target_activity_data_id=1,
        change_percent=Decimal("15.0"),
    )
    sc = service.create_and_calculate_scenario(seeded_db, req)
    assert sc.target_status == TARGET_STATUS_MET
    assert sc.remaining_target_gap_kgco2e < Decimal("0.0")


def test_32_roadmap_target_not_met(seeded_db):
    # Target: 26.40368 tCO2e (26,403.68 kgCO2e). Baseline: 33,004.60 kgCO2e.
    roadmap = ReductionRoadmap(
        roadmap_code="RDMP-DOC_1-TEST-NOT-MET",
        name="20% Target Roadmap",
        document_id=1,
        baseline_period="FY2024-Q3",
        baseline_emissions_kgco2e=Decimal("33004.600000"),
        baseline_emissions_tco2e=Decimal("33.004600"),
        target_reduction_percent=Decimal("20.0"),
        target_emissions_kgco2e=Decimal("26403.680000"),
        target_emissions_tco2e=Decimal("26.403680"),
        reduction_gap_kgco2e=Decimal("6600.920000"),
        reduction_gap_tco2e=Decimal("6.600920"),
        created_at=datetime.utcnow(),
    )
    seeded_db.add(roadmap)
    seeded_db.commit()

    # Scenario: Diesel -20% (reduces only 225.12 kgCO2e -> scenario = 32779.48 > 26403.68)
    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Diesel -20%",
        scenario_type=SCENARIO_TYPE_REDUCE_ACTIVITY,
        document_id=1,
        roadmap_id=roadmap.id,
        target_activity_data_id=2,
        change_percent=Decimal("20.0"),
    )
    sc = service.create_and_calculate_scenario(seeded_db, req)
    assert sc.target_status == TARGET_STATUS_NOT_MET
    assert sc.remaining_target_gap_kgco2e == Decimal("6375.800000")
    assert sc.remaining_target_gap_tco2e == Decimal("6.375800")


def test_33_target_not_defined_when_no_roadmap(seeded_db):
    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Diesel -20%",
        scenario_type=SCENARIO_TYPE_REDUCE_ACTIVITY,
        document_id=1,
        target_activity_data_id=2,
        change_percent=Decimal("20.0"),
    )
    sc = service.create_and_calculate_scenario(seeded_db, req)
    assert sc.target_status == TARGET_STATUS_NOT_DEFINED
    assert sc.remaining_target_gap_kgco2e is None


def test_34_roadmap_target_with_unresolved_factor_is_unquantifiable(seeded_db):
    roadmap = ReductionRoadmap(
        roadmap_code="RDMP-DOC_1-UNRESOLVED",
        name="20% Target Roadmap",
        document_id=1,
        baseline_period="FY2024-Q3",
        baseline_emissions_kgco2e=Decimal("33004.600000"),
        baseline_emissions_tco2e=Decimal("33.004600"),
        target_reduction_percent=Decimal("20.0"),
        target_emissions_kgco2e=Decimal("26403.680000"),
        target_emissions_tco2e=Decimal("26.403680"),
        reduction_gap_kgco2e=Decimal("6600.920000"),
        reduction_gap_tco2e=Decimal("6.600920"),
        created_at=datetime.utcnow(),
    )
    seeded_db.add(roadmap)
    seeded_db.commit()

    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Solar 30% Unresolved",
        scenario_type=SCENARIO_TYPE_REPLACE_SOURCE,
        document_id=1,
        roadmap_id=roadmap.id,
        source_activity_data_id=1,
        replacement_activity_type="solar_electricity",
        replacement_percent=Decimal("30.0"),
    )
    sc = service.create_and_calculate_scenario(seeded_db, req)
    assert sc.target_status == TARGET_STATUS_SCENARIO_NOT_QUANTIFIABLE


def test_35_roadmap_immutability(seeded_db):
    roadmap = ReductionRoadmap(
        roadmap_code="RDMP-DOC_1-IMMUTABLE",
        name="Roadmap Immutability Test",
        document_id=1,
        baseline_period="FY2024-Q3",
        baseline_emissions_kgco2e=Decimal("33004.600000"),
        baseline_emissions_tco2e=Decimal("33.004600"),
        target_reduction_percent=Decimal("20.0"),
        target_emissions_kgco2e=Decimal("26403.680000"),
        target_emissions_tco2e=Decimal("26.403680"),
        reduction_gap_kgco2e=Decimal("6600.920000"),
        reduction_gap_tco2e=Decimal("6.600920"),
        created_at=datetime.utcnow(),
    )
    seeded_db.add(roadmap)
    seeded_db.commit()

    orig_target_kg = roadmap.target_emissions_kgco2e

    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Diesel -20%",
        scenario_type=SCENARIO_TYPE_REDUCE_ACTIVITY,
        document_id=1,
        roadmap_id=roadmap.id,
        target_activity_data_id=2,
        change_percent=Decimal("20.0"),
    )
    service.create_and_calculate_scenario(seeded_db, req)
    seeded_db.refresh(roadmap)
    assert roadmap.target_emissions_kgco2e == orig_target_kg


def test_36_ledger_immutability_after_scenario(seeded_db):
    orig_entries = seeded_db.query(CarbonLedgerEntry).all()
    orig_counts = len(orig_entries)
    orig_co2e_sum = sum(e.calculated_co2e for e in orig_entries)

    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Diesel -20%",
        scenario_type=SCENARIO_TYPE_REDUCE_ACTIVITY,
        document_id=1,
        target_activity_data_id=2,
        change_percent=Decimal("20.0"),
    )
    service.create_and_calculate_scenario(seeded_db, req)

    fresh_entries = seeded_db.query(CarbonLedgerEntry).all()
    assert len(fresh_entries) == orig_counts
    assert sum(e.calculated_co2e for e in fresh_entries) == orig_co2e_sum


def test_37_activity_data_immutability(seeded_db):
    act = seeded_db.query(ActivityData).filter(ActivityData.id == 2).first()
    orig_qty = act.quantity

    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Diesel -20%",
        scenario_type=SCENARIO_TYPE_REDUCE_ACTIVITY,
        document_id=1,
        target_activity_data_id=2,
        change_percent=Decimal("20.0"),
    )
    service.create_and_calculate_scenario(seeded_db, req)
    seeded_db.refresh(act)
    assert act.quantity == orig_qty


def test_38_carbon_calculations_immutability(seeded_db):
    calcs = seeded_db.query(CarbonCalculation).all()
    orig_sum = sum(c.calculated_co2e for c in calcs)

    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Diesel -20%",
        scenario_type=SCENARIO_TYPE_REDUCE_ACTIVITY,
        document_id=1,
        target_activity_data_id=2,
        change_percent=Decimal("20.0"),
    )
    service.create_and_calculate_scenario(seeded_db, req)
    fresh_calcs = seeded_db.query(CarbonCalculation).all()
    assert sum(c.calculated_co2e for c in fresh_calcs) == orig_sum


def test_39_document_immutability(seeded_db):
    doc = seeded_db.query(Document).filter(Document.id == 1).first()
    orig_filename = doc.filename

    service = EmissionScenarioService()
    req = ScenarioCreateRequest(
        name="Diesel -20%",
        scenario_type=SCENARIO_TYPE_REDUCE_ACTIVITY,
        document_id=1,
        target_activity_data_id=2,
        change_percent=Decimal("20.0"),
    )
    service.create_and_calculate_scenario(seeded_db, req)
    seeded_db.refresh(doc)
    assert doc.filename == orig_filename


def test_40_cross_document_isolation(seeded_db):
    # Create Document #2
    doc2 = Document(
        id=2,
        filename="doc2.pdf",
        original_filename="doc2.pdf",
        file_path="/tmp/doc2.pdf",
        file_size=1024,
        mime_type="application/pdf",
        document_type="UTILITY_BILL",
        created_at=datetime.utcnow(),
    )
    seeded_db.add(doc2)
    seeded_db.flush()

    ledger_doc2 = CarbonLedgerEntry(
        id=10,
        document_id=2,
        carbon_calculation_id=1,
        activity_type="purchased_electricity",
        quantity=Decimal("1000.0"),
        activity_unit="kWh",
        calculated_co2e=Decimal("710.0"),
        factor_value=Decimal("0.71"),
        accounting_status="POSTED",
        created_at=datetime.utcnow(),
    )
    seeded_db.add(ledger_doc2)
    seeded_db.commit()

    service = EmissionScenarioService()
    sc1 = service.create_and_calculate_scenario(seeded_db, ScenarioCreateRequest(
        name="Doc 1 Scenario",
        scenario_type=SCENARIO_TYPE_REDUCE_ACTIVITY,
        document_id=1,
        target_activity_data_id=2,
        change_percent=Decimal("20.0"),
    ))
    sc2 = service.create_and_calculate_scenario(seeded_db, ScenarioCreateRequest(
        name="Doc 2 Scenario",
        scenario_type=SCENARIO_TYPE_REDUCE_ACTIVITY,
        document_id=2,
        change_percent=Decimal("20.0"),
    ))

    assert sc1.baseline_emissions_kgco2e == Decimal("33004.600000")
    assert sc2.baseline_emissions_kgco2e == Decimal("710.000000")


# ==============================================================================
# 5. API ENDPOINTS & HTTP CONTRACT (20 Tests)
# ==============================================================================

def test_41_api_create_scenario_success(test_client, seeded_db):
    payload = {
        "name": "API Diesel Scenario",
        "scenario_type": "REDUCE_ACTIVITY",
        "document_id": 1,
        "target_activity_data_id": 2,
        "change_percent": 20.0,
    }
    resp = test_client.post("/api/emission-scenarios", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "API Diesel Scenario"
    assert data["quantification_status"] == "QUANTIFIED"
    assert data["reduction_kgco2e"] == 225.12


def test_42_api_create_scenario_invalid_type(test_client, seeded_db):
    payload = {
        "name": "Bad Type",
        "scenario_type": "INVALID_TYPE",
        "document_id": 1,
    }
    resp = test_client.post("/api/emission-scenarios", json=payload)
    assert resp.status_code == 422


def test_43_api_create_scenario_negative_percent(test_client, seeded_db):
    payload = {
        "name": "Negative Percent",
        "scenario_type": "REDUCE_ACTIVITY",
        "document_id": 1,
        "change_percent": -10.0,
    }
    resp = test_client.post("/api/emission-scenarios", json=payload)
    assert resp.status_code == 422


def test_44_api_create_scenario_over_100_percent_reduction(test_client, seeded_db):
    payload = {
        "name": "Over 100 Percent",
        "scenario_type": "REDUCE_ACTIVITY",
        "document_id": 1,
        "inputs": [
            {
                "activity_type": "diesel",
                "change_type": "REDUCE_ACTIVITY",
                "change_percent": 150.0,
            }
        ]
    }
    resp = test_client.post("/api/emission-scenarios", json=payload)
    assert resp.status_code == 422


def test_45_api_list_scenarios(test_client, seeded_db):
    test_client.post("/api/emission-scenarios", json={
        "name": "Scenario 1",
        "scenario_type": "REDUCE_ACTIVITY",
        "document_id": 1,
        "change_percent": 10.0,
    })
    test_client.post("/api/emission-scenarios", json={
        "name": "Scenario 2",
        "scenario_type": "REDUCE_ACTIVITY",
        "document_id": 1,
        "change_percent": 20.0,
    })
    resp = test_client.get("/api/emission-scenarios")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2


def test_46_api_list_document_scenarios(test_client, seeded_db):
    test_client.post("/api/emission-scenarios", json={
        "name": "Doc 1 Scenario",
        "scenario_type": "REDUCE_ACTIVITY",
        "document_id": 1,
        "change_percent": 10.0,
    })
    resp = test_client.get("/api/emission-scenarios/document/1")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_47_api_get_scenario_detail(test_client, seeded_db):
    create_resp = test_client.post("/api/emission-scenarios", json={
        "name": "Detail Test",
        "scenario_type": "REDUCE_ACTIVITY",
        "document_id": 1,
        "target_activity_data_id": 2,
        "change_percent": 20.0,
    })
    sc_id = create_resp.json()["id"]

    resp = test_client.get(f"/api/emission-scenarios/{sc_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == sc_id
    assert len(resp.json()["results"]) == 2


def test_48_api_get_scenario_not_found(test_client, seeded_db):
    resp = test_client.get("/api/emission-scenarios/99999")
    assert resp.status_code == 404


def test_49_api_recalculate_scenario(test_client, seeded_db):
    create_resp = test_client.post("/api/emission-scenarios", json={
        "name": "Recalc Test",
        "scenario_type": "REDUCE_ACTIVITY",
        "document_id": 1,
        "target_activity_data_id": 2,
        "change_percent": 20.0,
    })
    sc_id = create_resp.json()["id"]

    resp = test_client.post(f"/api/emission-scenarios/{sc_id}/calculate")
    assert resp.status_code == 200
    assert resp.json()["reduction_kgco2e"] == 225.12


def test_50_api_get_scenario_results(test_client, seeded_db):
    create_resp = test_client.post("/api/emission-scenarios", json={
        "name": "Results Test",
        "scenario_type": "REDUCE_ACTIVITY",
        "document_id": 1,
        "target_activity_data_id": 2,
        "change_percent": 20.0,
    })
    sc_id = create_resp.json()["id"]

    resp = test_client.get(f"/api/emission-scenarios/{sc_id}/results")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 2


def test_51_api_patch_scenario_metadata(test_client, seeded_db):
    create_resp = test_client.post("/api/emission-scenarios", json={
        "name": "Original Name",
        "scenario_type": "REDUCE_ACTIVITY",
        "document_id": 1,
        "target_activity_data_id": 2,
        "change_percent": 20.0,
    })
    sc_id = create_resp.json()["id"]

    resp = test_client.patch(f"/api/emission-scenarios/{sc_id}", json={
        "name": "Updated Name",
        "description": "Updated Description",
    })
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"
    assert resp.json()["description"] == "Updated Description"


def test_52_api_soft_delete_archives_scenario(test_client, seeded_db):
    create_resp = test_client.post("/api/emission-scenarios", json={
        "name": "To Archive",
        "scenario_type": "REDUCE_ACTIVITY",
        "document_id": 1,
        "target_activity_data_id": 2,
        "change_percent": 20.0,
    })
    sc_id = create_resp.json()["id"]

    del_resp = test_client.delete(f"/api/emission-scenarios/{sc_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["message"] == "Scenario archived successfully"

    # Verify excluded from default list
    list_resp = test_client.get("/api/emission-scenarios")
    assert list_resp.json()["total"] == 0

    # Verify returned when filtering by status=ARCHIVED
    arch_resp = test_client.get("/api/emission-scenarios?status=ARCHIVED")
    assert arch_resp.json()["total"] == 1


def test_53_api_hard_delete_permanently_removes(test_client, seeded_db):
    create_resp = test_client.post("/api/emission-scenarios", json={
        "name": "To Hard Delete",
        "scenario_type": "REDUCE_ACTIVITY",
        "document_id": 1,
        "target_activity_data_id": 2,
        "change_percent": 20.0,
    })
    sc_id = create_resp.json()["id"]

    del_resp = test_client.delete(f"/api/emission-scenarios/{sc_id}?hard_delete=true")
    assert del_resp.status_code == 200

    get_resp = test_client.get(f"/api/emission-scenarios/{sc_id}")
    assert get_resp.status_code == 404


def test_54_api_unresolved_solar_scenario_returns_null_reductions(test_client, seeded_db):
    payload = {
        "name": "Solar 30% Unresolved",
        "scenario_type": "REPLACE_SOURCE",
        "document_id": 1,
        "source_activity_data_id": 1,
        "replacement_activity_type": "solar_electricity",
        "replacement_percent": 30.0,
    }
    resp = test_client.post("/api/emission-scenarios", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["quantification_status"] == "NOT_QUANTIFIABLE"
    assert data["reduction_kgco2e"] is None
    assert data["target_status"] == "SCENARIO_NOT_QUANTIFIABLE"


def test_55_api_unknown_fields_rejected_by_pydantic(test_client, seeded_db):
    payload = {
        "name": "Bad Payload",
        "scenario_type": "REDUCE_ACTIVITY",
        "document_id": 1,
        "hallucinated_roi": "150%",
    }
    resp = test_client.post("/api/emission-scenarios", json=payload)
    assert resp.status_code == 422


def test_56_api_zero_percent_reduction(test_client, seeded_db):
    payload = {
        "name": "0% Reduction",
        "scenario_type": "REDUCE_ACTIVITY",
        "document_id": 1,
        "target_activity_data_id": 2,
        "change_percent": 0.0,
    }
    resp = test_client.post("/api/emission-scenarios", json=payload)
    assert resp.status_code == 201
    assert resp.json()["reduction_kgco2e"] == 0.0


def test_57_api_100_percent_reduction(test_client, seeded_db):
    payload = {
        "name": "100% Diesel Removal",
        "scenario_type": "REMOVE_SOURCE",
        "document_id": 1,
        "target_activity_data_id": 2,
        "change_percent": 100.0,
    }
    resp = test_client.post("/api/emission-scenarios", json=payload)
    assert resp.status_code == 201
    assert resp.json()["reduction_kgco2e"] == 1125.6


def test_58_api_archive_nonexistent_scenario(test_client, seeded_db):
    resp = test_client.delete("/api/emission-scenarios/99999")
    assert resp.status_code == 404


def test_59_api_patch_nonexistent_scenario(test_client, seeded_db):
    resp = test_client.patch("/api/emission-scenarios/99999", json={"name": "New"})
    assert resp.status_code == 404


def test_60_api_recalculate_nonexistent_scenario(test_client, seeded_db):
    resp = test_client.post("/api/emission-scenarios/99999/calculate")
    assert resp.status_code == 404


# ==============================================================================
# 6. COPILOT INTENTS & SAFETY REFUSALS (20 Tests)
# ==============================================================================

def test_61_copilot_intent_what_if_solar():
    q = "What if I replace 30% of grid electricity with solar?"
    assert classify_intent(q) == "EMISSION_SCENARIO_ANALYSIS"


def test_62_copilot_intent_what_if_diesel():
    q = "What if diesel consumption decreases by 20%?"
    assert classify_intent(q) == "EMISSION_SCENARIO_ANALYSIS"


def test_63_copilot_intent_what_if_grid():
    q = "What if grid electricity consumption decreases by 15%?"
    assert classify_intent(q) == "EMISSION_SCENARIO_ANALYSIS"


def test_64_copilot_intent_scenario_analysis():
    q = "Run an emission scenario analysis on our fuel usage"
    assert classify_intent(q) == "EMISSION_SCENARIO_ANALYSIS"


def test_65_copilot_intent_affect_target():
    q = "How would this scenario affect my 20% reduction target?"
    assert classify_intent(q) == "EMISSION_SCENARIO_ANALYSIS"


def test_66_copilot_intent_what_assumptions_used():
    q = "What assumptions did you use for the solar scenario?"
    assert classify_intent(q) == "EMISSION_SCENARIO_ANALYSIS"


def test_67_copilot_intent_how_much_solar_save():
    q = "How much CO2 will solar save?"
    assert classify_intent(q) == "EMISSION_SCENARIO_ANALYSIS"


def test_68_copilot_intent_can_i_switch_to_solar():
    q = "Can I switch to solar to reduce emissions?"
    assert classify_intent(q) == "EMISSION_SCENARIO_ANALYSIS"


def test_69_copilot_intent_what_if_fuel():
    q = "What if fuel consumption drops by half?"
    assert classify_intent(q) == "EMISSION_SCENARIO_ANALYSIS"


def test_70_copilot_intent_model_a_scenario():
    q = "Model a scenario where we replace electricity"
    assert classify_intent(q) == "EMISSION_SCENARIO_ANALYSIS"


def test_71_copilot_general_help_preserved():
    assert classify_intent("Hello, what can you do?") == "GENERAL_HELP"


def test_72_copilot_carbon_credit_intent_preserved():
    assert classify_intent("Why is my carbon credit readiness score low?") == "CARBON_CREDIT_EXPLAIN_SCORE"


def test_73_copilot_action_recommendation_preserved():
    assert classify_intent("What is my biggest reduction opportunity?") == "ACTION_RECOMMENDATION"


def test_74_copilot_document_review_preserved():
    assert classify_intent("What documents need review?") == "DOCUMENT_REVIEW"


def test_75_copilot_missing_data_preserved():
    assert classify_intent("What data gaps exist?") == "MISSING_DATA"


def test_76_copilot_trend_analysis_preserved():
    assert classify_intent("What is the emissions trend over time?") == "TREND_ANALYSIS"


def test_77_copilot_metric_query_preserved():
    assert classify_intent("What was the latest peak demand?") == "METRIC_QUERY"


def test_78_copilot_document_search_preserved():
    assert classify_intent("Show invoices uploaded") == "DOCUMENT_SEARCH"


def test_79_copilot_emissions_analysis_preserved():
    assert classify_intent("Why did Scope 1 GHG emissions change?") == "EMISSIONS_ANALYSIS"


def test_80_version_constant_matches():
    from backend.app.config.emission_scenario import SCENARIO_CALCULATION_VERSION
    assert SCENARIO_CALCULATION_VERSION == "1.0"
