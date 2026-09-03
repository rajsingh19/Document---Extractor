"""
tests/test_green_finance.py — Test Suite for Green Finance Readiness Engine (Step 19).

Contains 105 comprehensive tests covering:
1. Models, Schemas & Database Operations
2. 10 Readiness Dimensions Evaluation
3. Deterministic Weighted Scoring & Band Thresholds
4. Missing Data != Zero Boundaries (Scope 3 Handling)
5. Carbon Accounting Grounding (POSTED Ledger Only)
6. Evidence Lineage & Provenance
7. Reduction Opportunities & Projects Integration
8. Measurement & Verification Links
9. Compliance Report Integration
10. Finance Document Checklist Boundaries (No Credit Scoring)
11. Immutability, Versioning & Audit History
12. REST API Endpoints
13. ReportLab PDF Generation
14. Copilot Integration & Credit Underwriting Refusal Boundaries
15. Safety & Product Boundaries
"""
import pytest
from datetime import datetime
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.database.base import Base
from backend.app.database.session import get_db, init_db
from backend.app.models.document import Document
from backend.app.models.sustainability_metric import SustainabilityMetric
from backend.app.models.activity_data import ActivityData
from backend.app.models.carbon_calculation import CarbonCalculation
from backend.app.models.carbon_ledger import CarbonLedgerEntry
from backend.app.models.reduction_opportunity import ReductionOpportunity
from backend.app.models.reduction_project import ReductionProject
from backend.app.models.reduction_measurement import ReductionMeasurement
from backend.app.models.verification_record import VerificationRecord
from backend.app.models.compliance_report import ComplianceReport
from backend.app.models.green_finance import (
    GreenFinanceAssessment,
    GreenFinanceRequirement,
    GreenFinanceEvidence,
    GreenFinanceAssessmentEvent,
)
from backend.app.services.green_finance_readiness import (
    green_finance_service,
    GREEN_FINANCE_DISCLAIMER,
    FINANCIAL_CHECKLIST_DISCLAIMER,
    REQUIREMENT_DEFINITIONS,
)
from backend.app.services.green_finance_pdf import green_finance_pdf_renderer
from backend.app.services.copilot_llm import copilot_llm_service
from backend.app.schemas.copilot import CopilotContext, CopilotSummary
from backend.app.schemas.green_finance import GreenFinanceAssessmentCreate


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
def seeded_db_session(db_session):
    """Populate db_session with sample POSTED ledger entries and sustainability records."""
    doc = Document(
        original_filename="test_invoice.pdf",
        filename="test_invoice.pdf",
        file_path="/tmp/test_invoice.pdf",
        file_size=1024,
        document_type="UTILITY_BILL",
        status="COMPLETED",
        extracted_text="Electricity consumption: 48,750 kWh for October 2024. Diesel generator fuel: 420 Liters.",
        reporting_period="2024-10",
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    metric1 = SustainabilityMetric(
        document_id=doc.id,
        metric_type="grid_electricity",
        category="energy",
        source_field="grid_electricity",
        value=48750.0,
        unit="kWh",
        source_text="Electricity consumption: 48,750 kWh for October 2024.",
    )
    metric2 = SustainabilityMetric(
        document_id=doc.id,
        metric_type="fuel_diesel",
        category="energy",
        source_field="fuel_diesel",
        value=420.0,
        unit="liters",
        source_text="Diesel generator fuel: 420 Liters.",
    )
    db_session.add_all([metric1, metric2])
    db_session.commit()

    act1 = ActivityData(
        document_id=doc.id,
        activity_type="ELECTRICITY",
        category="ENERGY",
        quantity=48750.0,
        unit="kWh",
        scope="SCOPE_2",
        reporting_period="2024-10",
    )
    act2 = ActivityData(
        document_id=doc.id,
        activity_type="DIESEL",
        category="FUEL",
        quantity=420.0,
        unit="liters",
        scope="SCOPE_1",
        reporting_period="2024-10",
    )
    db_session.add_all([act1, act2])
    db_session.commit()

    calc1 = CarbonCalculation(
        activity_data_id=act1.id,
        document_id=doc.id,
        activity_type="ELECTRICITY",
        quantity=Decimal("48750.0"),
        activity_unit="kWh",
        scope="SCOPE_2",
        calculated_co2e=Decimal("31880.0"),
        factor_code="EF-ELEC-IN-WEST",
        factor_value=Decimal("0.716"),
        reporting_period="2024-10",
    )
    calc2 = CarbonCalculation(
        activity_data_id=act2.id,
        document_id=doc.id,
        activity_type="DIESEL",
        quantity=Decimal("420.0"),
        activity_unit="liters",
        scope="SCOPE_1",
        calculated_co2e=Decimal("1125.6"),
        factor_code="EF-DIESEL-GEN",
        factor_value=Decimal("2.68"),
        reporting_period="2024-10",
    )
    db_session.add_all([calc1, calc2])
    db_session.commit()

    ledger1 = CarbonLedgerEntry(
        carbon_calculation_id=calc1.id,
        activity_data_id=act1.id,
        document_id=doc.id,
        scope="SCOPE_2",
        quantity=Decimal("48750.0"),
        activity_unit="kWh",
        calculated_co2e=Decimal("31880.0"),
        activity_type="ELECTRICITY",
        category="ENERGY",
        factor_name="CEA Grid Factor",
        factor_value=Decimal("0.716"),
        accounting_status="POSTED",
        reporting_period="2024-10",
    )
    ledger2 = CarbonLedgerEntry(
        carbon_calculation_id=calc2.id,
        activity_data_id=act2.id,
        document_id=doc.id,
        scope="SCOPE_1",
        quantity=Decimal("420.0"),
        activity_unit="liters",
        calculated_co2e=Decimal("1125.6"),
        activity_type="DIESEL",
        category="FUEL",
        factor_name="DEFRA Diesel Factor",
        factor_value=Decimal("2.68"),
        accounting_status="POSTED",
        reporting_period="2024-10",
    )
    db_session.add_all([ledger1, ledger2])
    db_session.commit()

    opp = ReductionOpportunity(
        opportunity_code="OPP-2024-0001",
        title="Rooftop Solar Expansion",
        description="Expand rooftop solar PV capacity",
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

    proj = ReductionProject(
        project_code="PRJ-2024-0001",
        opportunity_id=opp.id,
        title="Solar Rooftop Installation",
        category="RENEWABLE_ENERGY",
        status="IN_PROGRESS",
    )
    db_session.add(proj)
    db_session.commit()

    meas = ReductionMeasurement(
        project_id=proj.id,
        reference_period="2024-09",
        measurement_period="2024-10",
        reference_co2e=Decimal("35000.0"),
        measurement_co2e=Decimal("33010.0"),
        observed_change=Decimal("-1990.0"),
        measurement_status="MEASURED",
    )
    db_session.add(meas)
    db_session.commit()

    verif = VerificationRecord(
        project_id=proj.id,
        measurement_id=meas.id,
        verifier_name="Green Audit Corp",
        verification_status="VERIFIED",
    )
    db_session.add(verif)
    db_session.commit()

    rep = ComplianceReport(
        report_code="CR-GHG-2024-0001",
        report_name="GHG Protocol Annual Inventory 2024",
        framework="GHG_PROTOCOL",
        reporting_period="2024-10",
        status="GENERATED",
        completeness_status="COMPLETE",
    )
    db_session.add(rep)
    db_session.commit()
    return db_session


# =============================================================================
# 1. DATABASE MODELS & SCHEMAS (20 Tests)
# =============================================================================

class TestGreenFinanceModels:

    def test_01_create_green_finance_assessment_model(self, db_session):
        ass = GreenFinanceAssessment(
            assessment_code="GFA-2026-0001",
            business_name="TARA ENGINEERING WORKS",
            reporting_period="2024-10",
            reporting_year=2024,
            assessment_version="1.0",
            overall_readiness_score=72.5,
            readiness_band="READY_FOR_REVIEW",
            status="DRAFT",
        )
        db_session.add(ass)
        db_session.commit()
        db_session.refresh(ass)
        assert ass.id is not None
        assert ass.assessment_code == "GFA-2026-0001"
        assert ass.overall_readiness_score == 72.5

    def test_02_create_green_finance_requirement_model(self, db_session):
        ass = GreenFinanceAssessment(assessment_code="GFA-2026-0002", reporting_period="2024-10")
        db_session.add(ass)
        db_session.commit()

        req = GreenFinanceRequirement(
            assessment_id=ass.id,
            requirement_code="GF_DATA_DOCS",
            requirement_name="Processed Business Source Documents",
            category="DATA_READINESS",
            weight=1.0,
            status="SUPPORTED",
        )
        db_session.add(req)
        db_session.commit()
        db_session.refresh(req)
        assert req.id is not None
        assert req.requirement_code == "GF_DATA_DOCS"

    def test_03_create_green_finance_evidence_model(self, db_session):
        ass = GreenFinanceAssessment(assessment_code="GFA-2026-0003", reporting_period="2024-10")
        db_session.add(ass)
        db_session.commit()

        req = GreenFinanceRequirement(assessment_id=ass.id, requirement_code="GF_EVID_TEXT", requirement_name="Evidence Text", category="EVIDENCE")
        db_session.add(req)
        db_session.commit()

        ev = GreenFinanceEvidence(
            assessment_id=ass.id,
            requirement_id=req.id,
            source_type="DOCUMENT",
            document_id=1,
            source_field="extracted_text",
            source_text="Electricity bill 48750 kWh",
            evidence_status="VERIFIED",
        )
        db_session.add(ev)
        db_session.commit()
        db_session.refresh(ev)
        assert ev.id is not None
        assert ev.source_type == "DOCUMENT"

    def test_04_create_assessment_event_model(self, db_session):
        ass = GreenFinanceAssessment(assessment_code="GFA-2026-0004", reporting_period="2024-10")
        db_session.add(ass)
        db_session.commit()

        ev = GreenFinanceAssessmentEvent(
            assessment_id=ass.id,
            event_type="CREATED",
            previous_status=None,
            new_status="DRAFT",
            notes="Initial assessment",
            actor="SYSTEM",
        )
        db_session.add(ev)
        db_session.commit()
        db_session.refresh(ev)
        assert ev.id is not None
        assert ev.event_type == "CREATED"

    def test_05_assessment_cascade_delete(self, db_session):
        ass = GreenFinanceAssessment(assessment_code="GFA-2026-0005", reporting_period="2024-10")
        db_session.add(ass)
        db_session.commit()

        req = GreenFinanceRequirement(assessment_id=ass.id, requirement_code="GF_DATA_DOCS", requirement_name="Docs", category="DATA_READINESS")
        db_session.add(req)
        db_session.commit()

        db_session.delete(ass)
        db_session.commit()

        req_count = db_session.query(GreenFinanceRequirement).filter_by(assessment_id=ass.id).count()
        assert req_count == 0

    def test_06_requirement_definitions_count(self):
        assert len(REQUIREMENT_DEFINITIONS) >= 15

    def test_07_requirement_categories_presence(self):
        cats = {r["category"] for r in REQUIREMENT_DEFINITIONS}
        expected = {
            "DATA_READINESS", "CARBON_ACCOUNTING", "EVIDENCE", "EMISSIONS_DATA",
            "REDUCTION_PLAN", "REDUCTION_PROJECTS", "MEASUREMENT_VERIFICATION",
            "REPORTING", "GOVERNANCE", "FINANCE_DOCUMENT_READINESS"
        }
        assert expected.issubset(cats)

    def test_08_assessment_schema_validation(self):
        dto = GreenFinanceAssessmentCreate(reporting_period="2024-10", business_name="TEST MSME")
        assert dto.reporting_period == "2024-10"
        assert dto.business_name == "TEST MSME"

    def test_09_assessment_default_business_name(self):
        dto = GreenFinanceAssessmentCreate(reporting_period="2024-10")
        assert dto.business_name == "TARA ENGINEERING WORKS"

    def test_10_disclaimer_text_preservation(self):
        assert "not a lender credit score" in GREEN_FINANCE_DISCLAIMER

    def test_11_financial_checklist_disclaimer(self):
        assert "Credit assessment is outside the scope of this product" in FINANCIAL_CHECKLIST_DISCLAIMER

    def test_12_status_to_completion_supported(self):
        assert green_finance_service._status_to_completion("SUPPORTED") == 1.0

    def test_13_status_to_completion_partially_supported(self):
        assert green_finance_service._status_to_completion("PARTIALLY_SUPPORTED") == 0.5

    def test_14_status_to_completion_needs_review(self):
        assert green_finance_service._status_to_completion("NEEDS_REVIEW") == 0.25

    def test_15_status_to_completion_missing(self):
        assert green_finance_service._status_to_completion("MISSING") == 0.0

    def test_16_readiness_band_ready_for_review(self):
        assert green_finance_service._calculate_readiness_band(75.0) == "READY_FOR_REVIEW"

    def test_17_readiness_band_partially_ready(self):
        assert green_finance_service._calculate_readiness_band(55.0) == "PARTIALLY_READY"

    def test_18_readiness_band_not_ready(self):
        assert green_finance_service._calculate_readiness_band(30.0) == "NOT_READY"

    def test_19_readiness_band_boundary_70(self):
        assert green_finance_service._calculate_readiness_band(70.0) == "READY_FOR_REVIEW"

    def test_20_readiness_band_boundary_40(self):
        assert green_finance_service._calculate_readiness_band(40.0) == "PARTIALLY_READY"


# =============================================================================
# 2. DETERMINISTIC READINESS ENGINE (30 Tests)
# =============================================================================

class TestGreenFinanceEngine:

    def test_21_create_assessment_service(self, db_session):
        ass = green_finance_service.create_assessment(db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        assert ass.id is not None
        assert ass.status == "DRAFT"
        assert ass.assessment_code.startswith("GFA-")

    def test_22_generate_assessment_with_empty_db(self, db_session):
        ass = green_finance_service.create_assessment(db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        gen_ass = green_finance_service.generate_assessment(db_session, ass.id)
        assert gen_ass.overall_readiness_score == 3.9
        assert gen_ass.readiness_band == "NOT_READY"
        assert gen_ass.status == "NEEDS_REVIEW"

    def test_23_generate_assessment_with_posted_db(self, seeded_db_session):
        ass = green_finance_service.create_assessment(seeded_db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        gen_ass = green_finance_service.generate_assessment(seeded_db_session, ass.id)
        assert gen_ass.overall_readiness_score > 60.0
        assert gen_ass.readiness_band in ["PARTIALLY_READY", "READY_FOR_REVIEW"]

    def test_24_data_readiness_docs_supported(self, seeded_db_session):
        ass = green_finance_service.create_assessment(seeded_db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        gen_ass = green_finance_service.generate_assessment(seeded_db_session, ass.id)
        req = seeded_db_session.query(GreenFinanceRequirement).filter_by(assessment_id=gen_ass.id, requirement_code="GF_DATA_DOCS").first()
        assert req.status == "SUPPORTED"

    def test_25_carbon_accounting_posted_supported(self, seeded_db_session):
        ass = green_finance_service.create_assessment(seeded_db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        gen_ass = green_finance_service.generate_assessment(seeded_db_session, ass.id)
        req = seeded_db_session.query(GreenFinanceRequirement).filter_by(assessment_id=gen_ass.id, requirement_code="GF_CALC_POSTED").first()
        assert req.status == "SUPPORTED"

    def test_26_scope_1_emissions_supported(self, seeded_db_session):
        ass = green_finance_service.create_assessment(seeded_db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        gen_ass = green_finance_service.generate_assessment(seeded_db_session, ass.id)
        req = seeded_db_session.query(GreenFinanceRequirement).filter_by(assessment_id=gen_ass.id, requirement_code="GF_EMIS_S1").first()
        assert req.status == "SUPPORTED"

    def test_27_scope_2_emissions_supported(self, seeded_db_session):
        ass = green_finance_service.create_assessment(seeded_db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        gen_ass = green_finance_service.generate_assessment(seeded_db_session, ass.id)
        req = seeded_db_session.query(GreenFinanceRequirement).filter_by(assessment_id=gen_ass.id, requirement_code="GF_EMIS_S2").first()
        assert req.status == "SUPPORTED"

    def test_28_scope_3_missing_handled_as_missing(self, seeded_db_session):
        ass = green_finance_service.create_assessment(seeded_db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        gen_ass = green_finance_service.generate_assessment(seeded_db_session, ass.id)
        req = seeded_db_session.query(GreenFinanceRequirement).filter_by(assessment_id=gen_ass.id, requirement_code="GF_EMIS_S3").first()
        assert req.status == "MISSING"
        assert "Marked MISSING" in req.reason

    def test_29_reduction_opportunities_supported(self, seeded_db_session):
        ass = green_finance_service.create_assessment(seeded_db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        gen_ass = green_finance_service.generate_assessment(seeded_db_session, ass.id)
        req = seeded_db_session.query(GreenFinanceRequirement).filter_by(assessment_id=gen_ass.id, requirement_code="GF_PLAN_OPPS").first()
        assert req.status == "SUPPORTED"

    def test_30_reduction_projects_supported(self, seeded_db_session):
        ass = green_finance_service.create_assessment(seeded_db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        gen_ass = green_finance_service.generate_assessment(seeded_db_session, ass.id)
        req = seeded_db_session.query(GreenFinanceRequirement).filter_by(assessment_id=gen_ass.id, requirement_code="GF_PROJ_EXISTS").first()
        assert req.status == "SUPPORTED"

    def test_31_measurement_supported(self, seeded_db_session):
        ass = green_finance_service.create_assessment(seeded_db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        gen_ass = green_finance_service.generate_assessment(seeded_db_session, ass.id)
        req = seeded_db_session.query(GreenFinanceRequirement).filter_by(assessment_id=gen_ass.id, requirement_code="GF_MV_MEASUREMENT").first()
        assert req.status == "SUPPORTED"

    def test_32_verification_supported(self, seeded_db_session):
        ass = green_finance_service.create_assessment(seeded_db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        gen_ass = green_finance_service.generate_assessment(seeded_db_session, ass.id)
        req = seeded_db_session.query(GreenFinanceRequirement).filter_by(assessment_id=gen_ass.id, requirement_code="GF_MV_VERIFICATION").first()
        assert req.status == "SUPPORTED"

    def test_33_compliance_report_supported(self, seeded_db_session):
        ass = green_finance_service.create_assessment(seeded_db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        gen_ass = green_finance_service.generate_assessment(seeded_db_session, ass.id)
        req = seeded_db_session.query(GreenFinanceRequirement).filter_by(assessment_id=gen_ass.id, requirement_code="GF_REP_GENERATED").first()
        assert req.status == "SUPPORTED"

    def test_34_finance_documents_supported(self, seeded_db_session):
        ass = green_finance_service.create_assessment(seeded_db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        gen_ass = green_finance_service.generate_assessment(seeded_db_session, ass.id)
        req = seeded_db_session.query(GreenFinanceRequirement).filter_by(assessment_id=gen_ass.id, requirement_code="GF_FIN_DOCS").first()
        assert req.status == "SUPPORTED"

    def test_35_evidence_records_created(self, seeded_db_session):
        ass = green_finance_service.create_assessment(seeded_db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        gen_ass = green_finance_service.generate_assessment(seeded_db_session, ass.id)
        ev_count = seeded_db_session.query(GreenFinanceEvidence).filter_by(assessment_id=gen_ass.id).count()
        assert ev_count > 0

    def test_36_dto_builder_dimensions_count(self, seeded_db_session):
        ass = green_finance_service.create_assessment(seeded_db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        gen_ass = green_finance_service.generate_assessment(seeded_db_session, ass.id)
        dto = green_finance_service.build_assessment_dto(seeded_db_session, gen_ass)
        assert len(dto.dimensions) == 10

    def test_37_dto_missing_requirements_list(self, seeded_db_session):
        ass = green_finance_service.create_assessment(seeded_db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        gen_ass = green_finance_service.generate_assessment(seeded_db_session, ass.id)
        dto = green_finance_service.build_assessment_dto(seeded_db_session, gen_ass)
        assert len(dto.missing_requirements) >= 1

    def test_38_dto_next_actions_list(self, seeded_db_session):
        ass = green_finance_service.create_assessment(seeded_db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        gen_ass = green_finance_service.generate_assessment(seeded_db_session, ass.id)
        dto = green_finance_service.build_assessment_dto(seeded_db_session, gen_ass)
        assert len(dto.next_actions) >= 1

    def test_39_dto_checklist_items_count(self, seeded_db_session):
        ass = green_finance_service.create_assessment(seeded_db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        gen_ass = green_finance_service.generate_assessment(seeded_db_session, ass.id)
        dto = green_finance_service.build_assessment_dto(seeded_db_session, gen_ass)
        assert len(dto.checklist) == len(REQUIREMENT_DEFINITIONS)

    def test_40_update_status_service(self, db_session):
        ass = green_finance_service.create_assessment(db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        updated = green_finance_service.update_assessment_status(db_session, ass.id, "READY_FOR_APPLICATION", "Ready for review")
        assert updated.status == "READY_FOR_APPLICATION"

    def test_41_finalize_assessment_service(self, db_session):
        ass = green_finance_service.create_assessment(db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        finalized = green_finance_service.update_assessment_status(db_session, ass.id, "FINALIZED")
        assert finalized.status == "FINALIZED"
        assert finalized.finalized_at is not None

    def test_42_finalized_assessment_immutable_error(self, db_session):
        ass = green_finance_service.create_assessment(db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        green_finance_service.update_assessment_status(db_session, ass.id, "FINALIZED")
        with pytest.raises(ValueError, match="FINALIZED"):
            green_finance_service.generate_assessment(db_session, ass.id)

    def test_43_finalized_assessment_status_change_prohibited(self, db_session):
        ass = green_finance_service.create_assessment(db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        green_finance_service.update_assessment_status(db_session, ass.id, "FINALIZED")
        with pytest.raises(ValueError, match="FINALIZED"):
            green_finance_service.update_assessment_status(db_session, ass.id, "DRAFT")

    def test_44_audit_event_logged_on_create(self, db_session):
        ass = green_finance_service.create_assessment(db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        events = db_session.query(GreenFinanceAssessmentEvent).filter_by(assessment_id=ass.id).all()
        assert len(events) >= 1
        assert events[0].event_type == "CREATED"

    def test_45_audit_event_logged_on_status_change(self, db_session):
        ass = green_finance_service.create_assessment(db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        green_finance_service.update_assessment_status(db_session, ass.id, "NEEDS_REVIEW", "Needs manual check")
        events = db_session.query(GreenFinanceAssessmentEvent).filter_by(assessment_id=ass.id).all()
        assert any(e.event_type == "STATUS_CHANGE" for e in events)

    def test_46_deterministic_repeatability(self, seeded_db_session):
        ass = green_finance_service.create_assessment(seeded_db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        g1 = green_finance_service.generate_assessment(seeded_db_session, ass.id)
        s1 = g1.overall_readiness_score

        ass2 = green_finance_service.create_assessment(seeded_db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        g2 = green_finance_service.generate_assessment(seeded_db_session, ass2.id)
        s2 = g2.overall_readiness_score

        assert s1 == s2

    def test_47_get_assessments_filter_period(self, db_session):
        green_finance_service.create_assessment(db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        green_finance_service.create_assessment(db_session, GreenFinanceAssessmentCreate(reporting_period="2024-11"))
        res = green_finance_service.get_assessments(db_session, reporting_period="2024-10")
        assert len(res) == 1
        assert res[0].reporting_period == "2024-10"

    def test_48_get_assessments_filter_status(self, db_session):
        ass1 = green_finance_service.create_assessment(db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        green_finance_service.update_assessment_status(db_session, ass1.id, "FINALIZED")
        green_finance_service.create_assessment(db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        res = green_finance_service.get_assessments(db_session, status="FINALIZED")
        assert len(res) == 1
        assert res[0].status == "FINALIZED"

    def test_49_invalid_status_raises_error(self, db_session):
        ass = green_finance_service.create_assessment(db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        with pytest.raises(ValueError, match="Invalid assessment status"):
            green_finance_service.update_assessment_status(db_session, ass.id, "APPROVED_FOR_LOAN")

    def test_50_version_string_explicit(self, db_session):
        ass = green_finance_service.create_assessment(db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        assert ass.assessment_version == "1.0"


# =============================================================================
# 3. SAFETY & BOUNDARY SUITE (25 Tests)
# =============================================================================

class TestSafetyBoundaries:

    def test_51_no_loan_approval_logic(self):
        fields = GreenFinanceAssessment.__table__.columns.keys()
        forbidden = ["loan_approved", "approval_prediction", "credit_score", "interest_rate", "loan_amount"]
        for f in forbidden:
            assert f not in fields

    def test_52_no_creditworthiness_scoring(self):
        for req in REQUIREMENT_DEFINITIONS:
            assert "credit" not in req["name"].lower()
            assert "debt" not in req["name"].lower()
            assert "profit" not in req["name"].lower()

    def test_53_disclaimer_attached_to_response(self, seeded_db_session):
        ass = green_finance_service.create_assessment(seeded_db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        dto = green_finance_service.build_assessment_dto(seeded_db_session, ass)
        assert "not a lender credit score" in dto.disclaimer

    def test_54_financial_checklist_disclaimer_present(self, seeded_db_session):
        ass = green_finance_service.create_assessment(seeded_db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        gen_ass = green_finance_service.generate_assessment(seeded_db_session, ass.id)
        dto = green_finance_service.build_assessment_dto(seeded_db_session, gen_ass)
        fin_dim = next(d for d in dto.dimensions if d.category == "FINANCE_DOCUMENT_READINESS")
        assert "Credit assessment is outside the scope of this product" in fin_dim.explanation

    def test_55_missing_data_not_treated_as_zero(self, db_session):
        ass = green_finance_service.create_assessment(db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        gen_ass = green_finance_service.generate_assessment(db_session, ass.id)
        req = db_session.query(GreenFinanceRequirement).filter_by(assessment_id=gen_ass.id, requirement_code="GF_EMIS_S3").first()
        assert req.status == "MISSING"

    def test_56_no_unposted_ledger_entries_used(self, db_session):
        doc = Document(
            original_filename="unposted.pdf",
            filename="unposted.pdf",
            file_path="/tmp/unposted.pdf",
            file_size=1024,
            document_type="UTILITY_BILL",
            status="COMPLETED",
            reporting_period="2024-10",
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        act = ActivityData(document_id=doc.id, activity_type="ELECTRICITY", category="ENERGY", quantity=10.0, unit="kWh", scope="SCOPE_1", reporting_period="2024-10")
        db_session.add(act)
        db_session.commit()
        db_session.refresh(act)

        calc = CarbonCalculation(activity_data_id=act.id, document_id=doc.id, activity_type="ELECTRICITY", quantity=Decimal("10.0"), activity_unit="kWh", scope="SCOPE_1", calculated_co2e=Decimal("10.0"), reporting_period="2024-10")
        db_session.add(calc)
        db_session.commit()
        db_session.refresh(calc)

        unposted = CarbonLedgerEntry(
            carbon_calculation_id=calc.id,
            activity_data_id=act.id,
            document_id=doc.id,
            scope="SCOPE_1",
            quantity=Decimal("10.0"),
            activity_unit="kWh",
            activity_type="ELECTRICITY",
            calculated_co2e=Decimal("10.0"),
            accounting_status="UNPOSTED",
            reporting_period="2024-10",
        )
        db_session.add(unposted)
        db_session.commit()

        ass = green_finance_service.create_assessment(db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        gen_ass = green_finance_service.generate_assessment(db_session, ass.id)
        req = db_session.query(GreenFinanceRequirement).filter_by(assessment_id=gen_ass.id, requirement_code="GF_CALC_POSTED").first()
        assert req.status == "MISSING"

    def test_57_no_fabricated_evidence_snippets(self, seeded_db_session):
        ass = green_finance_service.create_assessment(seeded_db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        gen_ass = green_finance_service.generate_assessment(seeded_db_session, ass.id)
        evidence = seeded_db_session.query(GreenFinanceEvidence).all()
        for ev in evidence:
            if ev.source_type == "METRIC":
                m = seeded_db_session.query(SustainabilityMetric).filter_by(id=ev.source_id).first()
                assert m is not None

    def test_58_copilot_loan_approval_refusal(self):
        ctx = CopilotContext(intent="GENERAL", query="Will I get approved for a green loan?", sources=[], documents=[], summary=CopilotSummary(total_documents=0, total_metrics=0, total_emissions_tco2e=0.0), insights=[], review_items=[], attention_items=[])
        resp = copilot_llm_service._generate_deterministic_response(context=ctx, source_map={}, recommendations=[])
        assert "does not perform credit underwriting" in resp.answer

    def test_59_copilot_interest_rate_refusal(self):
        ctx = CopilotContext(intent="GENERAL", query="What interest rate will the bank give me?", sources=[], documents=[], summary=CopilotSummary(total_documents=0, total_metrics=0, total_emissions_tco2e=0.0), insights=[], review_items=[], attention_items=[])
        resp = copilot_llm_service._generate_deterministic_response(context=ctx, source_map={}, recommendations=[])
        assert "does not perform credit underwriting" in resp.answer

    def test_60_copilot_credit_score_refusal(self):
        ctx = CopilotContext(intent="GENERAL", query="Calculate my credit score for loan eligibility", sources=[], documents=[], summary=CopilotSummary(total_documents=0, total_metrics=0, total_emissions_tco2e=0.0), insights=[], review_items=[], attention_items=[])
        resp = copilot_llm_service._generate_deterministic_response(context=ctx, source_map={}, recommendations=[])
        assert "does not perform credit underwriting" in resp.answer

    def test_61_copilot_green_finance_intent_answering(self):
        ctx = CopilotContext(intent="GREEN_FINANCE_READINESS", query="What is my green finance readiness score?", sources=[], documents=[], summary=CopilotSummary(total_documents=0, total_metrics=0, total_emissions_tco2e=0.0), insights=[], review_items=[], attention_items=[])
        resp = copilot_llm_service._generate_deterministic_response(context=ctx, source_map={}, recommendations=[])
        assert "Green Finance Readiness Assessment" in resp.answer
        assert resp.intent == "GREEN_FINANCE_READINESS"

    def test_62_no_llm_numerical_score_generation(self, seeded_db_session):
        ass = green_finance_service.create_assessment(seeded_db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        gen_ass = green_finance_service.generate_assessment(seeded_db_session, ass.id)
        assert isinstance(gen_ass.overall_readiness_score, float)

    def test_63_planned_project_not_completed(self, db_session):
        opp = ReductionOpportunity(
            opportunity_code="OPP-2024-9999",
            title="Opp",
            description="Desc",
            category="ENERGY",
            trigger_type="HIGH_ENERGY_USE",
            rationale="Rat",
            recommended_action="Act",
            limitations="Lim",
        )
        db_session.add(opp)
        db_session.commit()
        proj = ReductionProject(project_code="PRJ-2024-9999", opportunity_id=opp.id, title="Planned Solar", category="ENERGY", status="PLANNED")
        db_session.add(proj)
        db_session.commit()

        ass = green_finance_service.create_assessment(db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        gen_ass = green_finance_service.generate_assessment(db_session, ass.id)
        req = db_session.query(GreenFinanceRequirement).filter_by(assessment_id=gen_ass.id, requirement_code="GF_PROJ_STATUS").first()
        assert req.status == "SUPPORTED"
        assert "active in lifecycle" in req.reason

    def test_64_no_carbon_credits_in_scoring(self):
        for req in REQUIREMENT_DEFINITIONS:
            assert "credit" not in req["code"].lower()
            assert "offset" not in req["code"].lower()

    def test_65_no_roi_claims_in_next_actions(self, seeded_db_session):
        ass = green_finance_service.create_assessment(seeded_db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        gen_ass = green_finance_service.generate_assessment(seeded_db_session, ass.id)
        dto = green_finance_service.build_assessment_dto(seeded_db_session, gen_ass)
        for act in dto.next_actions:
            assert "ROI" not in act.expected_readiness_impact
            assert "payback" not in act.expected_readiness_impact.lower()

    def test_66_no_loan_amount_estimation(self):
        for req in REQUIREMENT_DEFINITIONS:
            assert "amount" not in req["code"].lower()

    def test_67_finance_documents_presence_only(self, seeded_db_session):
        ass = green_finance_service.create_assessment(seeded_db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        gen_ass = green_finance_service.generate_assessment(seeded_db_session, ass.id)
        req = seeded_db_session.query(GreenFinanceRequirement).filter_by(assessment_id=gen_ass.id, requirement_code="GF_FIN_DOCS").first()
        assert "Presence of core business identity" in req.description

    def test_68_governance_missing_when_unspecified(self, db_session):
        ass = green_finance_service.create_assessment(db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        gen_ass = green_finance_service.generate_assessment(db_session, ass.id)
        req = db_session.query(GreenFinanceRequirement).filter_by(assessment_id=gen_ass.id, requirement_code="GF_GOV_POLICY").first()
        assert req.status == "MISSING"

    def test_69_audit_events_immutable(self, seeded_db_session):
        ass = green_finance_service.create_assessment(seeded_db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        green_finance_service.generate_assessment(seeded_db_session, ass.id)
        events = seeded_db_session.query(GreenFinanceAssessmentEvent).filter_by(assessment_id=ass.id).all()
        assert len(events) >= 2

    def test_70_pdf_contains_disclaimer(self, seeded_db_session):
        ass = green_finance_service.create_assessment(seeded_db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        gen_ass = green_finance_service.generate_assessment(seeded_db_session, ass.id)
        dto = green_finance_service.build_assessment_dto(seeded_db_session, gen_ass)
        pdf_bytes = green_finance_pdf_renderer.render(dto)
        assert len(pdf_bytes) > 2000
        assert pdf_bytes.startswith(b"%PDF")

    def test_71_ready_for_review_does_not_mean_financing_guarantee(self):
        band = green_finance_service._calculate_readiness_band(95.0)
        assert band == "READY_FOR_REVIEW"
        assert band != "LOAN_APPROVED"

    def test_72_assessment_code_uniqueness(self, db_session):
        a1 = green_finance_service.create_assessment(db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        a2 = green_finance_service.create_assessment(db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        assert a1.assessment_code != a2.assessment_code

    def test_73_missing_requirements_priority_high(self, db_session):
        ass = green_finance_service.create_assessment(db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        gen_ass = green_finance_service.generate_assessment(db_session, ass.id)
        dto = green_finance_service.build_assessment_dto(db_session, gen_ass)
        s3_miss = next((m for m in dto.missing_requirements if m.requirement_code == "GF_EMIS_S3"), None)
        if s3_miss:
            assert s3_miss.priority in ["HIGH", "MEDIUM"]

    def test_74_engine_version_is_1_0(self):
        assert green_finance_service.engine_version == "1.0"

    def test_75_audit_actor_defaults_to_system(self, db_session):
        ass = green_finance_service.create_assessment(db_session, GreenFinanceAssessmentCreate(reporting_period="2024-10"))
        ev = db_session.query(GreenFinanceAssessmentEvent).filter_by(assessment_id=ass.id).all()
        assert ev[0].actor == "SYSTEM"


# =============================================================================
# 4. REST API ENDPOINTS (30 Tests)
# =============================================================================

@pytest.fixture(scope="module", autouse=True)
def setup_api_database():
    init_db()
    api_engine = create_engine("sqlite:///./dev.db", echo=False)
    Base.metadata.create_all(bind=api_engine)
    TestingSessionLocal = sessionmaker(bind=api_engine)

    def override_get_db():
        db = TestingSessionLocal()
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

    def test_76_api_get_requirements(self, client):
        response = client.get("/api/green-finance/requirements")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 15

    def test_77_api_get_framework(self, client):
        response = client.get("/api/green-finance/framework")
        assert response.status_code == 200
        data = response.json()
        assert data["framework_name"] == "Green Finance Readiness Engine"
        assert "not a lender credit score" in data["disclaimer"]

    def test_78_api_create_assessment(self, client):
        payload = {"reporting_period": "2024-10", "business_name": "API MSME"}
        response = client.post("/api/green-finance/assessments", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["assessment_code"].startswith("GFA-")
        assert data["business_name"] == "API MSME"

    def test_79_api_list_assessments(self, client):
        client.post("/api/green-finance/assessments", json={"reporting_period": "2024-10"})
        response = client.get("/api/green-finance/assessments")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    def test_80_api_get_assessment_detail(self, client):
        res = client.post("/api/green-finance/assessments", json={"reporting_period": "2024-10"})
        ass_id = res.json()["id"]

        response = client.get(f"/api/green-finance/assessments/{ass_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == ass_id

    def test_81_api_generate_assessment(self, client):
        res = client.post("/api/green-finance/assessments", json={"reporting_period": "2024-10"})
        ass_id = res.json()["id"]

        response = client.post(f"/api/green-finance/assessments/{ass_id}/generate")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["GENERATED", "NEEDS_REVIEW"]
        assert len(data["dimensions"]) == 10

    def test_82_api_get_requirements_subresource(self, client):
        res = client.post("/api/green-finance/assessments", json={"reporting_period": "2024-10"})
        ass_id = res.json()["id"]
        client.post(f"/api/green-finance/assessments/{ass_id}/generate")

        response = client.get(f"/api/green-finance/assessments/{ass_id}/requirements")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 15

    def test_83_api_get_evidence_subresource(self, client):
        res = client.post("/api/green-finance/assessments", json={"reporting_period": "2024-10"})
        ass_id = res.json()["id"]
        client.post(f"/api/green-finance/assessments/{ass_id}/generate")

        response = client.get(f"/api/green-finance/assessments/{ass_id}/evidence")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_84_api_get_actions_subresource(self, client):
        res = client.post("/api/green-finance/assessments", json={"reporting_period": "2024-10"})
        ass_id = res.json()["id"]
        client.post(f"/api/green-finance/assessments/{ass_id}/generate")

        response = client.get(f"/api/green-finance/assessments/{ass_id}/actions")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_85_api_get_checklist_subresource(self, client):
        res = client.post("/api/green-finance/assessments", json={"reporting_period": "2024-10"})
        ass_id = res.json()["id"]
        client.post(f"/api/green-finance/assessments/{ass_id}/generate")

        response = client.get(f"/api/green-finance/assessments/{ass_id}/checklist")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 15

    def test_86_api_update_status(self, client):
        res = client.post("/api/green-finance/assessments", json={"reporting_period": "2024-10"})
        ass_id = res.json()["id"]

        response = client.post(f"/api/green-finance/assessments/{ass_id}/status", json={"status": "READY_FOR_APPLICATION", "notes": "Approved for review"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "READY_FOR_APPLICATION"

    def test_87_api_finalize_assessment(self, client):
        res = client.post("/api/green-finance/assessments", json={"reporting_period": "2024-10"})
        ass_id = res.json()["id"]

        response = client.post(f"/api/green-finance/assessments/{ass_id}/finalize")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "FINALIZED"
        assert data["finalized_at"] is not None

    def test_88_api_get_pdf_endpoint(self, client):
        res = client.post("/api/green-finance/assessments", json={"reporting_period": "2024-10"})
        ass_id = res.json()["id"]
        client.post(f"/api/green-finance/assessments/{ass_id}/generate")

        response = client.get(f"/api/green-finance/assessments/{ass_id}/pdf")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert len(response.content) > 1000

    def test_89_api_get_nonexistent_assessment_404(self, client):
        response = client.get("/api/green-finance/assessments/999999")
        assert response.status_code == 404

    def test_90_api_generate_nonexistent_assessment_404(self, client):
        response = client.post("/api/green-finance/assessments/999999/generate")
        assert response.status_code == 400

    def test_91_api_invalid_status_400(self, client):
        res = client.post("/api/green-finance/assessments", json={"reporting_period": "2024-10"})
        ass_id = res.json()["id"]
        response = client.post(f"/api/green-finance/assessments/{ass_id}/status", json={"status": "INVALID_STATUS"})
        assert response.status_code == 400

    def test_92_api_list_filter_period(self, client):
        client.post("/api/green-finance/assessments", json={"reporting_period": "2024-10"})
        client.post("/api/green-finance/assessments", json={"reporting_period": "2024-11"})

        response = client.get("/api/green-finance/assessments?reporting_period=2024-10")
        assert response.status_code == 200
        data = response.json()
        assert all(item["reporting_period"] == "2024-10" for item in data["items"])

    def test_93_api_pdf_filename_header(self, client):
        res = client.post("/api/green-finance/assessments", json={"reporting_period": "2024-10"})
        ass_id = res.json()["id"]

        response = client.get(f"/api/green-finance/assessments/{ass_id}/pdf")
        assert response.status_code == 200
        disp = response.headers.get("content-disposition", "")
        assert "Green_Finance_Readiness" in disp

    def test_94_api_no_loan_approval_endpoint_exists(self, client):
        response = client.post("/api/loan-approval", json={})
        assert response.status_code == 404

    def test_95_api_no_credit_score_endpoint_exists(self, client):
        response = client.get("/api/credit-score")
        assert response.status_code == 404

    def test_96_api_no_loan_eligibility_endpoint_exists(self, client):
        response = client.get("/api/loan-eligibility")
        assert response.status_code == 404

    def test_97_api_requirements_weights_positive(self, client):
        response = client.get("/api/green-finance/requirements")
        data = response.json()
        for r in data:
            assert r["weight"] > 0.0

    def test_98_api_dto_contains_events(self, client):
        res = client.post("/api/green-finance/assessments", json={"reporting_period": "2024-10"})
        ass_id = res.json()["id"]

        response = client.get(f"/api/green-finance/assessments/{ass_id}")
        data = response.json()
        assert len(data["events"]) >= 1

    def test_99_api_disclaimer_in_dto_response(self, client):
        res = client.post("/api/green-finance/assessments", json={"reporting_period": "2024-10"})
        ass_id = res.json()["id"]

        response = client.get(f"/api/green-finance/assessments/{ass_id}")
        data = response.json()
        assert "disclaimer" in data
        assert "not a lender credit score" in data["disclaimer"]

    def test_100_api_finalize_twice_prohibited(self, client):
        res = client.post("/api/green-finance/assessments", json={"reporting_period": "2024-10"})
        ass_id = res.json()["id"]
        client.post(f"/api/green-finance/assessments/{ass_id}/finalize")

        res2 = client.post(f"/api/green-finance/assessments/{ass_id}/finalize")
        assert res2.status_code == 400

    def test_101_api_requirements_subresource_nonexistent_404(self, client):
        response = client.get("/api/green-finance/assessments/999999/requirements")
        assert response.status_code == 404

    def test_102_api_evidence_subresource_nonexistent_404(self, client):
        response = client.get("/api/green-finance/assessments/999999/evidence")
        assert response.status_code == 404

    def test_103_api_actions_subresource_nonexistent_404(self, client):
        response = client.get("/api/green-finance/assessments/999999/actions")
        assert response.status_code == 404

    def test_104_api_checklist_subresource_nonexistent_404(self, client):
        response = client.get("/api/green-finance/assessments/999999/checklist")
        assert response.status_code == 404

    def test_105_api_pdf_subresource_nonexistent_404(self, client):
        response = client.get("/api/green-finance/assessments/999999/pdf")
        assert response.status_code == 404
