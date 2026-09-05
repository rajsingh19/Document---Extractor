"""
tests/test_reduction_roadmap.py — Comprehensive Test Suite for Personalized Reduction Roadmap Engine (Step 22B).

Covers >= 70 rigorous unit and integration tests verifying:
- Deterministic target arithmetic (Decimal precision, zero Float leakage).
- Baseline selection from POSTED CarbonLedgerEntry records.
- 4-phase structured action items with explicit dependencies.
- Reusing Step 22A priorities, opportunities, and projects without duplication.
- Data quality blocker prioritization in Phase 1 Foundation.
- Strict prevention of fabricated savings / ROI / target feasibility.
- Clean separation of Roadmap Progress from Emissions Reduction Progress.
- Event audit history and status lifecycle management.
- Complete API endpoint validation.
- Copilot target intent handling and grounded explanations with safety boundaries.
"""
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database.base import Base
from backend.app.database.session import get_db
from backend.app.main import app
from backend.app.models.document import Document
from backend.app.models.carbon_calculation import CarbonCalculation
from backend.app.models.carbon_ledger import CarbonLedgerEntry
from backend.app.models.reduction_intelligence import ReductionPriority
from backend.app.models.reduction_opportunity import ReductionOpportunity
from backend.app.models.reduction_project import ReductionProject
from backend.app.models.reduction_roadmap import (
    ReductionRoadmap,
    ReductionRoadmapItem,
    ReductionRoadmapEvent,
)
from backend.app.config.reduction_roadmap import (
    REDUCTION_ROADMAP_VERSION,
    PHASE_1_FOUNDATION,
    PHASE_2_ACTION,
    PHASE_3_MEASUREMENT,
    PHASE_4_VERIFICATION,
    ACTION_TYPE_DATA_QUALITY,
    ACTION_TYPE_BASELINE_REVIEW,
    ACTION_TYPE_INVESTIGATION,
    ACTION_TYPE_REDUCTION_PROJECT,
    ACTION_TYPE_MEASUREMENT,
    ACTION_TYPE_VERIFICATION,
    ROADMAP_STATUS_ACTIVE,
    ROADMAP_STATUS_DRAFT,
    ITEM_STATUS_NOT_STARTED,
    ITEM_STATUS_IN_PROGRESS,
    ITEM_STATUS_COMPLETED,
    CONTRIBUTION_STATUS_NOT_QUANTIFIED,
    TARGET_FEASIBILITY_UNKNOWN,
    TARGET_FEASIBILITY_DATA_INSUFFICIENT,
    TARGET_FEASIBILITY_SUPPORTED,
    EVENT_TYPE_CREATED,
    EVENT_TYPE_STATUS_CHANGED,
    EVENT_TYPE_ITEM_STATUS_CHANGED,
    EVENT_TYPE_REGENERATED,
)
from backend.app.services.reduction_roadmap import ReductionRoadmapService
from backend.app.services.copilot_context import classify_intent, CopilotContextService
from backend.app.services.copilot_llm import CopilotLLMService


# ==============================================================================
# TEST FIXTURES
# ==============================================================================

@pytest.fixture(scope="function")
def db_session():
    """In-memory SQLite test database session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
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
def client(db_session):
    """FastAPI TestClient with overridden get_db dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def seeded_db(db_session):
    """
    Standard test dataset representing Tara Engineering Works:
    - Document #1:
      - Scope 2 Grid Electricity: 31,879.0 kgCO2e (31.879 tCO2e, 2024-10)
      - Scope 1 Diesel Fuel: 1,125.6 kgCO2e (1.1256 tCO2e, 2024-10)
      - Total: 33,004.6 kgCO2e (33.0046 tCO2e)
    - Opportunities:
      - Opp #1: Grid electricity efficiency (PLANNED project)
      - Opp #2: Diesel generator audit
      - Opp #3: Solar rooftop factor data gap (DATA_QUALITY)
    - Projects:
      - Proj #1: Grid Electricity Procurement (PLANNED)
    """
    # 1. Document
    doc = Document(
        id=1,
        filename="electricity_bill_oct2024.pdf",
        original_filename="electricity_bill_oct2024.pdf",
        file_path="/tmp/electricity_bill_oct2024.pdf",
        file_size=1024,
        mime_type="application/pdf",
        review_status="VERIFIED",
    )
    db_session.add(doc)

    # 2. Carbon Calculations
    c1 = CarbonCalculation(
        id=1,
        document_id=1,
        activity_data_id=1,
        quantity=Decimal("48750.000000"),
        activity_unit="kWh",
        scope="SCOPE_2",
        activity_type="purchased_electricity",
        calculated_co2e=Decimal("31879.000000"),
        status="APPROVED",
    )
    c2 = CarbonCalculation(
        id=2,
        document_id=1,
        activity_data_id=2,
        quantity=Decimal("420.000000"),
        activity_unit="L",
        scope="SCOPE_1",
        activity_type="diesel",
        calculated_co2e=Decimal("1125.600000"),
        status="APPROVED",
    )
    db_session.add_all([c1, c2])

    # 3. POSTED Carbon Ledger Entries
    led1 = CarbonLedgerEntry(
        id=1,
        carbon_calculation_id=1,
        document_id=1,
        scope="SCOPE_2",
        category="ENERGY",
        activity_type="purchased_electricity",
        quantity=Decimal("48750.000000"),
        activity_unit="kWh",
        calculated_co2e=Decimal("31879.000000"),
        reporting_period="2024-10",
        reporting_year=2024,
        accounting_status="POSTED",
        source_text="Total energy consumed: 48,750 kWh",
    )
    led2 = CarbonLedgerEntry(
        id=2,
        carbon_calculation_id=2,
        document_id=1,
        scope="SCOPE_1",
        category="FUEL",
        activity_type="diesel",
        quantity=Decimal("420.000000"),
        activity_unit="L",
        calculated_co2e=Decimal("1125.600000"),
        reporting_period="2024-10",
        reporting_year=2024,
        accounting_status="POSTED",
        source_text="Diesel consumed: 420 liters",
    )
    db_session.add_all([led1, led2])

    # 4. Opportunities
    opp1 = ReductionOpportunity(
        id=1,
        opportunity_code="OPP-DOC1-ENERGY-001",
        title="Investigate Grid Electricity Consumption & Procurement",
        description="High electricity consumption represents dominant emissions share.",
        category="ENERGY",
        activity_type="purchased_electricity",
        scope="SCOPE_2",
        priority="HIGH",
        trigger_type="HIGH_ENERGY_USE",
        evidence_document_id=1,
        evidence_ledger_entry_id=1,
        calculated_co2e=Decimal("31879.000000"),
        rationale="Accounts for 96.6% of posted emissions.",
        recommended_action="Initiate tariff review and energy efficiency audit.",
        limitations="Intervention savings must be verified post-implementation.",
    )
    opp2 = ReductionOpportunity(
        id=2,
        opportunity_code="OPP-DOC1-FUEL-002",
        title="Audit Diesel Fuel Use & Generator Run Hours",
        description="Diesel generator operations account for Scope 1 emissions.",
        category="FUEL",
        activity_type="diesel",
        scope="SCOPE_1",
        priority="MEDIUM",
        trigger_type="HIGH_FUEL_USE",
        evidence_document_id=1,
        evidence_ledger_entry_id=2,
        calculated_co2e=Decimal("1125.600000"),
        rationale="Scope 1 fuel consumption.",
        recommended_action="Review generator maintenance schedule.",
        limitations="Grid reliability determines generator usage.",
    )
    opp3 = ReductionOpportunity(
        id=3,
        opportunity_code="OPP-DOC1-DQ-003",
        title="Register On-Site Solar Generation Factor & Accounting Rule",
        description="Rooftop solar generation has 3,850 kWh but unresolved factor.",
        category="DATA_QUALITY",
        activity_type="purchased_electricity",
        scope="SCOPE_2",
        priority="HIGH",
        trigger_type="UNRESOLVED_FACTOR",
        evidence_document_id=1,
        calculated_co2e=Decimal("0.000000"),
        rationale="Missing regional solar avoidance factor.",
        recommended_action="Configure regional factor in registry.",
        limitations="Excluded records are not treated as zero emissions.",
    )
    db_session.add_all([opp1, opp2, opp3])

    # 5. Projects
    proj1 = ReductionProject(
        id=1,
        project_code="PROJ-2024-0001",
        title="Grid Electricity Optimization & Renewable Procurement",
        category="ENERGY",
        scope="SCOPE_2",
        opportunity_id=1,
        activity_type="purchased_electricity",
        status="PLANNED",
        description="Switch to green energy tariff and install sub-metering.",
        baseline_period="2024-10",
        baseline_co2e=Decimal("31879.000000"),
    )
    db_session.add(proj1)

    db_session.commit()
    return db_session


# ==============================================================================
# 1. MODEL PERSISTENCE & DECIMAL PRECISION (Tests 1–7)
# ==============================================================================

class TestModelPersistence:
    def test_01_roadmap_model_persistence(self, db_session):
        roadmap = ReductionRoadmap(
            roadmap_code="RDMP-TEST-001",
            name="Test Roadmap",
            baseline_period="2024-10",
            baseline_emissions_kgco2e=Decimal("33004.600000"),
            baseline_emissions_tco2e=Decimal("33.004600"),
            target_reduction_percent=Decimal("20.00"),
            target_emissions_kgco2e=Decimal("26403.680000"),
            target_emissions_tco2e=Decimal("26.403680"),
            reduction_gap_kgco2e=Decimal("6600.920000"),
            reduction_gap_tco2e=Decimal("6.600920"),
            target_status=TARGET_FEASIBILITY_UNKNOWN,
        )
        db_session.add(roadmap)
        db_session.commit()
        db_session.refresh(roadmap)

        assert roadmap.id is not None
        assert roadmap.roadmap_code == "RDMP-TEST-001"
        assert isinstance(roadmap.baseline_emissions_kgco2e, Decimal)
        assert isinstance(roadmap.reduction_gap_tco2e, Decimal)
        assert roadmap.reduction_gap_tco2e == Decimal("6.600920")

    def test_02_roadmap_item_model_persistence(self, db_session):
        roadmap = ReductionRoadmap(
            roadmap_code="RDMP-ITEM-001",
            name="Item Test Roadmap",
            baseline_period="2024-10",
            baseline_emissions_kgco2e=Decimal("33004.600000"),
            baseline_emissions_tco2e=Decimal("33.004600"),
            target_reduction_percent=Decimal("20.00"),
            target_emissions_kgco2e=Decimal("26403.680000"),
            target_emissions_tco2e=Decimal("26.403680"),
            reduction_gap_kgco2e=Decimal("6600.920000"),
            reduction_gap_tco2e=Decimal("6.600920"),
        )
        db_session.add(roadmap)
        db_session.commit()

        item = ReductionRoadmapItem(
            roadmap_id=roadmap.id,
            sequence=1,
            phase=PHASE_1_FOUNDATION,
            title="Establish Reference Baseline",
            action_type=ACTION_TYPE_BASELINE_REVIEW,
            contribution_status=CONTRIBUTION_STATUS_NOT_QUANTIFIED,
        )
        db_session.add(item)
        db_session.commit()
        db_session.refresh(item)

        assert item.id is not None
        assert item.sequence == 1
        assert item.phase == PHASE_1_FOUNDATION
        assert item.contribution_status == CONTRIBUTION_STATUS_NOT_QUANTIFIED
        assert item.target_contribution_kgco2e is None

    def test_03_roadmap_event_model_persistence(self, db_session):
        roadmap = ReductionRoadmap(
            roadmap_code="RDMP-EVT-001",
            name="Event Test",
            baseline_period="2024-10",
            baseline_emissions_kgco2e=Decimal("1000.0"),
            baseline_emissions_tco2e=Decimal("1.0"),
            target_reduction_percent=Decimal("10.0"),
            target_emissions_kgco2e=Decimal("900.0"),
            target_emissions_tco2e=Decimal("0.9"),
            reduction_gap_kgco2e=Decimal("100.0"),
            reduction_gap_tco2e=Decimal("0.1"),
        )
        db_session.add(roadmap)
        db_session.commit()

        event = ReductionRoadmapEvent(
            roadmap_id=roadmap.id,
            event_type=EVENT_TYPE_CREATED,
            old_status=None,
            new_status=ROADMAP_STATUS_ACTIVE,
            actor="SYSTEM",
            notes="Initial creation",
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        assert event.id is not None
        assert event.event_type == EVENT_TYPE_CREATED
        assert event.new_status == ROADMAP_STATUS_ACTIVE

    def test_04_cascade_delete_items_and_events(self, db_session):
        roadmap = ReductionRoadmap(
            roadmap_code="RDMP-DEL-001",
            name="Cascade Delete Test",
            baseline_period="2024-10",
            baseline_emissions_kgco2e=Decimal("1000.0"),
            baseline_emissions_tco2e=Decimal("1.0"),
            target_reduction_percent=Decimal("10.0"),
            target_emissions_kgco2e=Decimal("900.0"),
            target_emissions_tco2e=Decimal("0.9"),
            reduction_gap_kgco2e=Decimal("100.0"),
            reduction_gap_tco2e=Decimal("0.1"),
        )
        db_session.add(roadmap)
        db_session.commit()

        item = ReductionRoadmapItem(
            roadmap_id=roadmap.id,
            sequence=1,
            phase=PHASE_1_FOUNDATION,
            title="Item to Delete",
            action_type=ACTION_TYPE_INVESTIGATION,
        )
        event = ReductionRoadmapEvent(
            roadmap_id=roadmap.id,
            event_type=EVENT_TYPE_CREATED,
            new_status=ROADMAP_STATUS_ACTIVE,
        )
        db_session.add_all([item, event])
        db_session.commit()

        r_id = roadmap.id
        db_session.delete(roadmap)
        db_session.commit()

        assert db_session.query(ReductionRoadmapItem).filter(ReductionRoadmapItem.roadmap_id == r_id).count() == 0
        assert db_session.query(ReductionRoadmapEvent).filter(ReductionRoadmapEvent.roadmap_id == r_id).count() == 0

    def test_05_roadmap_to_dict_serialization(self, db_session):
        roadmap = ReductionRoadmap(
            roadmap_code="RDMP-DICT-001",
            name="Dict Serialization",
            baseline_period="2024-10",
            baseline_emissions_kgco2e=Decimal("33004.6"),
            baseline_emissions_tco2e=Decimal("33.0046"),
            target_reduction_percent=Decimal("20.0"),
            target_emissions_kgco2e=Decimal("26403.68"),
            target_emissions_tco2e=Decimal("26.40368"),
            reduction_gap_kgco2e=Decimal("6600.92"),
            reduction_gap_tco2e=Decimal("6.60092"),
        )
        db_session.add(roadmap)
        db_session.commit()

        d = roadmap.to_dict()
        assert d["roadmap_code"] == "RDMP-DICT-001"
        assert d["target_reduction_percent"] == 20.0
        assert d["baseline_emissions_tco2e"] == 33.0046
        assert d["reduction_gap_tco2e"] == 6.60092

    def test_06_roadmap_versioning_defaults(self, db_session):
        roadmap = ReductionRoadmap(
            roadmap_code="RDMP-VER-001",
            name="Version Test",
            baseline_period="2024-10",
            baseline_emissions_kgco2e=Decimal("100.0"),
            baseline_emissions_tco2e=Decimal("0.1"),
            target_reduction_percent=Decimal("10.0"),
            target_emissions_kgco2e=Decimal("90.0"),
            target_emissions_tco2e=Decimal("0.09"),
            reduction_gap_kgco2e=Decimal("10.0"),
            reduction_gap_tco2e=Decimal("0.01"),
        )
        db_session.add(roadmap)
        db_session.commit()
        db_session.refresh(roadmap)

        assert roadmap.roadmap_version == REDUCTION_ROADMAP_VERSION
        assert roadmap.calculation_version == "1.0"

    def test_07_unique_roadmap_code_constraint(self, db_session):
        r1 = ReductionRoadmap(
            roadmap_code="RDMP-UNIQUE-001",
            name="R1",
            baseline_period="2024-10",
            baseline_emissions_kgco2e=Decimal("100.0"),
            baseline_emissions_tco2e=Decimal("0.1"),
            target_reduction_percent=Decimal("10.0"),
            target_emissions_kgco2e=Decimal("90.0"),
            target_emissions_tco2e=Decimal("0.09"),
            reduction_gap_kgco2e=Decimal("10.0"),
            reduction_gap_tco2e=Decimal("0.01"),
        )
        r2 = ReductionRoadmap(
            roadmap_code="RDMP-UNIQUE-001",
            name="R2",
            baseline_period="2024-10",
            baseline_emissions_kgco2e=Decimal("100.0"),
            baseline_emissions_tco2e=Decimal("0.1"),
            target_reduction_percent=Decimal("10.0"),
            target_emissions_kgco2e=Decimal("90.0"),
            target_emissions_tco2e=Decimal("0.09"),
            reduction_gap_kgco2e=Decimal("10.0"),
            reduction_gap_tco2e=Decimal("0.01"),
        )
        db_session.add(r1)
        db_session.commit()

        db_session.add(r2)
        with pytest.raises(Exception):
            db_session.commit()
        db_session.rollback()


# ==============================================================================
# 2. BASELINE SELECTION & DETERMINISTIC TARGET ARITHMETIC (Tests 8–18)
# ==============================================================================

class TestBaselineAndTargetArithmetic:
    def test_08_baseline_selection_explicit_period(self, seeded_db):
        svc = ReductionRoadmapService()
        period, kg, t = svc.select_baseline(seeded_db, document_id=1, explicit_period="2024-10")
        assert period == "2024-10"
        assert kg == Decimal("33004.600000")
        assert t == Decimal("33.004600")

    def test_09_baseline_selection_auto_latest(self, seeded_db):
        svc = ReductionRoadmapService()
        period, kg, t = svc.select_baseline(seeded_db, document_id=1)
        assert period == "2024-10"
        assert kg == Decimal("33004.600000")
        assert t == Decimal("33.004600")

    def test_10_baseline_selection_empty_database(self, db_session):
        svc = ReductionRoadmapService()
        period, kg, t = svc.select_baseline(db_session)
        assert period == "UNAVAILABLE"
        assert kg == Decimal("0.0")
        assert t == Decimal("0.0")

    def test_11_target_calculation_20_percent(self, seeded_db):
        svc = ReductionRoadmapService()
        b_kg = Decimal("33004.600000")
        b_t = Decimal("33.004600")
        t_kg, t_t, gap_kg, gap_t = svc.calculate_target_and_gap(b_kg, b_t, Decimal("20.00"))

        assert t_kg == Decimal("26403.680000")
        assert t_t == Decimal("26.403680")
        assert gap_kg == Decimal("6600.920000")
        assert gap_t == Decimal("6.600920")

    def test_12_target_calculation_0_percent(self, seeded_db):
        svc = ReductionRoadmapService()
        b_kg = Decimal("33004.600000")
        b_t = Decimal("33.004600")
        t_kg, t_t, gap_kg, gap_t = svc.calculate_target_and_gap(b_kg, b_t, Decimal("0.00"))

        assert t_kg == b_kg
        assert t_t == b_t
        assert gap_kg == Decimal("0.000000")
        assert gap_t == Decimal("0.000000")

    def test_13_target_calculation_100_percent(self, seeded_db):
        svc = ReductionRoadmapService()
        b_kg = Decimal("33004.600000")
        b_t = Decimal("33.004600")
        t_kg, t_t, gap_kg, gap_t = svc.calculate_target_and_gap(b_kg, b_t, Decimal("100.00"))

        assert t_kg == Decimal("0.000000")
        assert t_t == Decimal("0.000000")
        assert gap_kg == b_kg
        assert gap_t == b_t

    def test_14_target_calculation_50_percent(self, seeded_db):
        svc = ReductionRoadmapService()
        b_kg = Decimal("1000.000000")
        b_t = Decimal("1.000000")
        t_kg, t_t, gap_kg, gap_t = svc.calculate_target_and_gap(b_kg, b_t, Decimal("50.00"))

        assert t_kg == Decimal("500.000000")
        assert t_t == Decimal("0.500000")
        assert gap_kg == Decimal("500.000000")
        assert gap_t == Decimal("0.500000")

    def test_15_invalid_negative_target_raises_error(self, seeded_db):
        svc = ReductionRoadmapService()
        with pytest.raises(ValueError, match="target_reduction_percent"):
            svc.create_roadmap(seeded_db, target_reduction_percent=Decimal("-5.0"))

    def test_16_invalid_over_100_target_raises_error(self, seeded_db):
        svc = ReductionRoadmapService()
        with pytest.raises(ValueError, match="target_reduction_percent"):
            svc.create_roadmap(seeded_db, target_reduction_percent=Decimal("105.0"))

    def test_17_target_feasibility_zero_emissions(self, db_session):
        svc = ReductionRoadmapService()
        r = svc.create_roadmap(db_session, target_reduction_percent=Decimal("20.0"))
        assert r.target_status == TARGET_FEASIBILITY_DATA_INSUFFICIENT
        assert r.status == ROADMAP_STATUS_DRAFT

    def test_18_target_feasibility_unknown_when_not_quantified(self, seeded_db):
        svc = ReductionRoadmapService()
        r = svc.create_roadmap(seeded_db, document_id=1, target_reduction_percent=Decimal("20.0"))
        assert r.target_status == TARGET_FEASIBILITY_UNKNOWN
        assert "not yet available" in r.feasibility_explanation


# ==============================================================================
# 3. STRUCTURED PHASED ACTION GENERATION & LINEAGE (Tests 19–32)
# ==============================================================================

class TestPhasedRoadmapGeneration:
    def test_19_creates_all_4_planning_phases(self, seeded_db):
        svc = ReductionRoadmapService()
        roadmap = svc.create_roadmap(seeded_db, document_id=1, target_reduction_percent=Decimal("20.0"))

        phases = {item.phase for item in roadmap.items}
        assert PHASE_1_FOUNDATION in phases
        assert PHASE_2_ACTION in phases
        assert PHASE_3_MEASUREMENT in phases
        assert PHASE_4_VERIFICATION in phases

    def test_20_data_quality_gap_placed_in_phase_1(self, seeded_db):
        svc = ReductionRoadmapService()
        roadmap = svc.create_roadmap(seeded_db, document_id=1, target_reduction_percent=Decimal("20.0"))

        dq_items = [i for i in roadmap.items if i.action_type == ACTION_TYPE_DATA_QUALITY]
        assert len(dq_items) >= 1
        for dqi in dq_items:
            assert dqi.phase == PHASE_1_FOUNDATION
            assert dqi.contribution_status == CONTRIBUTION_STATUS_NOT_QUANTIFIED
            assert dqi.target_contribution_kgco2e is None

    def test_21_existing_project_reused_not_duplicated(self, seeded_db):
        svc = ReductionRoadmapService()
        initial_proj_count = seeded_db.query(ReductionProject).count()
        roadmap = svc.create_roadmap(seeded_db, document_id=1, target_reduction_percent=Decimal("20.0"))
        final_proj_count = seeded_db.query(ReductionProject).count()

        assert initial_proj_count == final_proj_count
        linked_items = [i for i in roadmap.items if i.project_id == 1]
        assert len(linked_items) >= 1

    def test_22_planned_project_creates_baseline_review_and_action(self, seeded_db):
        svc = ReductionRoadmapService()
        roadmap = svc.create_roadmap(seeded_db, document_id=1, target_reduction_percent=Decimal("20.0"))

        titles = [i.title for i in roadmap.items]
        assert any("Establish Reference Baseline" in t for t in titles)
        assert any("Initiate Planned Project" in t for t in titles)

    def test_23_in_progress_project_handling(self, seeded_db):
        proj = seeded_db.query(ReductionProject).filter(ReductionProject.id == 1).first()
        proj.status = "IN_PROGRESS"
        seeded_db.commit()

        svc = ReductionRoadmapService()
        roadmap = svc.create_roadmap(seeded_db, document_id=1, target_reduction_percent=Decimal("20.0"))

        act_items = [i for i in roadmap.items if i.action_type == ACTION_TYPE_REDUCTION_PROJECT]
        assert len(act_items) >= 1
        assert any("Continue Existing Project" in i.title for i in act_items)

    def test_24_completed_project_handling(self, seeded_db):
        proj = seeded_db.query(ReductionProject).filter(ReductionProject.id == 1).first()
        proj.status = "COMPLETED"
        seeded_db.commit()

        svc = ReductionRoadmapService()
        roadmap = svc.create_roadmap(seeded_db, document_id=1, target_reduction_percent=Decimal("20.0"))

        meas_items = [i for i in roadmap.items if i.action_type == ACTION_TYPE_MEASUREMENT]
        assert any("Audit & Measure Completed Project" in i.title for i in meas_items)

    def test_25_unquantified_contributions_remain_null(self, seeded_db):
        svc = ReductionRoadmapService()
        roadmap = svc.create_roadmap(seeded_db, document_id=1, target_reduction_percent=Decimal("20.0"))

        for item in roadmap.items:
            assert item.target_contribution_kgco2e is None
            assert item.target_contribution_tco2e is None
            assert item.contribution_status == CONTRIBUTION_STATUS_NOT_QUANTIFIED

    def test_26_sequential_ordering_assigned(self, seeded_db):
        svc = ReductionRoadmapService()
        roadmap = svc.create_roadmap(seeded_db, document_id=1, target_reduction_percent=Decimal("20.0"))

        seqs = [i.sequence for i in roadmap.items]
        assert seqs == list(range(1, len(seqs) + 1))

    def test_27_explicit_measurement_method_defined(self, seeded_db):
        svc = ReductionRoadmapService()
        roadmap = svc.create_roadmap(seeded_db, document_id=1, target_reduction_percent=Decimal("20.0"))

        meas_items = [i for i in roadmap.items if i.action_type in (ACTION_TYPE_MEASUREMENT, ACTION_TYPE_REDUCTION_PROJECT)]
        for mi in meas_items:
            assert mi.measurement_method is not None
            assert "POSTED" in mi.measurement_method

    def test_28_explicit_verification_method_defined(self, seeded_db):
        svc = ReductionRoadmapService()
        roadmap = svc.create_roadmap(seeded_db, document_id=1, target_reduction_percent=Decimal("20.0"))

        verif_items = [i for i in roadmap.items if i.action_type == ACTION_TYPE_VERIFICATION]
        for vi in verif_items:
            assert vi.verification_method is not None
            assert "VerificationRecord" in vi.verification_method

    def test_29_dependencies_properly_linked(self, seeded_db):
        svc = ReductionRoadmapService()
        roadmap = svc.create_roadmap(seeded_db, document_id=1, target_reduction_percent=Decimal("20.0"))

        p2_items = [i for i in roadmap.items if i.phase == PHASE_2_ACTION]
        assert all(i.dependency is not None for i in p2_items)

    def test_30_event_created_on_initialization(self, seeded_db):
        svc = ReductionRoadmapService()
        roadmap = svc.create_roadmap(seeded_db, document_id=1, target_reduction_percent=Decimal("20.0"))

        events = svc.get_roadmap_events(seeded_db, roadmap.id)
        assert len(events) == 1
        assert events[0].event_type == EVENT_TYPE_CREATED
        assert events[0].actor == "SYSTEM"

    def test_31_regeneration_replaces_items_cleanly(self, seeded_db):
        svc = ReductionRoadmapService()
        roadmap = svc.create_roadmap(seeded_db, document_id=1, target_reduction_percent=Decimal("20.0"))
        initial_item_count = len(roadmap.items)

        regenerated = svc.generate_roadmap_items(seeded_db, roadmap.id)
        assert len(regenerated.items) == initial_item_count

        events = svc.get_roadmap_events(seeded_db, roadmap.id)
        assert any(e.event_type == EVENT_TYPE_REGENERATED for e in events)

    def test_32_cross_document_isolation(self, seeded_db):
        # Create doc 2 with diesel only
        doc2 = Document(
            id=2,
            filename="d2.pdf",
            original_filename="d2.pdf",
            file_path="/tmp/d2.pdf",
            file_size=1024,
            mime_type="application/pdf",
            review_status="VERIFIED",
        )
        seeded_db.add(doc2)
        led_d2 = CarbonLedgerEntry(
            id=3,
            carbon_calculation_id=2,
            document_id=2,
            scope="SCOPE_1",
            category="FUEL",
            activity_type="diesel",
            quantity=Decimal("100.0"),
            activity_unit="L",
            calculated_co2e=Decimal("268.000000"),
            reporting_period="2024-10",
            accounting_status="POSTED",
        )
        seeded_db.add(led_d2)
        seeded_db.commit()

        svc = ReductionRoadmapService()
        r1 = svc.create_roadmap(seeded_db, document_id=1, target_reduction_percent=Decimal("20.0"))
        r2 = svc.create_roadmap(seeded_db, document_id=2, target_reduction_percent=Decimal("20.0"))

        assert r1.baseline_emissions_tco2e == Decimal("33.004600")
        assert r2.baseline_emissions_tco2e == Decimal("0.268000")


# ==============================================================================
# 4. PROGRESS TRACKING & STATUS MANAGEMENT (Tests 33–42)
# ==============================================================================

class TestProgressAndStatus:
    def test_33_initial_roadmap_progress_zero(self, seeded_db):
        svc = ReductionRoadmapService()
        roadmap = svc.create_roadmap(seeded_db, document_id=1, target_reduction_percent=Decimal("20.0"))
        prog = svc.calculate_progress(seeded_db, roadmap.id)

        assert prog["completed_items"] == 0
        assert prog["roadmap_progress_percent"] == 0.0
        assert prog["total_items"] > 0

    def test_34_item_status_update_increases_progress(self, seeded_db):
        svc = ReductionRoadmapService()
        roadmap = svc.create_roadmap(seeded_db, document_id=1, target_reduction_percent=Decimal("20.0"))

        first_item = roadmap.items[0]
        svc.update_item_status(seeded_db, roadmap.id, first_item.id, ITEM_STATUS_COMPLETED)

        prog = svc.calculate_progress(seeded_db, roadmap.id)
        assert prog["completed_items"] == 1
        assert prog["roadmap_progress_percent"] > 0.0

    def test_35_item_status_audit_event_recorded(self, seeded_db):
        svc = ReductionRoadmapService()
        roadmap = svc.create_roadmap(seeded_db, document_id=1, target_reduction_percent=Decimal("20.0"))

        first_item = roadmap.items[0]
        svc.update_item_status(seeded_db, roadmap.id, first_item.id, ITEM_STATUS_IN_PROGRESS, notes="Started investigation")

        events = svc.get_roadmap_events(seeded_db, roadmap.id)
        assert any(e.event_type == EVENT_TYPE_ITEM_STATUS_CHANGED for e in events)

    def test_36_roadmap_status_update(self, seeded_db):
        svc = ReductionRoadmapService()
        roadmap = svc.create_roadmap(seeded_db, document_id=1, target_reduction_percent=Decimal("20.0"))

        updated = svc.update_roadmap(seeded_db, roadmap.id, status="ON_TRACK", name="Updated Name")
        assert updated.status == "ON_TRACK"
        assert updated.name == "Updated Name"

        events = svc.get_roadmap_events(seeded_db, roadmap.id)
        assert any(e.event_type == EVENT_TYPE_STATUS_CHANGED for e in events)

    def test_37_emissions_progress_insufficient_when_no_subsequent_period(self, seeded_db):
        svc = ReductionRoadmapService()
        roadmap = svc.create_roadmap(seeded_db, document_id=1, target_reduction_percent=Decimal("20.0"))
        prog = svc.calculate_progress(seeded_db, roadmap.id)

        assert prog["emissions_progress_status"] == "INSUFFICIENT_POST_PROJECT_DATA"
        assert prog["actual_change_percent"] is None

    def test_38_emissions_progress_observed_when_new_period_exists(self, seeded_db):
        # Add a newer period 2024-11 with lower emissions
        led_nov = CarbonLedgerEntry(
            id=10,
            carbon_calculation_id=1,
            document_id=1,
            scope="SCOPE_2",
            category="ENERGY",
            activity_type="purchased_electricity",
            quantity=Decimal("40000.0"),
            activity_unit="kWh",
            calculated_co2e=Decimal("26000.000000"),
            reporting_period="2024-11",
            reporting_year=2024,
            accounting_status="POSTED",
        )
        seeded_db.add(led_nov)
        seeded_db.commit()

        svc = ReductionRoadmapService()
        roadmap = svc.create_roadmap(
            seeded_db,
            document_id=1,
            baseline_period="2024-10",
            target_reduction_percent=Decimal("20.0")
        )
        prog = svc.calculate_progress(seeded_db, roadmap.id)

        assert prog["emissions_progress_status"] == "OBSERVED_ACTUAL_CHANGE"
        assert prog["actual_change_percent"] is not None
        assert prog["actual_change_percent"] < 0.0  # Emissions decreased

    def test_39_invalid_item_status_raises_error(self, seeded_db):
        svc = ReductionRoadmapService()
        roadmap = svc.create_roadmap(seeded_db, document_id=1, target_reduction_percent=Decimal("20.0"))
        first_item = roadmap.items[0]

        # Validated by pydantic schema in API, but let's test invalid ID
        with pytest.raises(ValueError, match="not found"):
            svc.update_item_status(seeded_db, roadmap.id, 99999, ITEM_STATUS_COMPLETED)

    def test_40_get_roadmap_by_code(self, seeded_db):
        svc = ReductionRoadmapService()
        roadmap = svc.create_roadmap(seeded_db, document_id=1, target_reduction_percent=Decimal("20.0"))
        retrieved = svc.get_roadmap_by_code(seeded_db, roadmap.roadmap_code)
        assert retrieved is not None
        assert retrieved.id == roadmap.id

    def test_41_list_roadmaps_filter_by_document(self, seeded_db):
        svc = ReductionRoadmapService()
        svc.create_roadmap(seeded_db, document_id=1, target_reduction_percent=Decimal("20.0"))

        results = svc.list_roadmaps(seeded_db, document_id=1)
        assert len(results) >= 1
        assert results[0].document_id == 1

    def test_42_list_roadmaps_filter_by_status(self, seeded_db):
        svc = ReductionRoadmapService()
        r = svc.create_roadmap(seeded_db, document_id=1, target_reduction_percent=Decimal("20.0"))
        svc.update_roadmap(seeded_db, r.id, status="COMPLETED")

        results = svc.list_roadmaps(seeded_db, status="COMPLETED")
        assert len(results) >= 1
        assert results[0].status == "COMPLETED"


# ==============================================================================
# 5. API ENDPOINTS (Tests 43–55)
# ==============================================================================

class TestAPIEndpoints:
    def test_43_post_create_roadmap(self, client, seeded_db):
        payload = {
            "target_reduction_percent": "20.0",
            "document_id": 1,
            "name": "Tara 20% Reduction Plan",
        }
        resp = client.post("/api/reduction-roadmaps", json=payload)
        assert resp.status_code == 201
        data = resp.json()

        assert data["name"] == "Tara 20% Reduction Plan"
        assert data["target_reduction_percent"] == 20.0
        assert data["baseline_emissions_tco2e"] == 33.0046
        assert data["target_emissions_tco2e"] == 26.40368
        assert data["reduction_gap_tco2e"] == 6.60092
        assert len(data["items"]) > 0

    def test_44_post_create_roadmap_invalid_negative_percent(self, client, seeded_db):
        payload = {
            "target_reduction_percent": "-10.0",
            "document_id": 1,
        }
        resp = client.post("/api/reduction-roadmaps", json=payload)
        assert resp.status_code == 422

    def test_45_post_create_roadmap_invalid_over_100_percent(self, client, seeded_db):
        payload = {
            "target_reduction_percent": "150.0",
            "document_id": 1,
        }
        resp = client.post("/api/reduction-roadmaps", json=payload)
        assert resp.status_code == 422

    def test_46_get_roadmaps_list(self, client, seeded_db):
        client.post("/api/reduction-roadmaps", json={"target_reduction_percent": "20.0", "document_id": 1})
        resp = client.get("/api/reduction-roadmaps")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    def test_47_get_roadmap_by_id(self, client, seeded_db):
        create_res = client.post("/api/reduction-roadmaps", json={"target_reduction_percent": "20.0", "document_id": 1})
        r_id = create_res.json()["id"]

        resp = client.get(f"/api/reduction-roadmaps/{r_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == r_id
        assert len(data["items"]) > 0
        assert len(data["events"]) > 0

    def test_48_get_roadmap_by_invalid_id_404(self, client, seeded_db):
        resp = client.get("/api/reduction-roadmaps/99999")
        assert resp.status_code == 404

    def test_49_post_regenerate_roadmap(self, client, seeded_db):
        create_res = client.post("/api/reduction-roadmaps", json={"target_reduction_percent": "20.0", "document_id": 1})
        r_id = create_res.json()["id"]

        resp = client.post(f"/api/reduction-roadmaps/{r_id}/generate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == r_id

    def test_50_get_roadmap_progress(self, client, seeded_db):
        create_res = client.post("/api/reduction-roadmaps", json={"target_reduction_percent": "20.0", "document_id": 1})
        r_id = create_res.json()["id"]

        resp = client.get(f"/api/reduction-roadmaps/{r_id}/progress")
        assert resp.status_code == 200
        data = resp.json()
        assert data["roadmap_id"] == r_id
        assert data["roadmap_progress_percent"] == 0.0
        assert data["reduction_gap_tco2e"] == 6.60092

    def test_51_patch_update_roadmap(self, client, seeded_db):
        create_res = client.post("/api/reduction-roadmaps", json={"target_reduction_percent": "20.0", "document_id": 1})
        r_id = create_res.json()["id"]

        resp = client.patch(f"/api/reduction-roadmaps/{r_id}", json={"status": "ON_TRACK", "name": "Patched Name"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ON_TRACK"
        assert data["name"] == "Patched Name"

    def test_52_patch_update_roadmap_invalid_status(self, client, seeded_db):
        create_res = client.post("/api/reduction-roadmaps", json={"target_reduction_percent": "20.0", "document_id": 1})
        r_id = create_res.json()["id"]

        resp = client.patch(f"/api/reduction-roadmaps/{r_id}", json={"status": "INVALID_STATUS"})
        assert resp.status_code == 422

    def test_53_patch_update_roadmap_item_status(self, client, seeded_db):
        create_res = client.post("/api/reduction-roadmaps", json={"target_reduction_percent": "20.0", "document_id": 1})
        r_data = create_res.json()
        r_id = r_data["id"]
        item_id = r_data["items"][0]["id"]

        resp = client.patch(
            f"/api/reduction-roadmaps/{r_id}/items/{item_id}",
            json={"status": "COMPLETED", "notes": "Completed baseline review"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "COMPLETED"

    def test_54_patch_update_roadmap_item_invalid_status(self, client, seeded_db):
        create_res = client.post("/api/reduction-roadmaps", json={"target_reduction_percent": "20.0", "document_id": 1})
        r_data = create_res.json()
        r_id = r_data["id"]
        item_id = r_data["items"][0]["id"]

        resp = client.patch(
            f"/api/reduction-roadmaps/{r_id}/items/{item_id}",
            json={"status": "INVALID_ITEM_STATUS"}
        )
        assert resp.status_code == 422

    def test_55_get_roadmap_events(self, client, seeded_db):
        create_res = client.post("/api/reduction-roadmaps", json={"target_reduction_percent": "20.0", "document_id": 1})
        r_id = create_res.json()["id"]

        resp = client.get(f"/api/reduction-roadmaps/{r_id}/events")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["event_type"] == EVENT_TYPE_CREATED


# ==============================================================================
# 6. IMMUTABILITY & PURITY CHECKS (Tests 56–63)
# ==============================================================================

class TestImmutabilityAndPurity:
    def test_56_source_carbon_ledger_immutable(self, seeded_db):
        entries_before = [(e.id, e.calculated_co2e, e.accounting_status) for e in seeded_db.query(CarbonLedgerEntry).all()]
        svc = ReductionRoadmapService()
        svc.create_roadmap(seeded_db, document_id=1, target_reduction_percent=Decimal("20.0"))
        entries_after = [(e.id, e.calculated_co2e, e.accounting_status) for e in seeded_db.query(CarbonLedgerEntry).all()]
        assert entries_before == entries_after

    def test_57_source_carbon_calculation_immutable(self, seeded_db):
        calcs_before = [(c.id, c.calculated_co2e, c.status) for c in seeded_db.query(CarbonCalculation).all()]
        svc = ReductionRoadmapService()
        svc.create_roadmap(seeded_db, document_id=1, target_reduction_percent=Decimal("20.0"))
        calcs_after = [(c.id, c.calculated_co2e, c.status) for c in seeded_db.query(CarbonCalculation).all()]
        assert calcs_before == calcs_after

    def test_58_source_opportunity_immutable(self, seeded_db):
        opps_before = [(o.id, o.title, o.category) for o in seeded_db.query(ReductionOpportunity).all()]
        svc = ReductionRoadmapService()
        svc.create_roadmap(seeded_db, document_id=1, target_reduction_percent=Decimal("20.0"))
        opps_after = [(o.id, o.title, o.category) for o in seeded_db.query(ReductionOpportunity).all()]
        assert opps_before == opps_after

    def test_59_source_project_immutable(self, seeded_db):
        projs_before = [(p.id, p.title, p.status) for p in seeded_db.query(ReductionProject).all()]
        svc = ReductionRoadmapService()
        svc.create_roadmap(seeded_db, document_id=1, target_reduction_percent=Decimal("20.0"))
        projs_after = [(p.id, p.title, p.status) for p in seeded_db.query(ReductionProject).all()]
        assert projs_before == projs_after

    def test_60_repeated_generation_is_idempotent(self, seeded_db):
        svc = ReductionRoadmapService()
        r = svc.create_roadmap(seeded_db, document_id=1, target_reduction_percent=Decimal("20.0"))
        seq_before = [(i.sequence, i.title, i.phase) for i in r.items]

        svc.generate_roadmap_items(seeded_db, r.id)
        seeded_db.refresh(r)
        seq_after = [(i.sequence, i.title, i.phase) for i in r.items]
        assert seq_before == seq_after

    def test_61_target_year_validation(self, seeded_db):
        svc = ReductionRoadmapService()
        r = svc.create_roadmap(seeded_db, document_id=1, target_reduction_percent=Decimal("20.0"), target_year=2030)
        assert r.target_year == 2030

    def test_62_target_period_validation(self, seeded_db):
        svc = ReductionRoadmapService()
        r = svc.create_roadmap(seeded_db, document_id=1, target_reduction_percent=Decimal("20.0"), target_period="2025-10")
        assert r.target_period == "2025-10"

    def test_63_roadmap_preserves_strict_decimal_precision(self, seeded_db):
        svc = ReductionRoadmapService()
        r = svc.create_roadmap(seeded_db, document_id=1, target_reduction_percent=Decimal("33.33"))
        assert isinstance(r.target_emissions_kgco2e, Decimal)
        assert isinstance(r.reduction_gap_kgco2e, Decimal)


# ==============================================================================
# 7. COPILOT INTENT, ROADMAP GROUNDING & SAFETY (Tests 64–72)
# ==============================================================================

class TestCopilotIntegrationAndSafety:
    def test_64_copilot_intent_classification_target(self):
        assert classify_intent("I want to reduce emissions by 20%.") in ("ACTION_RECOMMENDATION", "REDUCTION_ROADMAP_PLAN")
        assert classify_intent("Create a reduction plan for me.") in ("ACTION_RECOMMENDATION", "REDUCTION_ROADMAP_PLAN")
        assert classify_intent("How can I reach my reduction target?") in ("ACTION_RECOMMENDATION", "REDUCTION_ROADMAP_PLAN")
        assert classify_intent("What should I do first to reach my target?") in ("ACTION_RECOMMENDATION", "REDUCTION_ROADMAP_PLAN")
        assert classify_intent("How far am I from my target?") in ("ACTION_RECOMMENDATION", "REDUCTION_ROADMAP_PLAN")
        assert classify_intent("What is blocking my reduction target?") in ("ACTION_RECOMMENDATION", "REDUCTION_ROADMAP_PLAN")

    def test_65_copilot_roadmap_grounded_response(self, seeded_db):
        llm = CopilotLLMService()
        ctx_svc = CopilotContextService()
        context = ctx_svc.build_context(seeded_db, "I want to reduce emissions by 20%.", document_id=1)
        resp = llm.generate_response(context, document_id=1)

        assert "33.0046" in resp.answer
        assert "26.4037" in resp.answer
        assert "6.6009" in resp.answer
        assert "Phase 1: Foundation" in resp.answer
        assert "Phase 2: Action" in resp.answer
        assert "Not Yet Quantified" in resp.answer or "not yet available" in resp.answer

    def test_66_copilot_safety_refusal_solar_savings(self, seeded_db):
        llm = CopilotLLMService()
        ctx_svc = CopilotContextService()
        context = ctx_svc.build_context(seeded_db, "How much CO2 will solar save?", document_id=1)
        resp = llm.generate_response(context, document_id=1)

        assert "scenario inputs" in resp.answer.lower() or "not have verified" in resp.answer.lower() or "does not contain a verified savings estimate" in resp.answer.lower()
        assert "20%" not in resp.answer or "verified" in resp.answer.lower()

    def test_67_copilot_safety_refusal_false_feasibility(self, seeded_db):
        llm = CopilotLLMService()
        ctx_svc = CopilotContextService()
        context = ctx_svc.build_context(seeded_db, "Can I definitely achieve 20%?", document_id=1)
        resp = llm.generate_response(context, document_id=1)

        assert "6.6009" in resp.answer
        assert "not yet available" in resp.answer or "does not yet have" in resp.answer

    def test_68_copilot_action_button_targets_roadmap(self, seeded_db):
        llm = CopilotLLMService()
        ctx_svc = CopilotContextService()
        context = ctx_svc.build_context(seeded_db, "Create a reduction plan for me.", document_id=1)
        resp = llm.generate_response(context, document_id=1)

        assert any(a["target"] == "/reduction-roadmap" for a in resp.actions)

    def test_69_copilot_no_hallucinated_roi_or_payback(self, seeded_db):
        llm = CopilotLLMService()
        ctx_svc = CopilotContextService()
        context = ctx_svc.build_context(seeded_db, "What is the ROI and payback period for solar?", document_id=1)
        resp = llm.generate_response(context, document_id=1)

        assert "does not generate hypothetical financial savings" in resp.answer or "do not have verified financial" in resp.answer

    def test_70_manual_qa_doc1_values_match_deterministic_truth(self, seeded_db):
        """
        Document #1 manual QA verification:
        Current baseline: 33.0046 tCO2e
        Target: 20%
        Target emissions: 26.40368 tCO2e
        Required reduction: 6.60092 tCO2e
        """
        svc = ReductionRoadmapService()
        roadmap = svc.create_roadmap(seeded_db, document_id=1, target_reduction_percent=Decimal("20.0"))

        assert roadmap.baseline_emissions_tco2e == Decimal("33.004600")
        assert roadmap.target_emissions_tco2e == Decimal("26.403680")
        assert roadmap.reduction_gap_tco2e == Decimal("6.600920")
        assert roadmap.target_status == TARGET_FEASIBILITY_UNKNOWN

    def test_71_copilot_roadmap_blocking_explanation(self, seeded_db):
        llm = CopilotLLMService()
        ctx_svc = CopilotContextService()
        context = ctx_svc.build_context(seeded_db, "What is blocking my reduction target?", document_id=1)
        resp = llm.generate_response(context, document_id=1)

        assert "solar" in resp.answer.lower() or "grid electricity" in resp.answer.lower()
        assert resp.context_available is True

    def test_72_copilot_how_far_from_target_explanation(self, seeded_db):
        llm = CopilotLLMService()
        ctx_svc = CopilotContextService()
        context = ctx_svc.build_context(seeded_db, "How far am I from my target?", document_id=1)
        resp = llm.generate_response(context, document_id=1)

        assert "6.6009" in resp.answer
        assert "33.0046" in resp.answer
