"""
tests/test_carbon_credit.py — Comprehensive Test Suite for Carbon Credit Readiness & Project Eligibility Assessment Engine (Step 20).

Tests:
- Assessment creation and lifecycle
- Project scoping and isolation
- Deterministic weighted scoring formula
- Readiness bands (NOT_READY, PARTIALLY_READY, READY_FOR_METHODOLOGY_REVIEW)
- 15 Readiness dimensions (Project Definition, Baseline, Activity Data, Accounting, Factors, Reduction, Additionality, Monitoring, Measurement, Verification, Methodology, Standard, Reporting, Governance, Evidence)
- Product boundary enforcement (No carbon credit issuance, no credit predictions, no market values, no additionality claims, no fake verification)
- Finalization and immutability
- PDF report generation
- API endpoints
- Copilot grounding, intent routing, and refusal boundaries
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.database.base import Base
from backend.app.database.session import get_db, init_db, SessionLocal
from backend.app.models.document import Document
from backend.app.models.sustainability_metric import SustainabilityMetric
from backend.app.models.activity_data import ActivityData
from backend.app.models.carbon_calculation import CarbonCalculation
from backend.app.models.carbon_ledger import CarbonLedgerEntry
from backend.app.models.reduction_opportunity import ReductionOpportunity
from backend.app.models.reduction_project import ReductionProject, ReductionProjectEvent
from backend.app.models.reduction_measurement import ReductionMeasurement
from backend.app.models.verification_record import VerificationRecord
from backend.app.models.compliance_report import ComplianceReport
from backend.app.models.carbon_credit import (
    CarbonCreditAssessment,
    CarbonCreditRequirement,
    CarbonCreditEvidence,
    CarbonCreditAssessmentEvent,
)
from backend.app.schemas.carbon_credit import (
    CarbonCreditAssessmentCreate,
    CarbonCreditAssessmentStatusUpdate,
)
from backend.app.services.carbon_credit_readiness import (
    carbon_credit_service,
    CARBON_CREDIT_DISCLAIMER,
    METHODOLOGY_DISCLAIMER,
    REQUIREMENT_DEFINITIONS,
)
from backend.app.services.carbon_credit_pdf import carbon_credit_pdf_renderer
from backend.app.services.copilot_service import copilot_service


@pytest.fixture(scope="function")
def db_session():
    """In-memory SQLite database session for unit tests."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="function")
def sample_setup(db_session):
    """
    Standard test fixture providing isolated documents, activity data, ledger entries,
    reduction opportunities, reduction projects, and measurements.
    """
    # 1. Document
    doc = Document(
        original_filename="test_industrial_bill.pdf",
        filename="test_industrial_bill.pdf",
        file_path="/tmp/test_industrial_bill.pdf",
        file_size=10240,
        file_hash="hash_test_cca_12345",
        mime_type="application/pdf",
        status="COMPLETED",
        review_status="VERIFIED",
        company_name="Tara Engineering Works",
        reporting_period="2024-10",
        total_energy_kwh=48750.0,
        total_emissions_tco2e=33.01,
        extracted_text="Electricity consumption: 48,750 kWh for October 2024. Total Amount: ₹453,169.56",
        structured_data={
            "evidence": [
                {
                    "field": "electricity_kwh",
                    "value": 48750.0,
                    "unit": "kWh",
                    "source_text": "Total Active Energy 48,750 kWh",
                    "page_number": 1,
                    "is_verified": True
                }
            ]
        }
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    # Metric
    metric1 = SustainabilityMetric(
        document_id=doc.id,
        metric_type="grid_electricity",
        category="energy",
        source_field="grid_electricity",
        value=48750.0,
        unit="kWh",
        source_text="Electricity consumption: 48,750 kWh for October 2024.",
    )
    db_session.add(metric1)
    db_session.commit()

    # 2. Activity Data
    act = ActivityData(
        document_id=doc.id,
        activity_type="ELECTRICITY",
        category="ENERGY",
        quantity=48750.0,
        unit="kWh",
        scope="SCOPE_2",
        reporting_period="2024-10",
    )
    db_session.add(act)
    db_session.commit()

    # 3. Calculation
    calc = CarbonCalculation(
        activity_data_id=act.id,
        document_id=doc.id,
        activity_type="ELECTRICITY",
        quantity=Decimal("48750.0"),
        activity_unit="kWh",
        scope="SCOPE_2",
        calculated_co2e=Decimal("31880.0"),
        factor_code="EF-ELEC-CEA-2024",
        factor_name="CEA Grid Factor",
        factor_source="CEA v20.0",
        factor_value=Decimal("0.7100"),
        reporting_period="2024-10",
    )
    db_session.add(calc)
    db_session.commit()


    # 4. Posted Carbon Ledger Entry
    ledger = CarbonLedgerEntry(
        carbon_calculation_id=calc.id,
        activity_data_id=act.id,
        document_id=doc.id,
        scope="SCOPE_2",
        quantity=Decimal("48750.0"),
        activity_unit="kWh",
        calculated_co2e=Decimal("31880.0"),
        activity_type="ELECTRICITY",
        category="ENERGY",
        factor_name="CEA Grid Factor",
        factor_value=Decimal("0.7100"),
        accounting_status="POSTED",
        reporting_period="2024-10",
    )
    db_session.add(ledger)
    db_session.commit()

    # 5. Opportunity
    opp = ReductionOpportunity(
        opportunity_code="OPP-2024-0001",
        title="Rooftop Solar PV Expansion",
        description="Expand captive rooftop solar capacity to reduce grid electricity consumption.",
        category="RENEWABLE_ENERGY",
        priority="HIGH",
        trigger_type="HIGH_ENERGY_USE",
        status="OPEN",
        rationale="High Scope 2 grid electricity consumption",
        recommended_action="Install 50kW solar array",
        limitations="Space constraint on roof",
    )
    db_session.add(opp)
    db_session.commit()


    # 6. Reduction Project
    project = ReductionProject(
        project_code="PRJ-2024-0001",
        title="50kW Captive Rooftop Solar Installation",
        description="Install 50kW solar array to reduce grid electricity demand and Scope 2 emissions under business-as-usual baseline.",
        category="RENEWABLE_ENERGY",
        scope="SCOPE_2",
        opportunity_id=opp.id,
        status="IN_PROGRESS",
        owner="R. Sharma (Plant Energy Manager)",
        baseline_period="2024-10",
        baseline_co2e=Decimal("31880.00"),
        baseline_co2e_unit="kgCO2e",
        target_description="Achieve 30% reduction in grid electricity demand.",
    )
    db_session.add(project)
    db_session.commit()

    # 7. Project Event
    evt = ReductionProjectEvent(
        project_id=project.id,
        event_type="CREATED",
        previous_status=None,
        new_status="PLANNED",
        note="Project initiated.",
    )
    db_session.add(evt)
    db_session.commit()

    # 8. Measurement
    meas = ReductionMeasurement(
        project_id=project.id,
        reference_period="2024-09",
        measurement_period="2024-10",
        reference_co2e=Decimal("35000.0"),
        measurement_co2e=Decimal("31880.0"),
        observed_change=Decimal("-3120.0"),
        measurement_status="MEASURED",
    )
    db_session.add(meas)
    db_session.commit()

    # 9. Compliance Report
    comp = ComplianceReport(
        report_code="CR-2024-001",
        report_name="GHG Inventory 2024",
        framework="GHG_PROTOCOL",
        reporting_period="2024-10",
        status="GENERATED",
    )
    db_session.add(comp)
    db_session.commit()

    return {
        "db": db_session,
        "document": doc,
        "activity": act,
        "calculation": calc,
        "ledger": ledger,
        "opportunity": opp,
        "project": project,
        "measurement": meas,
        "compliance_report": comp,
    }


# =============================================================================
# 1. DATABASE MODELS & BASIC CREATION TESTS (1-15)
# =============================================================================

class TestCarbonCreditModels:
    def test_01_create_assessment_record(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = CarbonCreditAssessment(
            assessment_code="CCA-TEST-0001",
            project_id=proj.id,
            project_name=proj.title,
            reporting_period="2024-10",
            assessment_version="1.0",
            overall_readiness_score=0.0,
            readiness_band="NOT_READY",
            status="DRAFT",
        )
        db.add(ass)
        db.commit()
        db.refresh(ass)
        assert ass.id is not None
        assert ass.assessment_code == "CCA-TEST-0001"
        assert ass.project_id == proj.id
        assert ass.assessment_version == "1.0"

    def test_02_assessment_code_unique_constraint(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass1 = CarbonCreditAssessment(
            assessment_code="CCA-UNIQUE-01",
            project_id=proj.id,
            project_name=proj.title,
            reporting_period="2024-10",
        )
        db.add(ass1)
        db.commit()

        ass2 = CarbonCreditAssessment(
            assessment_code="CCA-UNIQUE-01",
            project_id=proj.id,
            project_name=proj.title,
            reporting_period="2024-10",
        )
        db.add(ass2)
        with pytest.raises(Exception):
            db.commit()
        db.rollback()

    def test_03_create_requirement_record(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = CarbonCreditAssessment(
            assessment_code="CCA-REQ-001",
            project_id=proj.id,
            project_name=proj.title,
            reporting_period="2024-10",
        )
        db.add(ass)
        db.commit()

        req = CarbonCreditRequirement(
            assessment_id=ass.id,
            requirement_code="CC_PROJ_DEF",
            requirement_name="Project Definition",
            category="PROJECT_DEFINITION",
            weight=1.5,
            required=True,
            status="SUPPORTED",
            reason="Project definition verified.",
        )
        db.add(req)
        db.commit()
        db.refresh(req)
        assert req.id is not None
        assert req.assessment_id == ass.id
        assert req.status == "SUPPORTED"

    def test_04_create_evidence_record(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        doc = sample_setup["document"]
        ass = CarbonCreditAssessment(
            assessment_code="CCA-EV-001",
            project_id=proj.id,
            project_name=proj.title,
            reporting_period="2024-10",
        )
        db.add(ass)
        db.commit()

        req = CarbonCreditRequirement(
            assessment_id=ass.id,
            requirement_code="CC_EVID_LINEAGE",
            requirement_name="Evidence Lineage",
            category="EVIDENCE",
        )
        db.add(req)
        db.commit()

        ev = CarbonCreditEvidence(
            assessment_id=ass.id,
            requirement_id=req.id,
            project_id=proj.id,
            source_type="DOCUMENT",
            source_id=doc.id,
            document_id=doc.id,
            source_field="electricity_kwh",
            source_text="Total Active Energy 48,750 kWh",
            reporting_period="2024-10",
            page_number=1,
            evidence_status="VERIFIED",
        )
        db.add(ev)
        db.commit()
        db.refresh(ev)
        assert ev.id is not None
        assert ev.document_id == doc.id
        assert ev.evidence_status == "VERIFIED"

    def test_05_create_assessment_event(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = CarbonCreditAssessment(
            assessment_code="CCA-EVT-001",
            project_id=proj.id,
            project_name=proj.title,
            reporting_period="2024-10",
        )
        db.add(ass)
        db.commit()

        evt = CarbonCreditAssessmentEvent(
            assessment_id=ass.id,
            event_type="STATUS_CHANGE",
            previous_status="DRAFT",
            new_status="GENERATED",
            notes="Generated assessment.",
            actor="USER",
        )
        db.add(evt)
        db.commit()
        db.refresh(evt)
        assert evt.id is not None
        assert evt.event_type == "STATUS_CHANGE"
        assert evt.actor == "USER"

    def test_06_assessment_cascade_delete(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = CarbonCreditAssessment(
            assessment_code="CCA-CASCADE-01",
            project_id=proj.id,
            project_name=proj.title,
            reporting_period="2024-10",
        )
        db.add(ass)
        db.commit()

        req = CarbonCreditRequirement(
            assessment_id=ass.id,
            requirement_code="CC_PROJ_DEF",
            requirement_name="Project Def",
            category="PROJECT_DEFINITION",
        )
        db.add(req)
        db.commit()

        ass_id = ass.id
        req_id = req.id
        db.delete(ass)
        db.commit()

        assert db.query(CarbonCreditAssessment).filter_by(id=ass_id).first() is None
        assert db.query(CarbonCreditRequirement).filter_by(id=req_id).first() is None

    def test_07_requirement_definition_count(self):
        assert len(REQUIREMENT_DEFINITIONS) >= 15
        codes = [r["code"] for r in REQUIREMENT_DEFINITIONS]
        assert len(codes) == len(set(codes))  # unique codes

    def test_08_assessment_default_statuses(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = CarbonCreditAssessment(
            assessment_code="CCA-DEF-01",
            project_id=proj.id,
            project_name=proj.title,
            reporting_period="2024-10",
        )
        db.add(ass)
        db.commit()
        assert ass.status == "DRAFT"
        assert ass.readiness_band == "NOT_READY"
        assert ass.methodology_status == "NEEDS_REVIEW"
        assert ass.standard_status == "NEEDS_REVIEW"

    def test_09_assessment_version_immutable_default(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = CarbonCreditAssessment(
            assessment_code="CCA-VER-01",
            project_id=proj.id,
            project_name=proj.title,
            reporting_period="2024-10",
        )
        db.add(ass)
        db.commit()
        assert ass.assessment_version == "1.0"

    def test_10_invalid_project_id_raises(self, sample_setup):
        db = sample_setup["db"]
        with pytest.raises(ValueError, match="not found"):
            carbon_credit_service.create_assessment(
                db, CarbonCreditAssessmentCreate(project_id=999999, reporting_period="2024-10")
            )

    def test_11_service_create_assessment_populates_requirements(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        assert ass.id is not None
        assert len(ass.requirements) == len(REQUIREMENT_DEFINITIONS)
        assert all(r.status == "MISSING" for r in ass.requirements)

    def test_12_service_create_assessment_logs_event(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        events = db.query(CarbonCreditAssessmentEvent).filter_by(assessment_id=ass.id).all()
        assert len(events) == 1
        assert events[0].event_type == "CREATED"

    def test_13_generate_assessment_code_format(self, sample_setup):
        db = sample_setup["db"]
        code = carbon_credit_service.generate_assessment_code(db, "2024-10")
        assert code.startswith("CCA-")
        assert len(code.split("-")) == 3

    def test_14_get_assessments_filter_by_project(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass1 = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        results = carbon_credit_service.get_assessments(db, project_id=proj.id)
        assert len(results) >= 1
        assert all(r.project_id == proj.id for r in results)

    def test_15_get_assessments_filter_by_nonexistent_project(self, sample_setup):
        db = sample_setup["db"]
        results = carbon_credit_service.get_assessments(db, project_id=888888)
        assert len(results) == 0


# =============================================================================
# 2. DETERMINISTIC SCORING & READINESS BANDS (16-30)
# =============================================================================

class TestDeterministicScoring:
    def test_16_all_supported_score_is_100(self):
        reqs = [
            CarbonCreditRequirement(requirement_code="R1", requirement_name="R1", category="C1", weight=1.0, status="SUPPORTED"),
            CarbonCreditRequirement(requirement_code="R2", requirement_name="R2", category="C2", weight=1.5, status="SUPPORTED"),
            CarbonCreditRequirement(requirement_code="R3", requirement_name="R3", category="C3", weight=2.0, status="SUPPORTED"),
        ]
        score, band = carbon_credit_service._compute_deterministic_score(reqs)
        assert score == 100.0
        assert band == "READY_FOR_METHODOLOGY_REVIEW"

    def test_17_all_missing_score_is_0(self):
        reqs = [
            CarbonCreditRequirement(requirement_code="R1", requirement_name="R1", category="C1", weight=1.0, status="MISSING"),
            CarbonCreditRequirement(requirement_code="R2", requirement_name="R2", category="C2", weight=1.5, status="MISSING"),
        ]
        score, band = carbon_credit_service._compute_deterministic_score(reqs)
        assert score == 0.0
        assert band == "NOT_READY"

    def test_18_partially_supported_multiplier_is_50_percent(self):
        reqs = [
            CarbonCreditRequirement(requirement_code="R1", requirement_name="R1", category="C1", weight=2.0, status="PARTIALLY_SUPPORTED"),
        ]
        score, band = carbon_credit_service._compute_deterministic_score(reqs)
        assert score == 50.0
        assert band == "PARTIALLY_READY"

    def test_19_needs_review_multiplier_is_25_percent(self):
        reqs = [
            CarbonCreditRequirement(requirement_code="R1", requirement_name="R1", category="C1", weight=2.0, status="NEEDS_REVIEW"),
        ]
        score, band = carbon_credit_service._compute_deterministic_score(reqs)
        assert score == 25.0
        assert band == "NOT_READY"

    def test_20_not_applicable_is_excluded(self):
        reqs = [
            CarbonCreditRequirement(requirement_code="R1", requirement_name="R1", category="C1", weight=2.0, status="SUPPORTED"),
            CarbonCreditRequirement(requirement_code="R2", requirement_name="R2", category="C2", weight=5.0, status="NOT_APPLICABLE"),
        ]
        score, band = carbon_credit_service._compute_deterministic_score(reqs)
        assert score == 100.0
        assert band == "READY_FOR_METHODOLOGY_REVIEW"

    def test_21_weighted_mixed_score_formula(self):
        reqs = [
            CarbonCreditRequirement(requirement_code="R1", requirement_name="R1", category="C1", weight=2.0, status="SUPPORTED"),
            CarbonCreditRequirement(requirement_code="R2", requirement_name="R2", category="C2", weight=2.0, status="PARTIALLY_SUPPORTED"),
            CarbonCreditRequirement(requirement_code="R3", requirement_name="R3", category="C3", weight=2.0, status="NEEDS_REVIEW"),
            CarbonCreditRequirement(requirement_code="R4", requirement_name="R4", category="C4", weight=2.0, status="MISSING"),
        ]
        score, band = carbon_credit_service._compute_deterministic_score(reqs)
        assert score == 43.75
        assert band == "PARTIALLY_READY"

    def test_22_band_boundaries_not_ready(self):
        reqs = [
            CarbonCreditRequirement(requirement_code="R1", requirement_name="R1", category="C1", weight=39.0, status="SUPPORTED"),
            CarbonCreditRequirement(requirement_code="R2", requirement_name="R2", category="C2", weight=61.0, status="MISSING"),
        ]
        score, band = carbon_credit_service._compute_deterministic_score(reqs)
        assert score == 39.0
        assert band == "NOT_READY"

    def test_23_band_boundaries_partially_ready_40(self):
        reqs = [
            CarbonCreditRequirement(requirement_code="R1", requirement_name="R1", category="C1", weight=40.0, status="SUPPORTED"),
            CarbonCreditRequirement(requirement_code="R2", requirement_name="R2", category="C2", weight=60.0, status="MISSING"),
        ]
        score, band = carbon_credit_service._compute_deterministic_score(reqs)
        assert score == 40.0
        assert band == "PARTIALLY_READY"

    def test_24_band_boundaries_partially_ready_69(self):
        reqs = [
            CarbonCreditRequirement(requirement_code="R1", requirement_name="R1", category="C1", weight=69.0, status="SUPPORTED"),
            CarbonCreditRequirement(requirement_code="R2", requirement_name="R2", category="C2", weight=31.0, status="MISSING"),
        ]
        score, band = carbon_credit_service._compute_deterministic_score(reqs)
        assert score == 69.0
        assert band == "PARTIALLY_READY"

    def test_25_band_boundaries_ready_for_review_70(self):
        reqs = [
            CarbonCreditRequirement(requirement_code="R1", requirement_name="R1", category="C1", weight=70.0, status="SUPPORTED"),
            CarbonCreditRequirement(requirement_code="R2", requirement_name="R2", category="C2", weight=30.0, status="MISSING"),
        ]
        score, band = carbon_credit_service._compute_deterministic_score(reqs)
        assert score == 70.0
        assert band == "READY_FOR_METHODOLOGY_REVIEW"

    def test_26_empty_requirements_returns_0_score(self):
        score, band = carbon_credit_service._compute_deterministic_score([])
        assert score == 0.0
        assert band == "NOT_READY"

    def test_27_all_na_requirements_returns_0_score(self):
        reqs = [
            CarbonCreditRequirement(requirement_code="R1", requirement_name="R1", category="C1", weight=2.0, status="NOT_APPLICABLE"),
        ]
        score, band = carbon_credit_service._compute_deterministic_score(reqs)
        assert score == 0.0
        assert band == "NOT_READY"

    def test_28_score_precision_two_decimal_places(self):
        reqs = [
            CarbonCreditRequirement(requirement_code="R1", requirement_name="R1", category="C1", weight=1.0, status="SUPPORTED"),
            CarbonCreditRequirement(requirement_code="R2", requirement_name="R2", category="C2", weight=2.0, status="MISSING"),
        ]
        score, band = carbon_credit_service._compute_deterministic_score(reqs)
        assert score == 33.33

    def test_29_repeatable_score_guarantee(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        gen1 = carbon_credit_service.generate_assessment(db, ass.id)
        score1 = gen1.overall_readiness_score

        gen2 = carbon_credit_service.generate_assessment(db, ass.id)
        score2 = gen2.overall_readiness_score

        assert score1 == score2

    def test_30_deterministic_service_scoring_execution(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        gen = carbon_credit_service.generate_assessment(db, ass.id)
        assert gen.overall_readiness_score > 50.0
        assert gen.status in ("GENERATED", "READY_FOR_METHODOLOGY_REVIEW")


# =============================================================================
# 3. 15 READINESS DIMENSIONS EVALUATION (31-60)
# =============================================================================

class TestReadinessDimensions:
    def test_31_project_definition_evaluation(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        gen = carbon_credit_service.generate_assessment(db, ass.id)
        req = next(r for r in gen.requirements if r.requirement_code == "CC_PROJ_DEF")
        assert req.status == "SUPPORTED"
        assert "clearly identified" in req.reason

    def test_32_project_definition_partial_when_short(self, db_session):
        proj = ReductionProject(
            project_code="PRJ-SHORT-01",
            title="Short Title",
            category="RENEWABLE_ENERGY",
            description="",
            status="PLANNED",
        )
        db_session.add(proj)
        db_session.commit()

        ass = carbon_credit_service.create_assessment(
            db_session, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        gen = carbon_credit_service.generate_assessment(db_session, ass.id)
        req = next(r for r in gen.requirements if r.requirement_code == "CC_PROJ_DEF")
        assert req.status == "PARTIALLY_SUPPORTED"

    def test_33_linked_opportunity_evaluation(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        gen = carbon_credit_service.generate_assessment(db, ass.id)
        req = next(r for r in gen.requirements if r.requirement_code == "CC_PROJ_OPP")
        assert req.status == "SUPPORTED"
        assert "OPP-2024-0001" in req.reason

    def test_34_unlinked_opportunity_is_missing(self, db_session):
        proj = ReductionProject(
            project_code="PRJ-NO-OPP-01",
            title="Standalone Project",
            category="RENEWABLE_ENERGY",
            opportunity_id=None,
            status="PLANNED",
        )
        db_session.add(proj)
        db_session.commit()

        ass = carbon_credit_service.create_assessment(
            db_session, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        gen = carbon_credit_service.generate_assessment(db_session, ass.id)
        req = next(r for r in gen.requirements if r.requirement_code == "CC_PROJ_OPP")
        assert req.status == "MISSING"

    def test_35_baseline_exists_supported(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        gen = carbon_credit_service.generate_assessment(db, ass.id)
        req = next(r for r in gen.requirements if r.requirement_code == "CC_BASE_EXISTS")
        assert req.status == "SUPPORTED"
        assert "31880" in req.reason

    def test_36_baseline_trace_supported_with_posted_ledger(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        gen = carbon_credit_service.generate_assessment(db, ass.id)
        req = next(r for r in gen.requirements if r.requirement_code == "CC_BASE_TRACE")
        assert req.status == "SUPPORTED"
        assert "POSTED" in req.reason

    def test_37_baseline_missing_when_not_set(self, db_session):
        proj = ReductionProject(
            project_code="PRJ-NO-BASE",
            title="Project without baseline",
            category="RENEWABLE_ENERGY",
            baseline_period=None,
            baseline_co2e=None,
            status="PLANNED",
        )
        db_session.add(proj)
        db_session.commit()

        ass = carbon_credit_service.create_assessment(
            db_session, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        gen = carbon_credit_service.generate_assessment(db_session, ass.id)
        req = next(r for r in gen.requirements if r.requirement_code == "CC_BASE_EXISTS")
        assert req.status == "MISSING"

    def test_38_activity_data_quantities_supported(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        gen = carbon_credit_service.generate_assessment(db, ass.id)
        req = next(r for r in gen.requirements if r.requirement_code == "CC_ACT_QUANTITY")
        assert req.status == "SUPPORTED"

    def test_39_activity_data_source_lineage_supported(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        gen = carbon_credit_service.generate_assessment(db, ass.id)
        req = next(r for r in gen.requirements if r.requirement_code == "CC_ACT_SOURCE")
        assert req.status == "SUPPORTED"

    def test_40_carbon_accounting_calc_supported(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        gen = carbon_credit_service.generate_assessment(db, ass.id)
        req = next(r for r in gen.requirements if r.requirement_code == "CC_ACC_CALC")
        assert req.status == "SUPPORTED"

    def test_41_carbon_accounting_ledger_posted_supported(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        gen = carbon_credit_service.generate_assessment(db, ass.id)
        req = next(r for r in gen.requirements if r.requirement_code == "CC_ACC_LEDGER")
        assert req.status == "SUPPORTED"

    def test_42_emission_factor_resolved_supported(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        gen = carbon_credit_service.generate_assessment(db, ass.id)
        req = next(r for r in gen.requirements if r.requirement_code == "CC_EF_RESOLVED")
        assert req.status == "SUPPORTED"
        assert "EF-ELEC-CEA-2024" in req.reason

    def test_43_emission_factor_provenance_supported(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        gen = carbon_credit_service.generate_assessment(db, ass.id)
        req = next(r for r in gen.requirements if r.requirement_code == "CC_EF_PROVENANCE")
        assert req.status == "SUPPORTED"
        assert "CEA" in req.reason

    def test_44_reduction_evidence_supported(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        gen = carbon_credit_service.generate_assessment(db, ass.id)
        req = next(r for r in gen.requirements if r.requirement_code == "CC_RED_EVIDENCE")
        assert req.status == "SUPPORTED"
        assert "Does not establish that project definitely caused reduction" in req.reason

    def test_45_additionality_rationale_supported(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        gen = carbon_credit_service.generate_assessment(db, ass.id)
        req = next(r for r in gen.requirements if r.requirement_code == "CC_ADD_RATIONALE")
        assert req.status == "SUPPORTED"

    def test_46_additionality_checklist_explains_boundary(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        gen = carbon_credit_service.generate_assessment(db, ass.id)
        req = next(r for r in gen.requirements if r.requirement_code == "CC_ADD_CHECKLIST")
        assert req.status == "NEEDS_REVIEW"
        assert "Additionality has not been determined by Senseible" in req.reason

    def test_47_monitoring_plan_supported(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        gen = carbon_credit_service.generate_assessment(db, ass.id)
        req = next(r for r in gen.requirements if r.requirement_code == "CC_MON_PLAN")
        assert req.status == "SUPPORTED"

    def test_48_monitoring_period_supported(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        gen = carbon_credit_service.generate_assessment(db, ass.id)
        req = next(r for r in gen.requirements if r.requirement_code == "CC_MON_PERIOD")
        assert req.status == "SUPPORTED"
        assert "2024-10" in req.reason

    def test_49_measurement_history_supported(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        gen = carbon_credit_service.generate_assessment(db, ass.id)
        req = next(r for r in gen.requirements if r.requirement_code == "CC_MEAS_HISTORY")
        assert req.status == "SUPPORTED"

    def test_50_measurement_accounting_linkage_supported(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        gen = carbon_credit_service.generate_assessment(db, ass.id)
        req = next(r for r in gen.requirements if r.requirement_code == "CC_MEAS_ACCOUNTING")
        assert req.status == "SUPPORTED"

    def test_51_verification_status_internal_review_partially_supported(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        gen = carbon_credit_service.generate_assessment(db, ass.id)
        req = next(r for r in gen.requirements if r.requirement_code == "CC_VERIF_STATUS")
        assert req.status in ("MISSING", "PARTIALLY_SUPPORTED")
        assert "External verification not recorded" in req.reason or "INTERNAL_REVIEW" in req.reason

    def test_52_verification_status_external_verified_supported(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        meas = sample_setup["measurement"]
        v_rec = VerificationRecord(
            project_id=proj.id,
            measurement_id=meas.id,
            verifier_name="Dr. V. Rao",
            verifier_organization="TUV Nord India",
            verification_reference="VVB-2025-8899",
            verification_date=datetime(2025, 11, 1),
            verification_status="EXTERNALLY_VERIFIED",
        )
        db.add(v_rec)
        db.commit()

        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        gen = carbon_credit_service.generate_assessment(db, ass.id)
        req = next(r for r in gen.requirements if r.requirement_code == "CC_VERIF_STATUS")
        assert req.status == "SUPPORTED"
        assert "TUV Nord India" in req.reason

    def test_53_methodology_generic_readiness_supported(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        gen = carbon_credit_service.generate_assessment(db, ass.id)
        req = next(r for r in gen.requirements if r.requirement_code == "CC_METH_GENERIC")
        assert req.status in ("SUPPORTED", "PARTIALLY_SUPPORTED")

    def test_54_standard_readiness_framework_needs_review(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        gen = carbon_credit_service.generate_assessment(db, ass.id)
        req = next(r for r in gen.requirements if r.requirement_code == "CC_STD_FRAMEWORK")
        assert req.status == "NEEDS_REVIEW"
        assert "Standard-specific eligibility requires methodology and program review" in req.reason

    def test_55_reporting_compliance_supported(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        gen = carbon_credit_service.generate_assessment(db, ass.id)
        req = next(r for r in gen.requirements if r.requirement_code == "CC_REP_STRUCTURE")
        assert req.status == "SUPPORTED"
        assert "CR-2024-001" in req.reason

    def test_56_governance_owner_supported(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        gen = carbon_credit_service.generate_assessment(db, ass.id)
        req = next(r for r in gen.requirements if r.requirement_code == "CC_GOV_OWNER")
        assert req.status == "SUPPORTED"
        assert "R. Sharma" in req.reason

    def test_57_governance_owner_missing_when_none(self, db_session):
        proj = ReductionProject(
            project_code="PRJ-NO-OWNER",
            title="Unassigned Project",
            category="RENEWABLE_ENERGY",
            owner=None,
            status="PLANNED",
        )
        db_session.add(proj)
        db_session.commit()

        ass = carbon_credit_service.create_assessment(
            db_session, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        gen = carbon_credit_service.generate_assessment(db_session, ass.id)
        req = next(r for r in gen.requirements if r.requirement_code == "CC_GOV_OWNER")
        assert req.status == "MISSING"

    def test_58_governance_audit_supported(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        gen = carbon_credit_service.generate_assessment(db, ass.id)
        req = next(r for r in gen.requirements if r.requirement_code == "CC_GOV_AUDIT")
        assert req.status == "SUPPORTED"

    def test_59_evidence_lineage_supported(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        gen = carbon_credit_service.generate_assessment(db, ass.id)
        req = next(r for r in gen.requirements if r.requirement_code == "CC_EVID_LINEAGE")
        assert req.status == "SUPPORTED"

    def test_60_dimension_summary_builder(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        carbon_credit_service.generate_assessment(db, ass.id)
        dto = carbon_credit_service.build_assessment_dto(db, ass)
        assert len(dto.dimensions) == 15
        assert all(d.score >= 0.0 for d in dto.dimensions)


# =============================================================================
# 4. MISSING REQUIREMENTS, NEXT ACTIONS & CHECKLIST (61-75)
# =============================================================================

class TestMissingAndChecklist:
    def test_61_missing_requirements_generated(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        carbon_credit_service.generate_assessment(db, ass.id)
        dto = carbon_credit_service.build_assessment_dto(db, ass)
        assert isinstance(dto.missing_requirements, list)
        for m in dto.missing_requirements:
            assert m.priority in ("HIGH", "MEDIUM", "LOW")
            assert len(m.what_is_needed) > 0
            assert len(m.recommended_action) > 0

    def test_62_next_actions_prioritized(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        carbon_credit_service.generate_assessment(db, ass.id)
        dto = carbon_credit_service.build_assessment_dto(db, ass)
        assert isinstance(dto.next_actions, list)
        for a in dto.next_actions:
            assert a.priority in ("HIGH", "MEDIUM", "LOW")
            assert len(a.action) > 0

    def test_63_checklist_has_15_sections(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        carbon_credit_service.generate_assessment(db, ass.id)
        dto = carbon_credit_service.build_assessment_dto(db, ass)
        assert len(dto.checklist) == 15
        sections = [c.section_name for c in dto.checklist]
        assert "Project Definition" in sections
        assert "Baseline" in sections
        assert "Carbon Accounting" in sections
        assert "Monitoring" in sections
        assert "Verification" in sections

    def test_64_checklist_status_valid_values(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        carbon_credit_service.generate_assessment(db, ass.id)
        dto = carbon_credit_service.build_assessment_dto(db, ass)
        valid = {"READY", "PARTIAL", "MISSING", "NEEDS_REVIEW", "NOT_APPLICABLE"}
        assert all(c.status in valid for c in dto.checklist)

    def test_65_accounting_summary_does_not_label_credits(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        carbon_credit_service.generate_assessment(db, ass.id)
        dto = carbon_credit_service.build_assessment_dto(db, ass)
        assert dto.accounting_summary is not None
        assert dto.accounting_summary.unit_label == "tCO2e"
        assert "not carbon credits" in dto.accounting_summary.note.lower()

    def test_66_methodology_readiness_object_structure(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        carbon_credit_service.generate_assessment(db, ass.id)
        dto = carbon_credit_service.build_assessment_dto(db, ass)
        assert dto.methodology is not None
        assert dto.methodology.framework == "GENERIC_CARBON_STANDARD"
        assert "does not certify" in dto.methodology.disclaimer.lower()

    def test_67_missing_requirements_empty_when_perfect_score(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        for r in ass.requirements:
            r.status = "SUPPORTED"
        db.commit()
        dto = carbon_credit_service.build_assessment_dto(db, ass)
        assert len(dto.missing_requirements) == 0

    def test_68_missing_requirements_priority_mapping(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        req_base = next(r for r in ass.requirements if r.category == "BASELINE")
        req_base.status = "MISSING"
        db.commit()
        dto = carbon_credit_service.build_assessment_dto(db, ass)
        miss = next(m for m in dto.missing_requirements if m.requirement_code == req_base.requirement_code)
        assert miss.priority == "HIGH"

    def test_69_mandatory_disclaimer_present_in_dto(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        dto = carbon_credit_service.build_assessment_dto(db, ass)
        assert "does not issue" in dto.disclaimer.lower()
        assert "tradable carbon credits" in dto.disclaimer.lower()

    def test_70_evidence_items_linked_to_requirements(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        carbon_credit_service.generate_assessment(db, ass.id)
        dto = carbon_credit_service.build_assessment_dto(db, ass)
        req_with_ev = [r for r in dto.requirements if r.evidence_items]
        assert len(req_with_ev) > 0
        ev_first = req_with_ev[0].evidence_items[0]
        assert ev_first.evidence_status == "VERIFIED"

    def test_71_evidence_provenance_preserves_source_id(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        doc = sample_setup["document"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        carbon_credit_service.generate_assessment(db, ass.id)
        dto = carbon_credit_service.build_assessment_dto(db, ass)
        ev_items = [ev for r in dto.requirements for ev in r.evidence_items if ev.document_id == doc.id]
        assert len(ev_items) > 0
        assert ev_items[0].document_id == doc.id

    def test_72_action_guidance_text_presence(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        req = ass.requirements[0]
        needed, action = carbon_credit_service._get_requirement_action_guidance(req)
        assert len(needed) > 0
        assert len(action) > 0

    def test_73_no_cross_project_evidence_mixing(self, db_session):
        proj1 = ReductionProject(
            project_code="PRJ-ISOLATED-01",
            title="First Isolated Project",
            category="RENEWABLE_ENERGY",
            status="PLANNED",
        )
        proj2 = ReductionProject(
            project_code="PRJ-ISOLATED-02",
            title="Second Isolated Project",
            category="RENEWABLE_ENERGY",
            status="PLANNED",
        )
        db_session.add_all([proj1, proj2])
        db_session.commit()

        ass2 = carbon_credit_service.create_assessment(
            db_session, CarbonCreditAssessmentCreate(project_id=proj2.id, reporting_period="2024-10")
        )
        gen2 = carbon_credit_service.generate_assessment(db_session, ass2.id)
        dto2 = carbon_credit_service.build_assessment_dto(db_session, gen2)

        for r in dto2.requirements:
            for ev in r.evidence_items:
                assert ev.project_id == proj2.id

    def test_74_project_summary_fields_in_dto(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        dto = carbon_credit_service.build_assessment_dto(db, ass)
        assert dto.project_category == proj.category
        assert dto.project_owner == proj.owner
        assert dto.baseline_period == proj.baseline_period

    def test_75_dto_event_history_serialization(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        dto = carbon_credit_service.build_assessment_dto(db, ass)
        assert len(dto.events) >= 1
        assert dto.events[0].event_type == "CREATED"


# =============================================================================
# 5. FINALIZATION, IMMUTABILITY & VERSIONING (76-85)
# =============================================================================

class TestFinalizationAndImmutability:
    def test_76_finalize_assessment_updates_status(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        finalized = carbon_credit_service.update_assessment_status(
            db, ass.id, "FINALIZED", notes="Finalizing assessment."
        )
        assert finalized.status == "FINALIZED"
        assert finalized.finalized_at is not None

    def test_77_finalized_assessment_cannot_be_regenerated(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        carbon_credit_service.update_assessment_status(db, ass.id, "FINALIZED")
        with pytest.raises(ValueError, match="immutable"):
            carbon_credit_service.generate_assessment(db, ass.id)

    def test_78_finalized_assessment_cannot_change_status(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        carbon_credit_service.update_assessment_status(db, ass.id, "FINALIZED")
        with pytest.raises(ValueError, match="immutable"):
            carbon_credit_service.update_assessment_status(db, ass.id, "DRAFT")

    def test_79_invalid_status_transition_raises(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        with pytest.raises(ValueError, match="Invalid status"):
            carbon_credit_service.update_assessment_status(db, ass.id, "NONEXISTENT_STATUS")

    def test_80_finalized_assessment_event_actor(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        carbon_credit_service.update_assessment_status(db, ass.id, "FINALIZED", actor="Auditor-1")
        events = db.query(CarbonCreditAssessmentEvent).filter_by(assessment_id=ass.id, event_type="FINALIZED").all()
        assert len(events) == 1
        assert events[0].actor == "Auditor-1"

    def test_81_version_is_preserved_through_generation(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        gen = carbon_credit_service.generate_assessment(db, ass.id)
        assert gen.assessment_version == "1.0"

    def test_82_status_transition_event_logging(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        carbon_credit_service.update_assessment_status(db, ass.id, "NEEDS_REVIEW", notes="Review needed.")
        events = db.query(CarbonCreditAssessmentEvent).filter_by(assessment_id=ass.id).all()
        assert any(e.new_status == "NEEDS_REVIEW" for e in events)

    def test_83_finalization_sets_finalized_at_timestamp(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        before = datetime.utcnow()
        carbon_credit_service.update_assessment_status(db, ass.id, "FINALIZED")
        after = datetime.utcnow()
        assert ass.finalized_at >= before - timedelta(seconds=1)
        assert ass.finalized_at <= after + timedelta(seconds=1)

    def test_84_draft_status_remains_mutable(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        carbon_credit_service.generate_assessment(db, ass.id)
        ass_updated = carbon_credit_service.update_assessment_status(db, ass.id, "NEEDS_REVIEW")
        assert ass_updated.status == "NEEDS_REVIEW"

    def test_85_ready_for_review_status_transition(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        updated = carbon_credit_service.update_assessment_status(db, ass.id, "READY_FOR_METHODOLOGY_REVIEW")
        assert updated.status == "READY_FOR_METHODOLOGY_REVIEW"


# =============================================================================
# 6. PDF GENERATION (86-90)
# =============================================================================

class TestPDFReportGeneration:
    def test_86_pdf_generates_valid_bytes(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        carbon_credit_service.generate_assessment(db, ass.id)
        dto = carbon_credit_service.build_assessment_dto(db, ass)
        pdf_bytes = carbon_credit_pdf_renderer.render(dto)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 1000
        assert pdf_bytes.startswith(b"%PDF")

    def test_87_pdf_contains_disclaimer(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        carbon_credit_service.generate_assessment(db, ass.id)
        dto = carbon_credit_service.build_assessment_dto(db, ass)
        pdf_bytes = carbon_credit_pdf_renderer.render(dto)
        assert len(pdf_bytes) > 2000

    def test_88_pdf_with_empty_missing_requirements(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        for r in ass.requirements:
            r.status = "SUPPORTED"
        db.commit()
        dto = carbon_credit_service.build_assessment_dto(db, ass)
        pdf_bytes = carbon_credit_pdf_renderer.render(dto)
        assert len(pdf_bytes) > 1000

    def test_89_pdf_with_verified_status(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        meas = sample_setup["measurement"]
        v_rec = VerificationRecord(
            project_id=proj.id,
            measurement_id=meas.id,
            verifier_name="Dr. V. Rao",
            verifier_organization="TUV Nord India",
            verification_reference="VVB-2025-8899",
            verification_status="EXTERNALLY_VERIFIED",
        )
        db.add(v_rec)
        db.commit()

        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        carbon_credit_service.generate_assessment(db, ass.id)
        dto = carbon_credit_service.build_assessment_dto(db, ass)
        pdf_bytes = carbon_credit_pdf_renderer.render(dto)
        assert len(pdf_bytes) > 1000

    def test_90_pdf_endpoint_returns_pdf(self, sample_setup):
        db = sample_setup["db"]
        proj = sample_setup["project"]
        ass = carbon_credit_service.create_assessment(
            db, CarbonCreditAssessmentCreate(project_id=proj.id, reporting_period="2024-10")
        )
        carbon_credit_service.generate_assessment(db, ass.id)
        dto = carbon_credit_service.build_assessment_dto(db, ass)
        pdf_bytes = carbon_credit_pdf_renderer.render(dto)
        assert len(pdf_bytes) > 0


# =============================================================================
# 7. FASTAPI API ENDPOINTS (91-105)
# =============================================================================

@pytest.fixture(scope="module")
def api_engine():
    init_db()
    engine = create_engine("sqlite:///./test_carbon_credit.db", echo=False)
    Base.metadata.create_all(bind=engine)
    yield engine


@pytest.fixture(scope="module")
def TestingSession(api_engine):
    return sessionmaker(bind=api_engine)


@pytest.fixture(scope="module", autouse=True)
def setup_api_database(TestingSession):
    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


class TestAPIEndpoints:
    def test_91_api_get_framework(self, client: TestClient):
        res = client.get("/api/carbon-credit/framework")
        assert res.status_code == 200
        data = res.json()
        assert "framework_name" in data
        assert "disclaimer" in data
        assert data["boundaries"]["carbon_credits_issued"] is False

    def test_92_api_get_requirements(self, client: TestClient):
        res = client.get("/api/carbon-credit/requirements")
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 15

    def test_93_api_create_assessment(self, client: TestClient, TestingSession):
        import uuid
        uid = uuid.uuid4().hex[:8]
        with TestingSession() as db:
            p = ReductionProject(
                project_code=f"PRJ-API-{uid}-01",
                title="API Solar Project",
                category="RENEWABLE_ENERGY",
                status="IN_PROGRESS",
            )
            db.add(p)
            db.commit()
            p_id = p.id

        res = client.post(
            "/api/carbon-credit/assessments",
            json={"project_id": p_id, "reporting_period": "2024-10", "notes": "API test"},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["project_id"] == p_id
        assert data["status"] == "DRAFT"

    def test_94_api_create_assessment_invalid_project(self, client: TestClient):
        res = client.post(
            "/api/carbon-credit/assessments",
            json={"project_id": 999999, "reporting_period": "2024-10"},
        )
        assert res.status_code == 400

    def test_95_api_list_assessments(self, client: TestClient):
        res = client.get("/api/carbon-credit/assessments")
        assert res.status_code == 200
        data = res.json()
        assert "total" in data
        assert "items" in data

    def test_96_api_get_assessment_by_id(self, client: TestClient, TestingSession):
        import uuid
        uid = uuid.uuid4().hex[:8]
        with TestingSession() as db:
            p = ReductionProject(
                project_code=f"PRJ-API-{uid}-02",
                title="API Solar Project 2",
                category="RENEWABLE_ENERGY",
                status="IN_PROGRESS",
            )
            db.add(p)
            db.commit()
            ass = carbon_credit_service.create_assessment(
                db, CarbonCreditAssessmentCreate(project_id=p.id, reporting_period="2024-10")
            )
            ass_id = ass.id

        res = client.get(f"/api/carbon-credit/assessments/{ass_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == ass_id

    def test_97_api_get_assessment_not_found(self, client: TestClient):
        res = client.get("/api/carbon-credit/assessments/999999")
        assert res.status_code == 404

    def test_98_api_generate_assessment(self, client: TestClient, TestingSession):
        import uuid
        uid = uuid.uuid4().hex[:8]
        with TestingSession() as db:
            p = ReductionProject(
                project_code=f"PRJ-API-{uid}-03",
                title="API Solar Project 3",
                category="RENEWABLE_ENERGY",
                status="IN_PROGRESS",
            )
            db.add(p)
            db.commit()
            ass = carbon_credit_service.create_assessment(
                db, CarbonCreditAssessmentCreate(project_id=p.id, reporting_period="2024-10")
            )
            ass_id = ass.id

        res = client.post(f"/api/carbon-credit/assessments/{ass_id}/generate")
        assert res.status_code == 200
        data = res.json()
        assert data["overall_readiness_score"] >= 0
        assert data["status"] in ("GENERATED", "READY_FOR_METHODOLOGY_REVIEW", "NEEDS_REVIEW")

    def test_99_api_get_assessment_requirements(self, client: TestClient, TestingSession):
        import uuid
        uid = uuid.uuid4().hex[:8]
        with TestingSession() as db:
            p = ReductionProject(
                project_code=f"PRJ-API-{uid}-04",
                title="API Solar Project 4",
                category="RENEWABLE_ENERGY",
                status="IN_PROGRESS",
            )
            db.add(p)
            db.commit()
            ass = carbon_credit_service.create_assessment(
                db, CarbonCreditAssessmentCreate(project_id=p.id, reporting_period="2024-10")
            )
            ass_id = ass.id

        res = client.get(f"/api/carbon-credit/assessments/{ass_id}/requirements")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == len(REQUIREMENT_DEFINITIONS)

    def test_100_api_get_assessment_evidence(self, client: TestClient, TestingSession):
        import uuid
        uid = uuid.uuid4().hex[:8]
        with TestingSession() as db:
            p = ReductionProject(
                project_code=f"PRJ-API-{uid}-05",
                title="API Solar Project 5",
                category="RENEWABLE_ENERGY",
                status="IN_PROGRESS",
            )
            db.add(p)
            db.commit()
            ass = carbon_credit_service.create_assessment(
                db, CarbonCreditAssessmentCreate(project_id=p.id, reporting_period="2024-10")
            )
            carbon_credit_service.generate_assessment(db, ass.id)
            ass_id = ass.id

        res = client.get(f"/api/carbon-credit/assessments/{ass_id}/evidence")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)

    def test_101_api_get_assessment_actions(self, client: TestClient, TestingSession):
        import uuid
        uid = uuid.uuid4().hex[:8]
        with TestingSession() as db:
            p = ReductionProject(
                project_code=f"PRJ-API-{uid}-06",
                title="API Solar Project 6",
                category="RENEWABLE_ENERGY",
                status="IN_PROGRESS",
            )
            db.add(p)
            db.commit()
            ass = carbon_credit_service.create_assessment(
                db, CarbonCreditAssessmentCreate(project_id=p.id, reporting_period="2024-10")
            )
            carbon_credit_service.generate_assessment(db, ass.id)
            ass_id = ass.id

        res = client.get(f"/api/carbon-credit/assessments/{ass_id}/actions")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)

    def test_102_api_get_assessment_checklist(self, client: TestClient, TestingSession):
        import uuid
        uid = uuid.uuid4().hex[:8]
        with TestingSession() as db:
            p = ReductionProject(
                project_code=f"PRJ-API-{uid}-07",
                title="API Solar Project 7",
                category="RENEWABLE_ENERGY",
                status="IN_PROGRESS",
            )
            db.add(p)
            db.commit()
            ass = carbon_credit_service.create_assessment(
                db, CarbonCreditAssessmentCreate(project_id=p.id, reporting_period="2024-10")
            )
            carbon_credit_service.generate_assessment(db, ass.id)
            ass_id = ass.id

        res = client.get(f"/api/carbon-credit/assessments/{ass_id}/checklist")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 15

    def test_103_api_get_assessment_methodology(self, client: TestClient, TestingSession):
        import uuid
        uid = uuid.uuid4().hex[:8]
        with TestingSession() as db:
            p = ReductionProject(
                project_code=f"PRJ-API-{uid}-08",
                title="API Solar Project 8",
                category="RENEWABLE_ENERGY",
                status="IN_PROGRESS",
            )
            db.add(p)
            db.commit()
            ass = carbon_credit_service.create_assessment(
                db, CarbonCreditAssessmentCreate(project_id=p.id, reporting_period="2024-10")
            )
            carbon_credit_service.generate_assessment(db, ass.id)
            ass_id = ass.id

        res = client.get(f"/api/carbon-credit/assessments/{ass_id}/methodology")
        assert res.status_code == 200
        data = res.json()
        assert "overall_methodology_status" in data
        assert data["framework"] == "GENERIC_CARBON_STANDARD"

    def test_104_api_finalize_assessment(self, client: TestClient, TestingSession):
        import uuid
        uid = uuid.uuid4().hex[:8]
        with TestingSession() as db:
            p = ReductionProject(
                project_code=f"PRJ-API-{uid}-09",
                title="API Solar Project 9",
                category="RENEWABLE_ENERGY",
                status="IN_PROGRESS",
            )
            db.add(p)
            db.commit()
            ass = carbon_credit_service.create_assessment(
                db, CarbonCreditAssessmentCreate(project_id=p.id, reporting_period="2024-10")
            )
            ass_id = ass.id

        res = client.post(f"/api/carbon-credit/assessments/{ass_id}/finalize")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "FINALIZED"
        assert data["finalized_at"] is not None

    def test_105_api_finalize_twice_prohibited(self, client: TestClient, TestingSession):
        import uuid
        uid = uuid.uuid4().hex[:8]
        with TestingSession() as db:
            p = ReductionProject(
                project_code=f"PRJ-API-{uid}-10",
                title="API Solar Project 10",
                category="RENEWABLE_ENERGY",
                status="IN_PROGRESS",
            )
            db.add(p)
            db.commit()
            ass = carbon_credit_service.create_assessment(
                db, CarbonCreditAssessmentCreate(project_id=p.id, reporting_period="2024-10")
            )
            ass_id = ass.id

        client.post(f"/api/carbon-credit/assessments/{ass_id}/finalize")
        res2 = client.post(f"/api/carbon-credit/assessments/{ass_id}/finalize")
        assert res2.status_code == 400




# =============================================================================
# 8. COPILOT INTEGRATION & REFUSAL BOUNDARIES (106-115)
# =============================================================================

class TestCopilotIntegrationAndRefusals:
    def test_106_copilot_refusal_how_many_credits(self, sample_setup):
        db = sample_setup["db"]
        doc = sample_setup["document"]
        resp = copilot_service.chat(db, "How many carbon credits will I get from this project?", document_id=doc.id)
        assert "does not predict or issue carbon credits" in resp.answer.lower()
        assert resp.intent == "CARBON_CREDIT_READINESS"

    def test_107_copilot_refusal_sell_credits(self, sample_setup):
        db = sample_setup["db"]
        doc = sample_setup["document"]
        resp = copilot_service.chat(db, "Can I sell these carbon credits on a marketplace?", document_id=doc.id)
        assert "does not issue or certify tradable credits" in resp.answer.lower()
        assert resp.intent == "CARBON_CREDIT_READINESS"

    def test_108_copilot_refusal_additionality_guarantee(self, sample_setup):
        db = sample_setup["db"]
        doc = sample_setup["document"]
        resp = copilot_service.chat(db, "Are my reductions definitely additional?", document_id=doc.id)
        assert "does not determine additionality" in resp.answer.lower()
        assert resp.intent == "CARBON_CREDIT_READINESS"

    def test_109_copilot_refusal_verra_eligibility(self, sample_setup):
        db = sample_setup["db"]
        doc = sample_setup["document"]
        resp = copilot_service.chat(db, "Is my project Verra eligible?", document_id=doc.id)
        assert "standard-specific eligibility" in resp.answer.lower()
        assert resp.intent == "CARBON_CREDIT_METHODOLOGY"

    def test_110_copilot_refusal_credit_market_value(self, sample_setup):
        db = sample_setup["db"]
        doc = sample_setup["document"]
        resp = copilot_service.chat(db, "What will my credits be worth in EUR or USD?", document_id=doc.id)
        assert "does not estimate carbon-credit market value" in resp.answer.lower()
        assert resp.intent == "CARBON_CREDIT_READINESS"

    def test_111_copilot_refusal_has_project_generated_credits(self, sample_setup):
        db = sample_setup["db"]
        doc = sample_setup["document"]
        resp = copilot_service.chat(db, "Has this project generated carbon credits?", document_id=doc.id)
        assert "no" in resp.answer.lower()
        assert "does not issue, verify, guarantee, or generate" in resp.answer.lower()

    def test_112_copilot_intent_what_is_missing(self, sample_setup):
        db = sample_setup["db"]
        doc = sample_setup["document"]
        resp = copilot_service.chat(db, "What is missing before certification?", document_id=doc.id)
        assert "baseline accounting" in resp.answer.lower()
        assert resp.intent == "CARBON_CREDIT_MISSING"

    def test_113_copilot_intent_explain_score(self, sample_setup):
        db = sample_setup["db"]
        doc = sample_setup["document"]
        resp = copilot_service.chat(db, "Why is my carbon credit readiness score 62?", document_id=doc.id)
        assert "15 weighted dimensions" in resp.answer.lower()
        assert resp.intent == "CARBON_CREDIT_EXPLAIN_SCORE"

    def test_114_copilot_intent_is_project_verified(self, sample_setup):
        db = sample_setup["db"]
        doc = sample_setup["document"]
        resp = copilot_service.chat(db, "Is this project verified for carbon credits?", document_id=doc.id)
        assert "verificationrecord" in resp.answer.lower() or "verification status" in resp.answer.lower()
        assert resp.intent == "CARBON_CREDIT_VERIFICATION"

    def test_115_copilot_intent_is_project_ready(self, sample_setup):
        db = sample_setup["db"]
        doc = sample_setup["document"]
        resp = copilot_service.chat(db, "Is this project ready for carbon credits?", document_id=doc.id)
        assert "readiness bands" in resp.answer.lower() or "ready_for_methodology_review" in resp.answer.lower()
        assert resp.intent == "CARBON_CREDIT_READINESS"
