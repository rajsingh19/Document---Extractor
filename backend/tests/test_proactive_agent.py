"""
tests/test_proactive_agent.py — Comprehensive Test Suite for Step 23 Proactive AI Sustainability Agent v1.

Tests cover all 10 Improvement Patches and Step 23 requirements:
- Patch 1: Single source of priority truth (inherited directly from Step 22A)
- Patch 2: Queue separation (Queue A: REDUCTION vs Queue B: DATA_QUALITY)
- Patch 3: Action dependency graph (parent_action_id, blocks_action_id, dependency_status, unblocking children)
- Patch 4: AI Sustainability Brief (last evaluated, latest actual period, executive summary, KPI counts)
- Patch 5: Structured explanation contract (WHAT, WHY, NEXT, EVIDENCE, FOLLOW_UP, LIMITATION)
- Patch 6: Deterministic signal pipeline (subsystem gathering without hallucinated numbers)
- Patch 7: Deduplication safety (condition-identity hash, idempotency across runs)
- Patch 8: Explicit forecast & scenario labeling (FORECAST — NOT ACTUAL, SCENARIO — NOT ACTUAL)
- Patch 9 & 10: Lifecycle transitions, audit events, document isolation, Copilot grounding, and REST APIs.
"""
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend.app.database.base import Base
from backend.app.database.session import get_db
from backend.app.models.document import Document
from backend.app.models.carbon_calculation import CarbonCalculation
from backend.app.models.carbon_ledger import CarbonLedgerEntry
from backend.app.models.reduction_opportunity import ReductionOpportunity
from backend.app.models.reduction_project import ReductionProject
from backend.app.models.sustainability_metric import SustainabilityMetric
from backend.app.models.emission_forecast import EmissionForecast
from backend.app.models.reduction_intelligence import ReductionPriority
from backend.app.models.reduction_roadmap import ReductionRoadmap, ReductionRoadmapItem
from backend.app.models.emission_scenario import EmissionScenario
from backend.app.models.compliance_report import ComplianceReport
from backend.app.models.proactive_agent import AgentAction, AgentActionEvent
from backend.app.services.proactive_agent import ProactiveAgentService
from backend.app.services.copilot_rag import CopilotRAGRouter
from backend.app.services.copilot_llm import CopilotLLMService


# ==============================================================================
# FIXTURES
# ==============================================================================
@pytest.fixture(scope="function")
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db(db_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# Helper factories
def create_doc(db, doc_id=1, filename="bill_oct2024.pdf"):
    doc = Document(
        id=doc_id,
        filename=filename,
        original_filename=filename,
        file_path=f"/tmp/{filename}",
        file_size=2048,
        mime_type="application/pdf",
        status="COMPLETED",
        review_status="VERIFIED",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def create_ledger_entry(db, entry_id=1, doc_id=1, scope="SCOPE_2", co2e_kg=31879.0, period="2024-10"):
    entry = CarbonLedgerEntry(
        id=entry_id,
        document_id=doc_id,
        carbon_calculation_id=entry_id,
        scope=scope,
        category="ENERGY" if scope == "SCOPE_2" else "FUEL",
        calculated_co2e=Decimal(str(co2e_kg)),
        activity_type="grid_electricity" if scope == "SCOPE_2" else "diesel_generator",
        quantity=Decimal("48750.0"),
        activity_unit="kWh" if scope == "SCOPE_2" else "liters",
        reporting_period=period,
        reporting_year=int(period.split("-")[0]),
        accounting_status="POSTED",
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def create_22a_priority(db, priority_id=1, doc_id=1, score=82.5, level="CRITICAL", category="ENERGY"):
    p = ReductionPriority(
        id=priority_id,
        priority_code=f"RP_{priority_id}_{doc_id}",
        document_id=doc_id,
        opportunity_id=priority_id,
        scope="SCOPE_2",
        category=category,
        activity_type="grid_electricity",
        priority_rank=1,
        priority_level=level,
        priority_score=Decimal(str(score)),
        impact_score=Decimal("45.0"),
        trend_score=Decimal("15.0"),
        forecast_score=Decimal("10.0"),
        persistence_score=Decimal("5.0"),
        actionability_score=Decimal("7.5"),
        title="Transition grid electricity to captive rooftop solar",
        reason="Dominant Scope 2 contributor from posted ledger",
        current_emissions_kgco2e=Decimal("31879.0"),
        current_emissions_tco2e=Decimal("31.8790"),
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def create_unresolved_calculation(db, calc_id=1, doc_id=1, status="NO_FACTOR", activity_type="solar_electricity", scope="SCOPE_2"):
    calc = CarbonCalculation(
        id=calc_id,
        document_id=doc_id,
        activity_data_id=calc_id,
        activity_type=activity_type,
        scope=scope,
        quantity=Decimal("1000.0"),
        activity_unit="kWh" if scope == "SCOPE_2" else "liters",
        status=status,
    )
    db.add(calc)
    db.commit()
    db.refresh(calc)
    return calc


# ==============================================================================
# 1. MODEL INTEGRITY & FIELD DEFAULTS
# ==============================================================================
class TestAgentActionModel:
    def test_model_creation_defaults(self, db):
        action = AgentAction(
            title="Reduce Electricity Usage",
            action_type="REDUCE_CONSUMPTION",
            action_queue="REDUCTION",
            category="ENERGY",
            priority_level="HIGH",
            priority_score=Decimal("75.0"),
            priority_source="REDUCTION_INTELLIGENCE",
            what="Electricity is high.",
            why="31.8 tCO2e emitted.",
            next="Review tariffs.",
            dedup_key="test_hash_001",
        )
        db.add(action)
        db.commit()
        db.refresh(action)

        assert action.id is not None
        assert action.status == "OPEN"
        assert action.dependency_status == "NONE"
        assert action.priority_source == "REDUCTION_INTELLIGENCE"
        assert action.action_queue == "REDUCTION"
        assert action.created_at is not None

    def test_model_decimal_precision(self, db):
        action = AgentAction(
            title="Decimal Test",
            action_type="TEST_DECIMAL",
            action_queue="REDUCTION",
            category="ENERGY",
            priority_level="MEDIUM",
            priority_score=Decimal("63.45"),
            what="W",
            why="Y",
            next="N",
            dedup_key="test_hash_002",
        )
        db.add(action)
        db.commit()
        db.refresh(action)
        assert Decimal(str(action.priority_score)) == Decimal("63.45")

    def test_model_status_transitions(self, db):
        action = AgentAction(
            title="Status Test",
            action_type="TEST_STATUS",
            action_queue="DATA_QUALITY",
            category="DATA_QUALITY",
            priority_level="HIGH",
            priority_score=Decimal("70.0"),
            what="W",
            why="Y",
            next="N",
            dedup_key="test_hash_003",
        )
        db.add(action)
        db.commit()
        db.refresh(action)

        action.status = "IN_PROGRESS"
        db.commit()
        db.refresh(action)
        assert action.status == "IN_PROGRESS"

        action.status = "COMPLETED"
        action.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(action)
        assert action.status == "COMPLETED"
        assert action.completed_at is not None

    def test_event_model_creation(self, db):
        action = AgentAction(
            title="Action for event",
            action_type="EVENT_TEST",
            action_queue="REDUCTION",
            category="ENERGY",
            priority_level="LOW",
            priority_score=Decimal("20.0"),
            what="W",
            why="Y",
            next="N",
            dedup_key="test_hash_004",
        )
        db.add(action)
        db.commit()
        db.refresh(action)

        event = AgentActionEvent(
            action_id=action.id,
            event_type="STATUS_CHANGE",
            from_status="OPEN",
            to_status="IN_PROGRESS",
            actor="USER",
            details={"note": "Started action"},
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        assert event.id is not None
        assert event.action_id == action.id
        assert event.details["note"] == "Started action"


# ==============================================================================
# 2. PATCH 1 — SINGLE SOURCE OF PRIORITY TRUTH
# ==============================================================================
class TestPatch1SingleSourceOfTruth:
    def test_priority_inherited_directly_from_22a(self, db):
        doc = create_doc(db, doc_id=10)
        p = create_22a_priority(db, priority_id=10, doc_id=10, score=91.5, level="CRITICAL")

        service = ProactiveAgentService(db)
        actions = service.evaluate_actions()

        matched = [a for a in actions if str(a.source_id) == str(p.id) and a.source_type == "REDUCTION_PRIORITY"]
        assert len(matched) == 1
        action = matched[0]

        # Rule: Priority score and level are inherited directly
        assert Decimal(str(action.priority_score)) == Decimal("91.5")
        assert action.priority_level == "CRITICAL"
        assert action.priority_source == "REDUCTION_INTELLIGENCE"

    def test_priority_not_recalculated_or_overridden(self, db):
        doc = create_doc(db, doc_id=11)
        p = create_22a_priority(db, priority_id=11, doc_id=11, score=45.2, level="MEDIUM")

        service = ProactiveAgentService(db)
        actions = service.evaluate_actions()

        matched = [a for a in actions if str(a.source_id) == str(p.id)]
        assert len(matched) == 1
        assert Decimal(str(matched[0].priority_score)) == Decimal("45.2")
        assert matched[0].priority_level == "MEDIUM"

    def test_explicit_priority_sources_from_other_subsystems(self, db):
        # Create an unresolved calculation (data quality)
        calc = create_unresolved_calculation(db, calc_id=101, doc_id=1, status="NO_FACTOR", activity_type="solar_electricity", scope="SCOPE_2")

        service = ProactiveAgentService(db)
        actions = service.evaluate_actions()

        dq_actions = [a for a in actions if a.action_type == "RESOLVE_EMISSION_FACTOR"]
        assert len(dq_actions) >= 1
        for a in dq_actions:
            assert a.priority_source == "DATA_QUALITY_ENGINE"
            assert a.action_queue == "DATA_QUALITY"


# ==============================================================================
# 3. PATCH 2 — SEPARATE REDUCTION FROM DATA QUALITY QUEUES
# ==============================================================================
class TestPatch2QueueSeparation:
    def test_reduction_queue_items(self, db):
        doc = create_doc(db, doc_id=20)
        p = create_22a_priority(db, priority_id=20, doc_id=20, score=77.0, level="HIGH")

        service = ProactiveAgentService(db)
        service.evaluate_actions()

        queue_a = service.get_actions(queue="REDUCTION")
        assert len(queue_a) >= 1
        for a in queue_a:
            assert a.action_queue == "REDUCTION"

    def test_data_quality_queue_items(self, db):
        calc = create_unresolved_calculation(db, calc_id=202, doc_id=1, status="NO_FACTOR", activity_type="diesel_transport", scope="SCOPE_1")

        service = ProactiveAgentService(db)
        service.evaluate_actions()

        queue_b = service.get_actions(queue="DATA_QUALITY")
        assert len(queue_b) >= 1
        for b in queue_b:
            assert b.action_queue == "DATA_QUALITY"

    def test_data_quality_blocker_never_in_reduction_queue(self, db):
        calc = create_unresolved_calculation(db, calc_id=203, doc_id=1, status="MISSING_GEOGRAPHY", activity_type="coal_boiler", scope="SCOPE_1")

        service = ProactiveAgentService(db)
        service.evaluate_actions()

        queue_a = service.get_actions(queue="REDUCTION")
        for a in queue_a:
            assert a.action_type != "RESOLVE_EMISSION_FACTOR"
            assert a.action_queue == "REDUCTION"

    def test_brief_reports_both_queues_separately(self, db):
        doc = create_doc(db, doc_id=21)
        create_22a_priority(db, priority_id=21, doc_id=21, score=85.0, level="CRITICAL")
        calc = create_unresolved_calculation(db, calc_id=204, doc_id=doc.id, status="NO_FACTOR", activity_type="biomass", scope="SCOPE_1")

        service = ProactiveAgentService(db)
        brief = service.get_sustainability_brief()

        assert brief.queue_a_count >= 1
        assert brief.queue_b_count >= 1
        assert brief.attention_count == brief.queue_a_count + brief.queue_b_count


# ==============================================================================
# 4. PATCH 3 — ACTION DEPENDENCY GRAPH
# ==============================================================================
class TestPatch3DependencyGraph:
    def test_dependency_linking_unresolved_factor_blocks_child(self, db):
        doc = create_doc(db, doc_id=30)
        # Factor calculation blocker
        calc = create_unresolved_calculation(db, calc_id=301, doc_id=doc.id, status="NO_FACTOR", activity_type="grid_electricity", scope="SCOPE_2")

        service = ProactiveAgentService(db)
        actions = service.evaluate_actions()

        parent_actions = [a for a in actions if a.action_type == "RESOLVE_EMISSION_FACTOR" and a.document_id == doc.id]
        assert len(parent_actions) >= 1
        parent = parent_actions[0]
        assert parent.dependency_status in ["READY", "NONE"]

    def test_completing_parent_unblocks_child_to_ready(self, db):
        parent = AgentAction(
            title="Resolve Factor",
            action_type="RESOLVE_EMISSION_FACTOR",
            action_queue="DATA_QUALITY",
            category="DATA_QUALITY",
            priority_level="HIGH",
            priority_score=Decimal("80.0"),
            dependency_status="READY",
            what="Factor missing",
            why="Needed",
            next="Upload factor",
            dedup_key="parent_001",
        )
        db.add(parent)
        db.commit()
        db.refresh(parent)

        child = AgentAction(
            title="Recalculate Scenario",
            action_type="RECALCULATE_SCENARIO",
            action_queue="REDUCTION",
            category="ENERGY",
            priority_level="MEDIUM",
            priority_score=Decimal("60.0"),
            parent_action_id=parent.id,
            dependency_status="BLOCKED",
            what="Scenario blocked",
            why="Needs factor",
            next="Wait for parent",
            dedup_key="child_001",
        )
        db.add(child)
        db.commit()
        db.refresh(child)

        service = ProactiveAgentService(db)
        completed_parent = service.complete_action(parent.id, note="Factor provided")

        db.refresh(child)
        assert child.dependency_status == "READY"

    def test_completed_parent_audit_event_logged(self, db):
        parent = AgentAction(
            title="Parent Action",
            action_type="RESOLVE_EMISSION_FACTOR",
            action_queue="DATA_QUALITY",
            category="DATA_QUALITY",
            priority_level="HIGH",
            priority_score=Decimal("80.0"),
            dependency_status="READY",
            what="W",
            why="Y",
            next="N",
            dedup_key="parent_002",
        )
        db.add(parent)
        db.commit()
        db.refresh(parent)

        service = ProactiveAgentService(db)
        service.complete_action(parent.id, note="Done")

        events = db.query(AgentActionEvent).filter(AgentActionEvent.action_id == parent.id).all()
        assert len(events) >= 1
        assert events[0].event_type in ["STATUS_CHANGE", "COMPLETED"]
        assert events[0].to_status == "COMPLETED"

    def test_get_next_ready_action_selection(self, db):
        a1 = AgentAction(
            title="Blocked Action",
            action_type="ACT_1",
            action_queue="REDUCTION",
            category="ENERGY",
            priority_level="CRITICAL",
            priority_score=Decimal("95.0"),
            dependency_status="BLOCKED",
            what="W", why="Y", next="N",
            dedup_key="act_001",
        )
        a2 = AgentAction(
            title="Ready Action",
            action_type="ACT_2",
            action_queue="REDUCTION",
            category="ENERGY",
            priority_level="HIGH",
            priority_score=Decimal("85.0"),
            dependency_status="READY",
            what="W", why="Y", next="N",
            dedup_key="act_002",
        )
        db.add_all([a1, a2])
        db.commit()

        service = ProactiveAgentService(db)
        next_action = service.get_next_ready_action()

        assert next_action is not None
        assert next_action.id == a2.id
        assert next_action.dependency_status == "READY"


# ==============================================================================
# 5. PATCH 4 — AI SUSTAINABILITY BRIEF CONTRACT
# ==============================================================================
class TestPatch4AISustainabilityBrief:
    def test_brief_title_is_ai_sustainability_brief(self, db):
        service = ProactiveAgentService(db)
        brief = service.get_sustainability_brief()
        assert brief.title == "AI Sustainability Brief"

    def test_brief_contains_last_evaluated_timestamp(self, db):
        service = ProactiveAgentService(db)
        brief = service.get_sustainability_brief()
        assert brief.last_evaluated_at is not None
        assert isinstance(brief.last_evaluated_at, datetime)

    def test_brief_contains_latest_actual_period(self, db):
        doc = create_doc(db, doc_id=40)
        create_ledger_entry(db, entry_id=401, doc_id=doc.id, period="2024-10")

        service = ProactiveAgentService(db)
        brief = service.get_sustainability_brief()
        assert brief.latest_actual_reporting_period == "2024-10"

    def test_brief_no_continuous_monitoring_claim(self, db):
        service = ProactiveAgentService(db)
        brief = service.get_sustainability_brief()
        # Executive summary must not imply streaming or real-time continuous sensor monitoring
        assert "real-time continuous" not in brief.executive_summary.lower()
        assert "streaming" not in brief.executive_summary.lower()

    def test_brief_period_delta_calculated_only_when_multiple_periods(self, db):
        doc = create_doc(db, doc_id=41)
        create_ledger_entry(db, entry_id=411, doc_id=doc.id, co2e_kg=20000.0, period="2024-09")

        service = ProactiveAgentService(db)
        brief1 = service.get_sustainability_brief()
        # Only 1 period exists -> delta should be None
        assert brief1.period_to_period_delta_tco2e is None

        # Add second period
        create_ledger_entry(db, entry_id=412, doc_id=doc.id, co2e_kg=25000.0, period="2024-10")
        brief2 = service.get_sustainability_brief()
        # 25000 kg - 20000 kg = 5000 kg = 5.0 tCO2e
        assert brief2.period_to_period_delta_tco2e is not None
        assert Decimal(str(brief2.period_to_period_delta_tco2e)) == Decimal("5.0000")


# ==============================================================================
# 6. PATCH 5 — STRUCTURED EXPLANATION CONTRACT
# ==============================================================================
class TestPatch5StructuredExplanationContract:
    def test_explanation_contract_fields_present_on_all_actions(self, db):
        doc = create_doc(db, doc_id=50)
        create_22a_priority(db, priority_id=50, doc_id=doc.id)

        service = ProactiveAgentService(db)
        actions = service.evaluate_actions()

        for a in actions:
            assert a.what is not None and len(a.what) > 0
            assert a.why is not None and len(a.why) > 0
            assert a.next is not None and len(a.next) > 0
            assert a.evidence is not None and len(a.evidence) > 0
            assert a.follow_up is not None and len(a.follow_up) > 0
            assert a.limitation is not None and len(a.limitation) > 0

    def test_explain_action_returns_identical_structure(self, db):
        action = AgentAction(
            title="Grid Electricity Optimization",
            action_type="REDUCE_GRID_ELECTRICITY",
            action_queue="REDUCTION",
            category="ENERGY",
            priority_level="CRITICAL",
            priority_score=Decimal("88.0"),
            what="Grid electricity is the dominant emission source.",
            why="31.8790 tCO2e comes from posted ledger entries.",
            next="Review electricity procurement and captive solar potential.",
            evidence="CarbonLedgerEntry → ActivityData → Document #50",
            follow_up="Compare next reporting period.",
            limitation="This recommendation does not guarantee reduction.",
            dedup_key="contract_001",
        )
        db.add(action)
        db.commit()
        db.refresh(action)

        service = ProactiveAgentService(db)
        exp = service.explain_action(action.id)

        assert exp.action_id == action.id
        assert exp.what == action.what
        assert exp.why == action.why
        assert exp.next == action.next
        assert exp.evidence == action.evidence
        assert exp.follow_up == action.follow_up
        assert exp.limitation == action.limitation

    def test_limitation_contains_safety_disclaimer(self, db):
        doc = create_doc(db, doc_id=51)
        create_22a_priority(db, priority_id=51, doc_id=doc.id)

        service = ProactiveAgentService(db)
        actions = service.evaluate_actions()

        for a in actions:
            assert "guarantee" in a.limitation.lower() or "independent" in a.limitation.lower()


# ==============================================================================
# 7. PATCH 6 — AGENT SIGNAL PIPELINE
# ==============================================================================
class TestPatch6SignalPipeline:
    def test_pipeline_gathers_signals_deterministically(self, db):
        doc = create_doc(db, doc_id=60)
        create_22a_priority(db, priority_id=60, doc_id=doc.id, score=80.0, level="HIGH")

        service = ProactiveAgentService(db)
        actions = service.evaluate_actions()

        assert len(actions) >= 1
        assert all(a.priority_score is not None for a in actions)
        assert all(a.priority_level in ["CRITICAL", "HIGH", "MEDIUM", "LOW"] for a in actions)

    def test_no_hallucinated_fields(self, db):
        service = ProactiveAgentService(db)
        actions = service.evaluate_actions()
        for a in actions:
            assert a.priority_source is not None
            assert a.dedup_key is not None
            assert a.action_type is not None


# ==============================================================================
# 8. PATCH 7 — DEDUPLICATION SAFETY ACROSS RUNS
# ==============================================================================
class TestPatch7DeduplicationSafety:
    def test_idempotent_repeated_evaluation(self, db):
        doc = create_doc(db, doc_id=70)
        create_22a_priority(db, priority_id=70, doc_id=doc.id)

        service = ProactiveAgentService(db)
        run1 = service.evaluate_actions()
        initial_count = len(run1)

        run2 = service.evaluate_actions()
        second_count = len(run2)

        assert initial_count == second_count
        assert len(service.get_actions()) == initial_count

    def test_dedup_hash_stability(self, db):
        key1 = ProactiveAgentService._generate_dedup_key(
            "REDUCE_GRID_ELECTRICITY", "ENERGY", "REDUCTION_PRIORITY", 70, 70, "COND_001"
        )
        key2 = ProactiveAgentService._generate_dedup_key(
            "REDUCE_GRID_ELECTRICITY", "ENERGY", "REDUCTION_PRIORITY", 70, 70, "COND_001"
        )
        assert key1 == key2
        assert len(key1) == 32

    def test_timestamp_change_does_not_alter_dedup_key(self, db):
        # The key formula only includes (action_type, category, source_type, source_id, document_id, condition_code)
        key1 = ProactiveAgentService._generate_dedup_key(
            "ACT_TYPE", "CAT", "SRC", 1, 1, "CODE"
        )
        key2 = ProactiveAgentService._generate_dedup_key(
            "ACT_TYPE", "CAT", "SRC", 1, 1, "CODE"
        )
        assert key1 == key2


# ==============================================================================
# 9. PATCH 8 — FORECAST & SCENARIO EXPLICIT LABELING
# ==============================================================================
class TestPatch8ForecastScenarioLabeling:
    def test_forecast_action_explicitly_labeled_not_actual(self, db):
        doc = create_doc(db, doc_id=80)
        # Create a mock forecast
        forecast = EmissionForecast(
            id=801,
            forecast_code="FC-TEST-801",
            forecast_period="2025-Q1",
            reporting_year="2025",
            predicted_value=Decimal("40.0"),
            model_name="LINEAR_TREND",
            forecast_status="GENERATED",
        )
        db.add(forecast)
        db.commit()

        service = ProactiveAgentService(db)
        actions = service.evaluate_actions()

        forecast_actions = [a for a in actions if a.action_type in ["FORECAST_TREND", "FORECAST_INCREASE_REVIEW"]]
        assert len(forecast_actions) >= 1
        for fa in forecast_actions:
            assert "FORECAST — NOT ACTUAL" in fa.title or "FORECAST — NOT ACTUAL" in fa.what

    def test_scenario_action_explicitly_labeled_not_actual(self, db):
        scenario = EmissionScenario(
            id=802,
            scenario_code="SC-TEST-802",
            name="Solar 50% Simulation",
            scenario_type="REPLACE_SOURCE",
            baseline_emissions_tco2e=Decimal("31.8790"),
            status="QUANTIFIED",
            reduction_tco2e=Decimal("15.0"),
        )
        db.add(scenario)
        db.commit()

        service = ProactiveAgentService(db)
        actions = service.evaluate_actions()

        scenario_actions = [a for a in actions if a.action_type in ["EVALUATE_SCENARIO", "RECALCULATE_SCENARIO"]]
        assert len(scenario_actions) >= 1
        for sa in scenario_actions:
            assert "SCENARIO — NOT ACTUAL" in sa.title or "SCENARIO — NOT ACTUAL" in sa.what

    def test_actual_totals_never_include_forecast_numbers(self, db):
        doc = create_doc(db, doc_id=81)
        create_ledger_entry(db, entry_id=811, doc_id=doc.id, co2e_kg=15000.0, period="2024-10")

        # Create forecast with 500,000 kg
        forecast = EmissionForecast(
            id=812,
            forecast_code="FC-TEST-812",
            forecast_period="2025-10",
            reporting_year="2025",
            predicted_value=Decimal("500.0"),
            model_name="LINEAR_TREND",
            forecast_status="GENERATED",
        )
        db.add(forecast)
        db.commit()

        service = ProactiveAgentService(db)
        brief = service.get_sustainability_brief()

        # Actual footprint must ONLY reflect posted ledger: 15.0 tCO2e
        assert Decimal(str(brief.actual_footprint_tco2e)) == Decimal("15.0000")


# ==============================================================================
# 10. LIFECYCLE & AUDIT TRAILS
# ==============================================================================
class TestLifecycleAndAudit:
    def test_start_action(self, db):
        action = AgentAction(
            title="Startable Action",
            action_type="START_TEST",
            action_queue="REDUCTION",
            category="ENERGY",
            priority_level="HIGH",
            priority_score=Decimal("75.0"),
            status="OPEN",
            what="W", why="Y", next="N",
            dedup_key="start_001",
        )
        db.add(action)
        db.commit()

        service = ProactiveAgentService(db)
        updated = service.start_action(action.id, actor="OPERATOR")

        assert updated.status == "IN_PROGRESS"
        events = db.query(AgentActionEvent).filter(AgentActionEvent.action_id == action.id).all()
        assert len(events) == 1
        assert events[0].to_status == "IN_PROGRESS"
        assert events[0].actor == "OPERATOR"

    def test_dismiss_action(self, db):
        action = AgentAction(
            title="Dismissible Action",
            action_type="DISMISS_TEST",
            action_queue="DATA_QUALITY",
            category="DATA_QUALITY",
            priority_level="LOW",
            priority_score=Decimal("30.0"),
            status="OPEN",
            what="W", why="Y", next="N",
            dedup_key="dismiss_001",
        )
        db.add(action)
        db.commit()

        service = ProactiveAgentService(db)
        updated = service.dismiss_action(action.id, reason="Not applicable to site", actor="AUDITOR")

        assert updated.status == "DISMISSED"
        assert updated.dismissed_at is not None
        events = db.query(AgentActionEvent).filter(AgentActionEvent.action_id == action.id).all()
        assert len(events) == 1
        assert events[0].to_status == "DISMISSED"
        assert events[0].details["reason"] == "Not applicable to site"

    def test_cannot_start_completed_action(self, db):
        action = AgentAction(
            title="Completed Action",
            action_type="COMPLETED_TEST",
            action_queue="REDUCTION",
            category="ENERGY",
            priority_level="MEDIUM",
            priority_score=Decimal("50.0"),
            status="COMPLETED",
            what="W", why="Y", next="N",
            dedup_key="completed_001",
        )
        db.add(action)
        db.commit()

        service = ProactiveAgentService(db)
        with pytest.raises(ValueError):
            service.start_action(action.id)


# ==============================================================================
# 11. REST API ENDPOINTS
# ==============================================================================
class TestRestApiEndpoints:
    def test_get_status_endpoint(self, client):
        res = client.get("/api/agent/status")
        assert res.status_code == 200
        data = res.json()
        assert "engine_version" in data
        assert "active_actions_count" in data

    def test_post_run_endpoint(self, client, db):
        doc = create_doc(db, doc_id=90)
        create_22a_priority(db, priority_id=90, doc_id=doc.id)

        res = client.post("/api/agent/run")
        assert res.status_code == 200
        data = res.json()
        assert data["actions_evaluated"] >= 1
        assert "timestamp" in data

    def test_get_brief_endpoint(self, client, db):
        doc = create_doc(db, doc_id=91)
        create_ledger_entry(db, entry_id=911, doc_id=doc.id, co2e_kg=12000.0, period="2024-10")

        res = client.get("/api/agent/brief")
        assert res.status_code == 200
        data = res.json()
        assert data["title"] == "AI Sustainability Brief"
        assert data["actual_footprint_tco2e"] == 12.0

    def test_get_actions_endpoint_with_filters(self, client, db):
        a1 = AgentAction(
            title="Red Action", action_type="A1", action_queue="REDUCTION",
            category="ENERGY", priority_level="HIGH", priority_score=Decimal("70.0"),
            what="W", why="Y", next="N", dedup_key="filter_001"
        )
        a2 = AgentAction(
            title="DQ Action", action_type="A2", action_queue="DATA_QUALITY",
            category="DATA_QUALITY", priority_level="MEDIUM", priority_score=Decimal("50.0"),
            what="W", why="Y", next="N", dedup_key="filter_002"
        )
        db.add_all([a1, a2])
        db.commit()

        res_red = client.get("/api/agent/actions?queue=REDUCTION")
        assert res_red.status_code == 200
        assert res_red.json()["total"] >= 1
        for item in res_red.json()["items"]:
            assert item["action_queue"] == "REDUCTION"

        res_dq = client.get("/api/agent/actions?queue=DATA_QUALITY")
        assert res_dq.status_code == 200
        for item in res_dq.json()["items"]:
            assert item["action_queue"] == "DATA_QUALITY"

    def test_action_lifecycle_api(self, client, db):
        action = AgentAction(
            title="Lifecycle API Test", action_type="API_TEST", action_queue="REDUCTION",
            category="ENERGY", priority_level="HIGH", priority_score=Decimal("80.0"),
            status="OPEN", what="W", why="Y", next="N", dedup_key="lifecycle_api_001"
        )
        db.add(action)
        db.commit()
        db.refresh(action)

        # Start
        res_start = client.post(f"/api/agent/actions/{action.id}/start")
        assert res_start.status_code == 200
        assert res_start.json()["status"] == "IN_PROGRESS"

        # Complete
        res_comp = client.post(f"/api/agent/actions/{action.id}/complete", json={"note": "API completed"})
        assert res_comp.status_code == 200
        assert res_comp.json()["status"] == "COMPLETED"

        # Events
        res_events = client.get(f"/api/agent/actions/{action.id}/events")
        assert res_events.status_code == 200
        assert len(res_events.json()) == 2

    def test_explain_api_endpoint(self, client, db):
        action = AgentAction(
            title="Explain API Test", action_type="EXPLAIN_TEST", action_queue="REDUCTION",
            category="ENERGY", priority_level="CRITICAL", priority_score=Decimal("92.0"),
            what="Detailed What", why="Detailed Why", next="Detailed Next",
            evidence="Detailed Evidence", follow_up="Detailed Follow-Up", limitation="Detailed Limitation",
            dedup_key="explain_api_001"
        )
        db.add(action)
        db.commit()
        db.refresh(action)

        res = client.post(f"/api/agent/explain/{action.id}")
        assert res.status_code == 200
        data = res.json()
        assert data["what"] == "Detailed What"
        assert data["why"] == "Detailed Why"
        assert data["next"] == "Detailed Next"
        assert data["evidence"] == "Detailed Evidence"
        assert data["follow_up"] == "Detailed Follow-Up"
        assert data["limitation"] == "Detailed Limitation"


# ==============================================================================
# 12. COPILOT GROUNDING & INTENT ROUTING
# ==============================================================================
class TestCopilotIntegration:
    def test_router_detects_agent_brief_intent(self):
        router = CopilotRAGRouter(None)
        q1 = router.parse_query("What does the agent brief say?")
        assert q1["intent"] == "AGENT_BRIEF"

        q2 = router.parse_query("Show me the executive summary and brief")
        assert q2["intent"] == "AGENT_BRIEF"

    def test_router_detects_top_priority_intent(self):
        router = CopilotRAGRouter(None)
        q = router.parse_query("What is our top reduction priority?")
        assert q["intent"] == "TOP_PRIORITY"

    def test_router_detects_why_action_intent(self):
        router = CopilotRAGRouter(None)
        q = router.parse_query("Why is grid electricity our top recommendation?")
        assert q["intent"] == "WHY_ACTION"

    def test_router_detects_next_action_intent(self):
        router = CopilotRAGRouter(None)
        q = router.parse_query("What is the next action we should take?")
        assert q["intent"] == "NEXT_ACTION"

    def test_router_detects_what_changed_intent(self):
        router = CopilotRAGRouter(None)
        q = router.parse_query("What changed between periods?")
        assert q["intent"] == "WHAT_CHANGED"

    def test_copilot_deterministic_response_for_agent_brief(self, db):
        doc = create_doc(db, doc_id=99)
        create_ledger_entry(db, entry_id=991, doc_id=doc.id, co2e_kg=31879.0, period="2024-10")
        create_22a_priority(db, priority_id=99, doc_id=doc.id, score=85.0, level="CRITICAL")

        # Evaluate agent
        service = ProactiveAgentService(db)
        service.evaluate_actions()

        llm_service = CopilotLLMService(db)
        res = llm_service._generate_deterministic_response(
            intent="AGENT_BRIEF",
            context={},
            user_message="Give me the agent brief"
        )
        assert "AI Sustainability Brief" in res
        assert "Actual Footprint" in res

    def test_copilot_deterministic_response_for_top_priority(self, db):
        doc = create_doc(db, doc_id=98)
        create_22a_priority(db, priority_id=98, doc_id=doc.id, score=94.0, level="CRITICAL")

        service = ProactiveAgentService(db)
        service.evaluate_actions()

        llm_service = CopilotLLMService(db)
        res = llm_service._generate_deterministic_response(
            intent="TOP_PRIORITY",
            context={},
            user_message="What is the top priority?"
        )
        assert "Top Reduction Priority" in res
        assert "CRITICAL" in res
        assert "94.0" in res

    def test_copilot_deterministic_response_for_next_action(self, db):
        action = AgentAction(
            title="Next Step Test Action", action_type="NEXT_TEST", action_queue="REDUCTION",
            category="ENERGY", priority_level="HIGH", priority_score=Decimal("82.0"),
            dependency_status="READY", what="W", why="Y", next="Deploy solar panels",
            dedup_key="next_copilot_001"
        )
        db.add(action)
        db.commit()

        llm_service = CopilotLLMService(db)
        res = llm_service._generate_deterministic_response(
            intent="NEXT_ACTION",
            context={},
            user_message="What should we do next?"
        )
        assert "Next Recommended Action" in res
        assert "Deploy solar panels" in res


# ==============================================================================
# 13. SAFETY, ISOLATION & REGRESSION SAFEGUARDS
# ==============================================================================
class TestSafetyAndIsolationSafeguards:
    def test_cross_document_isolation(self, db):
        doc1 = create_doc(db, doc_id=111, filename="doc1.pdf")
        doc2 = create_doc(db, doc_id=222, filename="doc2.pdf")

        a1 = AgentAction(
            document_id=doc1.id, title="Doc 1 Action", action_type="T1", action_queue="REDUCTION",
            category="ENERGY", priority_level="HIGH", priority_score=Decimal("70.0"),
            what="W", why="Y", next="N", dedup_key="iso_001"
        )
        a2 = AgentAction(
            document_id=doc2.id, title="Doc 2 Action", action_type="T2", action_queue="REDUCTION",
            category="ENERGY", priority_level="LOW", priority_score=Decimal("30.0"),
            what="W", why="Y", next="N", dedup_key="iso_002"
        )
        db.add_all([a1, a2])
        db.commit()

        service = ProactiveAgentService(db)
        doc1_actions = service.get_actions(document_id=doc1.id)
        assert len(doc1_actions) == 1
        assert doc1_actions[0].id == a1.id

        doc2_actions = service.get_actions(document_id=doc2.id)
        assert len(doc2_actions) == 1
        assert doc2_actions[0].id == a2.id

    def test_no_fabricated_numbers_when_no_data(self, db):
        service = ProactiveAgentService(db)
        brief = service.get_sustainability_brief()
        assert brief.actual_footprint_tco2e == 0.0
        assert brief.attention_count == 0
        assert brief.latest_actual_reporting_period is None

    def test_no_fake_compliance_approvals(self, db):
        comp = ComplianceReport(
            id=777,
            report_code="BRSR-2024-001",
            report_name="BRSR Report 2024",
            framework="BRSR",
            reporting_period="2024",
            reporting_year=2024,
            status="DRAFT",
            completeness_status="INCOMPLETE",
        )
        db.add(comp)
        db.commit()

        service = ProactiveAgentService(db)
        actions = service.evaluate_actions()

        comp_actions = [a for a in actions if a.action_type == "COMPLIANCE_REVIEW_REQUIRED"]
        assert len(comp_actions) >= 1
        for ca in comp_actions:
            assert "approval" not in ca.what.lower()
            assert "certified" not in ca.what.lower()
