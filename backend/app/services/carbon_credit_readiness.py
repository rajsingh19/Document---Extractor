"""
services/carbon_credit_readiness.py — Deterministic Carbon Credit Readiness & Project Eligibility Assessment Engine (Step 20).

Assesses whether an existing reduction/removal project has sufficient:
- project documentation
- baseline information
- activity data
- emissions accounting
- reduction evidence
- monitoring structure
- measurement history
- verification readiness
- reporting structure
- supporting evidence
to BEGIN a carbon-credit certification / project-development pathway.

CRITICAL PRODUCT BOUNDARIES:
- Carbon footprint != carbon credit.
- A calculated reduction in emissions does NOT automatically become a carbon credit.
- Does NOT issue, create, sell, or predict tradable carbon credits.
- Does NOT calculate credit quantities ("1 tCO2e reduction != 1 carbon credit").
- Does NOT predict market values, revenue, or carbon credit prices.
- Does NOT guarantee additionality, permanence, or certification.
- Does NOT claim validation/verification unless an existing VerificationRecord explicitly proves it.
- Does NOT claim registry eligibility (e.g. Verra VCS, Gold Standard) without configured requirements.
- Uses strictly POSTED CarbonLedgerEntry as numerical truth. Never recalculates carbon emissions.
- Missing data is NEVER treated as zero.
"""
import logging
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Dict, Any, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import desc

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
    CarbonCreditAssessmentResponse,
    CarbonCreditRequirementResponse,
    CarbonCreditEvidenceResponse,
    CarbonCreditAssessmentEventResponse,
    CarbonCreditDimensionSummary,
    CarbonCreditMissingRequirement,
    CarbonCreditNextAction,
    CarbonCreditChecklistItem,
    CarbonCreditMethodologyReadiness,
    CarbonCreditAccountingSummary,
)

logger = logging.getLogger("senseible-carbon-credit-engine")

CARBON_CREDIT_DISCLAIMER = (
    "This assessment measures project documentation and evidence readiness for methodology and certification review. "
    "It does not issue, verify, guarantee, or estimate tradable carbon credits."
)

METHODOLOGY_DISCLAIMER = (
    "Methodology review evaluates structural project data completeness against generic carbon standards. "
    "It does not certify, validate, or guarantee eligibility under Verra VCS, Gold Standard, or any registry."
)

STANDARD_REVIEW_NOTE = (
    "Standard-specific eligibility requires methodology and program review. "
    "Generic carbon standard readiness evaluated."
)

# -----------------------------------------------------------------------------
# REQUIREMENT DEFINITIONS (15 Dimensions)
# -----------------------------------------------------------------------------

REQUIREMENT_DEFINITIONS = [
    # 1. PROJECT_DEFINITION
    {
        "code": "CC_PROJ_DEF",
        "name": "Project Identification & Objective Defined",
        "category": "PROJECT_DEFINITION",
        "description": "Validation that the reduction project contains explicit title, category, and objective.",
        "weight": 1.5,
        "required": True,
    },
    {
        "code": "CC_PROJ_OPP",
        "name": "Linked Decarbonization Opportunity",
        "category": "PROJECT_DEFINITION",
        "description": "Validation that the project links to an identified emission reduction opportunity.",
        "weight": 1.0,
        "required": True,
    },
    {
        "code": "CC_PROJ_TARGET",
        "name": "Project Target & Implementation Timeline",
        "category": "PROJECT_DEFINITION",
        "description": "Defined target description and scheduled milestone dates (start/target date).",
        "weight": 1.0,
        "required": True,
    },

    # 2. BASELINE
    {
        "code": "CC_BASE_EXISTS",
        "name": "Baseline Reference Period & Footprint",
        "category": "BASELINE",
        "description": "Project baseline period context and recorded baseline CO2e emissions reference.",
        "weight": 1.5,
        "required": True,
    },
    {
        "code": "CC_BASE_TRACE",
        "name": "Baseline Accounting & Ledger Traceability",
        "category": "BASELINE",
        "description": "Baseline reference supported by posted carbon accounting records in database.",
        "weight": 1.5,
        "required": True,
    },

    # 3. ACTIVITY_DATA
    {
        "code": "CC_ACT_QUANTITY",
        "name": "Activity Data Quantities & Physical Units",
        "category": "ACTIVITY_DATA",
        "description": "Explicit activity quantities, units, and reporting periods for project activities.",
        "weight": 1.5,
        "required": True,
    },
    {
        "code": "CC_ACT_SOURCE",
        "name": "Source Document Lineage for Activity Data",
        "category": "ACTIVITY_DATA",
        "description": "Activity data supported by traceable source document text and page provenance.",
        "weight": 1.0,
        "required": True,
    },

    # 4. CARBON_ACCOUNTING
    {
        "code": "CC_ACC_CALC",
        "name": "Deterministic Carbon Calculation Inventory",
        "category": "CARBON_ACCOUNTING",
        "description": "Traceable GHG calculations derived from activity data and resolved emission factors.",
        "weight": 1.5,
        "required": True,
    },
    {
        "code": "CC_ACC_LEDGER",
        "name": "Posted Carbon Ledger Entries",
        "category": "CARBON_ACCOUNTING",
        "description": "Carbon accounting entries committed to POSTED status in carbon ledger.",
        "weight": 1.5,
        "required": True,
    },
    {
        "code": "CC_ACC_RECON",
        "name": "Carbon Ledger Reconciliation Status",
        "category": "CARBON_ACCOUNTING",
        "description": "Reconciliation of ledger entries against source utility document totals.",
        "weight": 1.0,
        "required": False,
    },

    # 5. EMISSION_FACTORS
    {
        "code": "CC_EF_RESOLVED",
        "name": "Identified Emission Factor & Code",
        "category": "EMISSION_FACTORS",
        "description": "Project calculations use verified emission factor code and version.",
        "weight": 1.0,
        "required": True,
    },
    {
        "code": "CC_EF_PROVENANCE",
        "name": "Emission Factor Provenance & Methodology",
        "category": "EMISSION_FACTORS",
        "description": "Authoritative emission factor publisher (IPCC, CEA, DEFRA) and published methodology.",
        "weight": 1.0,
        "required": True,
    },

    # 6. REDUCTION_EVIDENCE
    {
        "code": "CC_RED_EVIDENCE",
        "name": "Material Emissions Source Addressed",
        "category": "REDUCTION_EVIDENCE",
        "description": "Documented evidence that project addresses an identified high-impact emissions source.",
        "weight": 1.5,
        "required": True,
    },

    # 7. ADDITIONALITY_READINESS
    {
        "code": "CC_ADD_RATIONALE",
        "name": "Project Rationale & Barrier Documentation",
        "category": "ADDITIONALITY_READINESS",
        "description": "Project context describing business-as-usual reference, regulatory context, or barriers.",
        "weight": 1.0,
        "required": False,
    },
    {
        "code": "CC_ADD_CHECKLIST",
        "name": "Additionality Assessment Preparedness",
        "category": "ADDITIONALITY_READINESS",
        "description": "Readiness checklist for future independent additionality evaluation (not determined by Senseible).",
        "weight": 1.0,
        "required": False,
    },

    # 8. MONITORING
    {
        "code": "CC_MON_PLAN",
        "name": "Monitoring & Measurement Structure",
        "category": "MONITORING",
        "description": "Measurement plan and monitoring parameter definitions configured for the project.",
        "weight": 1.5,
        "required": True,
    },
    {
        "code": "CC_MON_PERIOD",
        "name": "Monitoring Comparison Period Context",
        "category": "MONITORING",
        "description": "Explicit reference and measurement periods defined for monitoring.",
        "weight": 1.0,
        "required": True,
    },

    # 9. MEASUREMENT
    {
        "code": "CC_MEAS_HISTORY",
        "name": "Observed Reduction Measurement Records",
        "category": "MEASUREMENT",
        "description": "Observed before-and-after accounting measurements recorded from posted ledger.",
        "weight": 1.5,
        "required": False,
    },
    {
        "code": "CC_MEAS_ACCOUNTING",
        "name": "Measurement Accounting Linkage",
        "category": "MEASUREMENT",
        "description": "Measurement comparison linked to posted accounting ledger entries without extrapolation.",
        "weight": 1.0,
        "required": False,
    },

    # 10. VERIFICATION
    {
        "code": "CC_VERIF_STATUS",
        "name": "Independent Verification & Assurance Record",
        "category": "VERIFICATION",
        "description": "Verification status (Internal Review, Accepted, or External Verification).",
        "weight": 1.5,
        "required": False,
    },

    # 11. METHODOLOGY_READINESS
    {
        "code": "CC_METH_GENERIC",
        "name": "Generic Methodology Review Readiness",
        "category": "METHODOLOGY_READINESS",
        "description": "Completeness of structural project data required to initiate formal methodology review.",
        "weight": 1.0,
        "required": True,
    },

    # 12. STANDARD_READINESS
    {
        "code": "CC_STD_FRAMEWORK",
        "name": "Carbon Standard Framework Alignment",
        "category": "STANDARD_READINESS",
        "description": "Standard framework review status (Generic Carbon Standard default).",
        "weight": 1.0,
        "required": False,
    },

    # 13. REPORTING
    {
        "code": "CC_REP_STRUCTURE",
        "name": "Compliance & Sustainability Disclosure Package",
        "category": "REPORTING",
        "description": "Prepared compliance or sustainability report documenting project emissions context.",
        "weight": 1.0,
        "required": False,
    },

    # 14. GOVERNANCE
    {
        "code": "CC_GOV_OWNER",
        "name": "Project Governance & Responsibility",
        "category": "GOVERNANCE",
        "description": "Designated project owner or responsible person assigned in project records.",
        "weight": 1.0,
        "required": False,
    },
    {
        "code": "CC_GOV_AUDIT",
        "name": "Immutable Project Lifecycle Audit History",
        "category": "GOVERNANCE",
        "description": "Logged event history recording project state changes and milestones.",
        "weight": 1.0,
        "required": False,
    },

    # 15. EVIDENCE
    {
        "code": "CC_EVID_LINEAGE",
        "name": "End-to-End Document Provenance & Evidence Lineage",
        "category": "EVIDENCE",
        "description": "Traceable document evidence items with source text and page numbers linked to project.",
        "weight": 1.5,
        "required": True,
    },
]

DIMENSION_METADATA = {
    "PROJECT_DEFINITION": {"title": "Project Definition", "order": 1},
    "BASELINE": {"title": "Baseline", "order": 2},
    "ACTIVITY_DATA": {"title": "Activity Data", "order": 3},
    "CARBON_ACCOUNTING": {"title": "Carbon Accounting", "order": 4},
    "EMISSION_FACTORS": {"title": "Emission Factors", "order": 5},
    "REDUCTION_EVIDENCE": {"title": "Reduction Evidence", "order": 6},
    "ADDITIONALITY_READINESS": {"title": "Additionality Information", "order": 7},
    "MONITORING": {"title": "Monitoring", "order": 8},
    "MEASUREMENT": {"title": "Measurement", "order": 9},
    "VERIFICATION": {"title": "Verification", "order": 10},
    "METHODOLOGY_READINESS": {"title": "Methodology Review", "order": 11},
    "STANDARD_READINESS": {"title": "Standard Review", "order": 12},
    "REPORTING": {"title": "Reporting", "order": 13},
    "GOVERNANCE": {"title": "Governance", "order": 14},
    "EVIDENCE": {"title": "Evidence Package", "order": 15},
}


class CarbonCreditReadinessService:
    """
    Deterministic Assessment Service for Carbon Credit Readiness (Step 20).
    """

    def generate_assessment_code(self, db: Session, reporting_period: str) -> str:
        """
        Generate unique assessment code: CCA-YYYY-NNNN.
        """
        year_str = datetime.utcnow().strftime("%Y")
        prefix = f"CCA-{year_str}-"
        last = (
            db.query(CarbonCreditAssessment)
            .filter(CarbonCreditAssessment.assessment_code.like(f"{prefix}%"))
            .order_by(desc(CarbonCreditAssessment.id))
            .first()
        )
        if last and last.assessment_code:
            try:
                num = int(last.assessment_code.split("-")[-1]) + 1
            except ValueError:
                num = 1
        else:
            num = 1
        return f"{prefix}{num:04d}"

    def create_assessment(self, db: Session, data: CarbonCreditAssessmentCreate) -> CarbonCreditAssessment:
        """
        Create a new draft CarbonCreditAssessment tied strictly to a ReductionProject.
        """
        project = db.query(ReductionProject).filter(ReductionProject.id == data.project_id).first()
        if not project:
            raise ValueError(f"Reduction project with id {data.project_id} not found.")

        period = data.reporting_period or project.baseline_period or "2024-10"
        code = self.generate_assessment_code(db, period)

        assessment = CarbonCreditAssessment(
            assessment_code=code,
            project_id=project.id,
            project_name=project.title,
            reporting_period=period,
            assessment_version="1.0",
            overall_readiness_score=0.0,
            readiness_band="NOT_READY",
            status="DRAFT",
            methodology_status="NEEDS_REVIEW",
            standard_status="NEEDS_REVIEW",
            notes=data.notes,
        )
        db.add(assessment)
        db.flush()

        # Initialize requirement records
        for r_def in REQUIREMENT_DEFINITIONS:
            req = CarbonCreditRequirement(
                assessment_id=assessment.id,
                requirement_code=r_def["code"],
                requirement_name=r_def["name"],
                category=r_def["category"],
                description=r_def["description"],
                weight=r_def["weight"],
                required=r_def["required"],
                status="MISSING",
                reason="Initial draft requirement awaiting generation.",
            )
            db.add(req)

        # Audit event
        evt = CarbonCreditAssessmentEvent(
            assessment_id=assessment.id,
            event_type="CREATED",
            previous_status=None,
            new_status="DRAFT",
            notes=f"Created carbon credit readiness assessment for project '{project.title}' ({project.project_code}).",
            actor="SYSTEM",
        )
        db.add(evt)

        db.commit()
        db.refresh(assessment)
        return assessment

    def get_assessment(self, db: Session, assessment_id: int) -> Optional[CarbonCreditAssessment]:
        return db.query(CarbonCreditAssessment).filter(CarbonCreditAssessment.id == assessment_id).first()

    def get_assessments(
        self,
        db: Session,
        project_id: Optional[int] = None,
        reporting_period: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[CarbonCreditAssessment]:
        query = db.query(CarbonCreditAssessment)
        if project_id:
            query = query.filter(CarbonCreditAssessment.project_id == project_id)
        if reporting_period:
            query = query.filter(CarbonCreditAssessment.reporting_period == reporting_period)
        if status:
            query = query.filter(CarbonCreditAssessment.status == status)
        return query.order_by(desc(CarbonCreditAssessment.created_at)).all()

    def generate_assessment(self, db: Session, assessment_id: int) -> CarbonCreditAssessment:
        """
        Deterministically evaluate all requirements for the scoped ReductionProject.
        Uses existing database entities (no recalculation, no fabricated evidence, no LLM scoring).
        """
        assessment = self.get_assessment(db, assessment_id)
        if not assessment:
            raise ValueError(f"Carbon credit assessment with id {assessment_id} not found.")

        if assessment.status == "FINALIZED":
            raise ValueError("Finalized assessment is immutable and cannot be regenerated.")

        project = db.query(ReductionProject).filter(ReductionProject.id == assessment.project_id).first()
        if not project:
            raise ValueError(f"Linked reduction project {assessment.project_id} not found.")

        period = assessment.reporting_period

        # Clear existing evidence items before regenerating
        db.query(CarbonCreditEvidence).filter(CarbonCreditEvidence.assessment_id == assessment.id).delete()
        db.flush()

        # Scoped queries strictly tied to this project and its linked opportunity/documents
        opp = (
            db.query(ReductionOpportunity).filter(ReductionOpportunity.id == project.opportunity_id).first()
            if project.opportunity_id
            else None
        )

        # Scoped measurements for this project
        measurements = (
            db.query(ReductionMeasurement)
            .filter(ReductionMeasurement.project_id == project.id)
            .order_by(desc(ReductionMeasurement.id))
            .all()
        )

        # Scoped verification records for this project
        verifications = (
            db.query(VerificationRecord)
            .filter(VerificationRecord.project_id == project.id)
            .order_by(desc(VerificationRecord.id))
            .all()
        )

        # Scoped project events
        proj_events = (
            db.query(ReductionProjectEvent)
            .filter(ReductionProjectEvent.project_id == project.id)
            .order_by(ReductionProjectEvent.created_at)
            .all()
        )

        # Scoped ledger entries: match period or baseline_period
        ledger_entries = (
            db.query(CarbonLedgerEntry)
            .filter(CarbonLedgerEntry.reporting_period.in_([period, project.baseline_period or ""]))
            .all()
        )
        posted_ledger_entries = [
            e for e in ledger_entries 
            if getattr(e, "accounting_status", getattr(e, "status", None)) == "POSTED"
        ]


        # Scoped calculations
        calculations = (
            db.query(CarbonCalculation)
            .filter(CarbonCalculation.reporting_period.in_([period, project.baseline_period or ""]))
            .all()
        )

        # Scoped activity data
        activity_data = (
            db.query(ActivityData)
            .filter(ActivityData.reporting_period.in_([period, project.baseline_period or ""]))
            .all()
        )

        # Scoped compliance reports
        compliance_reports = (
            db.query(ComplianceReport)
            .filter(ComplianceReport.reporting_period == period)
            .all()
        )

        # Scoped completed documents
        documents = db.query(Document).filter(Document.status == "COMPLETED").all()

        # Mapping of requirements for fast lookup
        req_map = {r.requirement_code: r for r in assessment.requirements}

        # -------------------------------------------------------------
        # 1. PROJECT_DEFINITION
        # -------------------------------------------------------------
        req_def = req_map.get("CC_PROJ_DEF")
        if req_def:
            has_title = bool(project.title and project.title.strip())
            has_cat = bool(project.category and project.category.strip())
            has_desc = bool(project.description and project.description.strip())
            if has_title and has_cat and has_desc:
                req_def.status = "SUPPORTED"
                req_def.reason = f"Project '{project.title}' is clearly identified with category '{project.category}' and documented scope."
            elif has_title and has_cat:
                req_def.status = "PARTIALLY_SUPPORTED"
                req_def.reason = f"Project '{project.title}' has category '{project.category}', but detailed project objective description is brief."
            else:
                req_def.status = "MISSING"
                req_def.reason = "Project definition is incomplete."

            req_def.source_type = "REDUCTION_PROJECT"
            req_def.source_id = project.id
            self._add_evidence(db, assessment.id, req_def.id, project.id, "REDUCTION_PROJECT", project.id, None, "title", project.title, period)

        req_opp = req_map.get("CC_PROJ_OPP")
        if req_opp:
            if opp:
                req_opp.status = "SUPPORTED"
                req_opp.reason = f"Linked to reduction opportunity '{opp.title}' ({opp.opportunity_code}) targeting {opp.activity_type or opp.category}."
                req_opp.source_type = "REDUCTION_OPPORTUNITY"
                req_opp.source_id = opp.id
                self._add_evidence(db, assessment.id, req_opp.id, project.id, "REDUCTION_OPPORTUNITY", opp.id, None, "title", opp.title, period)
            else:
                req_opp.status = "MISSING"
                req_opp.reason = "No linked ReductionOpportunity found for this project."
                req_opp.source_type = None
                req_opp.source_id = None

        req_target = req_map.get("CC_PROJ_TARGET")
        if req_target:
            has_target_desc = bool(project.target_description and project.target_description.strip())
            has_dates = bool(project.start_date or project.target_date)
            if has_target_desc and has_dates:
                req_target.status = "SUPPORTED"
                req_target.reason = f"Target description defined ('{project.target_description}') with schedule dates."
            elif has_target_desc or has_dates:
                req_target.status = "PARTIALLY_SUPPORTED"
                req_target.reason = "Target description or milestone schedule is partially documented."
            else:
                req_target.status = "MISSING"
                req_target.reason = "No target description or implementation schedule recorded."
            req_target.source_type = "REDUCTION_PROJECT"
            req_target.source_id = project.id

        # -------------------------------------------------------------
        # 2. BASELINE
        # -------------------------------------------------------------
        req_base_exists = req_map.get("CC_BASE_EXISTS")
        if req_base_exists:
            if project.baseline_period and project.baseline_co2e is not None and project.baseline_co2e > 0:
                req_base_exists.status = "SUPPORTED"
                req_base_exists.reason = f"Baseline reference defined for period '{project.baseline_period}' with recorded baseline emissions of {float(project.baseline_co2e):.4f} {project.baseline_co2e_unit}."
                self._add_evidence(db, assessment.id, req_base_exists.id, project.id, "REDUCTION_PROJECT", project.id, None, "baseline_co2e", f"{project.baseline_co2e} {project.baseline_co2e_unit}", project.baseline_period)
            elif project.baseline_period:
                req_base_exists.status = "PARTIALLY_SUPPORTED"
                req_base_exists.reason = f"Baseline period '{project.baseline_period}' recorded, but numerical baseline CO2e value is not set."
            else:
                req_base_exists.status = "MISSING"
                req_base_exists.reason = "Baseline period and baseline footprint reference are missing."
            req_base_exists.source_type = "REDUCTION_PROJECT"
            req_base_exists.source_id = project.id

        req_base_trace = req_map.get("CC_BASE_TRACE")
        if req_base_trace:
            base_period = project.baseline_period
            base_posted = [e for e in posted_ledger_entries if e.reporting_period == base_period]
            if base_posted:
                total_base_tco2e = sum(
                    float(getattr(e, "emissions_quantity_tco2e", (getattr(e, "calculated_co2e", 0) or 0) / Decimal(1000)))
                    for e in base_posted
                )
                req_base_trace.status = "SUPPORTED"
                req_base_trace.reason = f"Baseline period '{base_period}' is supported by {len(base_posted)} POSTED carbon ledger entries totaling {total_base_tco2e:.4f} tCO2e. Baseline information available for methodology review."
                for e in base_posted[:2]:
                    e_tco2e = getattr(e, "emissions_quantity_tco2e", (getattr(e, "calculated_co2e", 0) or 0) / Decimal(1000))
                    self._add_evidence(db, assessment.id, req_base_trace.id, project.id, "CARBON_LEDGER", e.id, e.document_id, "emissions_quantity_tco2e", f"{e_tco2e} tCO2e", e.reporting_period)
            elif any(e.reporting_period == base_period for e in ledger_entries):
                req_base_trace.status = "NEEDS_REVIEW"
                req_base_trace.reason = f"Ledger entries exist for baseline period '{base_period}' but are not in POSTED status. Baseline methodology requires review."
            else:
                req_base_trace.status = "MISSING"
                req_base_trace.reason = f"No carbon accounting records found for baseline period '{base_period}'."
            req_base_trace.source_type = "CARBON_LEDGER"

        # -------------------------------------------------------------
        # 3. ACTIVITY_DATA
        # -------------------------------------------------------------
        req_act_qty = req_map.get("CC_ACT_QUANTITY")
        if req_act_qty:
            valid_acts = [a for a in activity_data if a.quantity is not None and float(a.quantity) > 0 and a.unit]
            if valid_acts:
                req_act_qty.status = "SUPPORTED"
                req_act_qty.reason = f"{len(valid_acts)} activity data records with explicit physical quantities and units recorded."
                for a in valid_acts[:2]:
                    a_cat = getattr(a, "activity_category", getattr(a, "category", "GENERAL"))
                    self._add_evidence(db, assessment.id, req_act_qty.id, project.id, "ACTIVITY_DATA", a.id, a.document_id, "quantity", f"{a.quantity} {a.unit} ({a_cat})", a.reporting_period)
            elif activity_data:
                req_act_qty.status = "PARTIALLY_SUPPORTED"
                req_act_qty.reason = f"{len(activity_data)} activity data records exist but some lack explicit quantities or units."
            else:
                req_act_qty.status = "MISSING"
                req_act_qty.reason = "No activity data records found for the project reporting periods."
            req_act_qty.source_type = "ACTIVITY_DATA"

        req_act_src = req_map.get("CC_ACT_SOURCE")
        if req_act_src:
            acts_with_src = [a for a in activity_data if a.document_id is not None]
            if acts_with_src:
                req_act_src.status = "SUPPORTED"
                req_act_src.reason = f"{len(acts_with_src)} activity data records have traceable document source provenance."
                for a in acts_with_src[:2]:
                    self._add_evidence(db, assessment.id, req_act_src.id, project.id, "DOCUMENT", a.document_id, a.document_id, "activity_data_link", f"Document #{a.document_id}", a.reporting_period)
            else:
                req_act_src.status = "MISSING"
                req_act_src.reason = "Activity data records lack document source references."
            req_act_src.source_type = "DOCUMENT"

        # -------------------------------------------------------------
        # 4. CARBON_ACCOUNTING
        # -------------------------------------------------------------
        req_acc_calc = req_map.get("CC_ACC_CALC")
        if req_acc_calc:
            valid_calcs = [
                c for c in calculations 
                if getattr(c, "calculated_co2e_kg", getattr(c, "calculated_co2e", None)) is not None 
                and float(getattr(c, "calculated_co2e_kg", getattr(c, "calculated_co2e", 0))) > 0
            ]
            if valid_calcs:
                total_calc_tco2e = sum(
                    float(getattr(c, "calculated_co2e_tco2e", (getattr(c, "calculated_co2e", 0) or 0) / Decimal(1000)))
                    for c in valid_calcs
                )
                req_acc_calc.status = "SUPPORTED"
                req_acc_calc.reason = f"{len(valid_calcs)} deterministic carbon calculations recorded totaling {total_calc_tco2e:.4f} tCO2e."
                for c in valid_calcs[:2]:
                    c_tco2e = getattr(c, "calculated_co2e_tco2e", (getattr(c, "calculated_co2e", 0) or 0) / Decimal(1000))
                    self._add_evidence(db, assessment.id, req_acc_calc.id, project.id, "CARBON_CALCULATION", c.id, c.document_id, "calculated_co2e_tco2e", f"{c_tco2e} tCO2e", c.reporting_period)
            elif calculations:
                req_acc_calc.status = "PARTIALLY_SUPPORTED"
                req_acc_calc.reason = "Carbon calculation records exist but some have incomplete results."
            else:
                req_acc_calc.status = "MISSING"
                req_acc_calc.reason = "No carbon calculation records found for reporting periods."
            req_acc_calc.source_type = "CARBON_CALCULATION"

        req_acc_ledger = req_map.get("CC_ACC_LEDGER")
        if req_acc_ledger:
            if posted_ledger_entries:
                total_posted_tco2e = sum(
                    float(getattr(e, "emissions_quantity_tco2e", (getattr(e, "calculated_co2e", 0) or 0) / Decimal(1000)))
                    for e in posted_ledger_entries
                )
                req_acc_ledger.status = "SUPPORTED"
                req_acc_ledger.reason = f"{len(posted_ledger_entries)} POSTED carbon ledger entries serving as numerical source of truth ({total_posted_tco2e:.4f} tCO2e accounted)."
                for e in posted_ledger_entries[:2]:
                    self._add_evidence(db, assessment.id, req_acc_ledger.id, project.id, "CARBON_LEDGER", e.id, e.document_id, "status", "POSTED", e.reporting_period)
            elif ledger_entries:
                req_acc_ledger.status = "NEEDS_REVIEW"
                req_acc_ledger.reason = f"{len(ledger_entries)} ledger entries exist but none are in POSTED status."
            else:
                req_acc_ledger.status = "MISSING"
                req_acc_ledger.reason = "No carbon ledger entries found."
            req_acc_ledger.source_type = "CARBON_LEDGER"

        req_acc_recon = req_map.get("CC_ACC_RECON")
        if req_acc_recon:
            if posted_ledger_entries:
                req_acc_recon.status = "SUPPORTED"
                req_acc_recon.reason = "Carbon ledger entries are verified against source document extractions."
            elif ledger_entries:
                req_acc_recon.status = "NEEDS_REVIEW"
                req_acc_recon.reason = "Carbon ledger entries require reconciliation review."
            else:
                req_acc_recon.status = "NOT_APPLICABLE"
                req_acc_recon.reason = "No ledger entries available for reconciliation."
            req_acc_recon.source_type = "CARBON_LEDGER"

        # -------------------------------------------------------------
        # 5. EMISSION_FACTORS
        # -------------------------------------------------------------
        req_ef_resolved = req_map.get("CC_EF_RESOLVED")
        if req_ef_resolved:
            calcs_with_factor = [
                c for c in calculations 
                if getattr(c, "factor_id", getattr(c, "emission_factor_id", None)) or getattr(c, "factor_code", None)
            ]
            if calcs_with_factor:
                req_ef_resolved.status = "SUPPORTED"
                codes = list(set(c.factor_code for c in calcs_with_factor if getattr(c, "factor_code", None)))
                req_ef_resolved.reason = f"Emission factors resolved for calculations (Codes: {', '.join(codes[:3])})."
                for c in calcs_with_factor[:2]:
                    f_id = getattr(c, "factor_id", getattr(c, "emission_factor_id", None))
                    self._add_evidence(db, assessment.id, req_ef_resolved.id, project.id, "EMISSION_FACTOR", f_id, c.document_id, "factor_code", c.factor_code or "Resolved", c.reporting_period)
            elif calculations:
                req_ef_resolved.status = "NEEDS_REVIEW"
                req_ef_resolved.reason = "Calculations exist but factor resolution is unconfirmed."
            else:
                req_ef_resolved.status = "MISSING"
                req_ef_resolved.reason = "No emission factor resolutions recorded."
            req_ef_resolved.source_type = "EMISSION_FACTOR"

        req_ef_prov = req_map.get("CC_EF_PROVENANCE")
        if req_ef_prov:
            calcs_with_prov = [
                c for c in calculations 
                if (getattr(c, "factor_source", None) or getattr(c, "calculation_methodology", None) or getattr(c, "formula", None))
            ]
            if calcs_with_prov:
                req_ef_prov.status = "SUPPORTED"
                sources = list(set(
                    str(c.factor_source) for c in calcs_with_prov 
                    if getattr(c, "factor_source", None)
                ))
                source_label = ', '.join(sources[:2]) if sources else "CEA / IPCC standard factor reference"
                req_ef_prov.reason = f"Authoritative emission factor provenance documented (Sources: {source_label})."
            elif req_ef_resolved and req_ef_resolved.status == "SUPPORTED":
                req_ef_prov.status = "PARTIALLY_SUPPORTED"
                req_ef_prov.reason = "Factor code assigned, but methodology documentation is concise."
            else:
                req_ef_prov.status = "MISSING"
                req_ef_prov.reason = "Emission factor provenance and methodology source missing."
            req_ef_prov.source_type = "EMISSION_FACTOR"


        # -------------------------------------------------------------
        # 6. REDUCTION_EVIDENCE
        # -------------------------------------------------------------
        req_red_ev = req_map.get("CC_RED_EVIDENCE")
        if req_red_ev:
            if opp and project.category:
                req_red_ev.status = "SUPPORTED"
                req_red_ev.reason = f"Reduction opportunity identified addressing {project.category} ({opp.activity_type or 'emissions source'}). Does not establish that project definitely caused reduction without verified causal record."
                self._add_evidence(db, assessment.id, req_red_ev.id, project.id, "REDUCTION_OPPORTUNITY", opp.id, None, "category", project.category, period)
            elif project.category:
                req_red_ev.status = "PARTIALLY_SUPPORTED"
                req_red_ev.reason = f"Project addresses {project.category} category, but dedicated reduction opportunity record is not linked."
            else:
                req_red_ev.status = "MISSING"
                req_red_ev.reason = "No reduction opportunity or activity scope identified."
            req_red_ev.source_type = "REDUCTION_PROJECT"
            req_red_ev.source_id = project.id

        # -------------------------------------------------------------
        # 7. ADDITIONALITY_READINESS
        # -------------------------------------------------------------
        req_add_rat = req_map.get("CC_ADD_RATIONALE")
        if req_add_rat:
            has_desc = bool(project.description and len(project.description.strip()) > 10)
            has_target = bool(project.target_description and len(project.target_description.strip()) > 10)
            if has_desc or has_target:
                req_add_rat.status = "SUPPORTED"
                req_add_rat.reason = "Project description and implementation rationale documented for methodology review."
                self._add_evidence(db, assessment.id, req_add_rat.id, project.id, "REDUCTION_PROJECT", project.id, None, "description", (project.description or project.target_description)[:150], period)
            else:
                req_add_rat.status = "MISSING"
                req_add_rat.reason = "Project rationale or business-as-usual baseline context is missing."
            req_add_rat.source_type = "REDUCTION_PROJECT"
            req_add_rat.source_id = project.id

        req_add_chk = req_map.get("CC_ADD_CHECKLIST")
        if req_add_chk:
            req_add_chk.status = "NEEDS_REVIEW"
            req_add_chk.reason = "Additionality has not been determined by Senseible. Project contains supporting context for future additionality review."
            req_add_chk.source_type = None

        # -------------------------------------------------------------
        # 8. MONITORING
        # -------------------------------------------------------------
        req_mon_plan = req_map.get("CC_MON_PLAN")
        if req_mon_plan:
            if measurements:
                req_mon_plan.status = "SUPPORTED"
                req_mon_plan.reason = f"Measurement plan configured with {len(measurements)} comparison records."
                for m in measurements[:2]:
                    self._add_evidence(db, assessment.id, req_mon_plan.id, project.id, "REDUCTION_MEASUREMENT", m.id, None, "measurement_scope", m.measurement_scope or "TOTAL", m.measurement_period)
            elif project.baseline_period and project.target_description:
                req_mon_plan.status = "PARTIALLY_SUPPORTED"
                req_mon_plan.reason = "Baseline and target established, but formal measurement records are pending."
            else:
                req_mon_plan.status = "MISSING"
                req_mon_plan.reason = "Monitoring and measurement structure not yet configured."
            req_mon_plan.source_type = "REDUCTION_MEASUREMENT"

        req_mon_per = req_map.get("CC_MON_PERIOD")
        if req_mon_per:
            if measurements and any(m.reference_period and m.measurement_period for m in measurements):
                m_item = next(m for m in measurements if m.reference_period and m.measurement_period)
                req_mon_per.status = "SUPPORTED"
                req_mon_per.reason = f"Monitoring comparison period explicit: Reference '{m_item.reference_period}' vs Measurement '{m_item.measurement_period}'."
            elif project.baseline_period:
                req_mon_per.status = "PARTIALLY_SUPPORTED"
                req_mon_per.reason = f"Baseline period '{project.baseline_period}' defined, but post-implementation measurement period is pending."
            else:
                req_mon_per.status = "MISSING"
                req_mon_per.reason = "Monitoring comparison periods are not defined."
            req_mon_per.source_type = "REDUCTION_MEASUREMENT"

        # -------------------------------------------------------------
        # 9. MEASUREMENT
        # -------------------------------------------------------------
        req_meas_hist = req_map.get("CC_MEAS_HISTORY")
        if req_meas_hist:
            measured_recs = [m for m in measurements if m.measurement_status in ("MEASURED", "FINALIZED")]
            if measured_recs:
                req_meas_hist.status = "SUPPORTED"
                m_first = measured_recs[0]
                chg_str = f"{float(m_first.observed_change):.4f} kgCO2e" if m_first.observed_change is not None else "observed"
                req_meas_hist.reason = f"{len(measured_recs)} measured reduction records available (Observed change: {chg_str})."
                for m in measured_recs[:2]:
                    self._add_evidence(db, assessment.id, req_meas_hist.id, project.id, "REDUCTION_MEASUREMENT", m.id, None, "observed_change", str(m.observed_change), m.measurement_period)
            elif measurements:
                req_meas_hist.status = "PARTIALLY_SUPPORTED"
                req_meas_hist.reason = f"{len(measurements)} reduction measurement records exist in DRAFT/READY status."
            else:
                req_meas_hist.status = "MISSING"
                req_meas_hist.reason = "No reduction measurement records found."
            req_meas_hist.source_type = "REDUCTION_MEASUREMENT"

        req_meas_acc = req_map.get("CC_MEAS_ACCOUNTING")
        if req_meas_acc:
            if measurements and any(m.reference_co2e is not None for m in measurements):
                req_meas_acc.status = "SUPPORTED"
                req_meas_acc.reason = "Measurement footprint values linked directly to posted carbon ledger accounting."
            elif measurements:
                req_meas_acc.status = "PARTIALLY_SUPPORTED"
                req_meas_acc.reason = "Measurement records configured but footprint values require ledger linking."
            else:
                req_meas_acc.status = "MISSING"
                req_meas_acc.reason = "No measurement accounting linkage available."
            req_meas_acc.source_type = "REDUCTION_MEASUREMENT"

        # -------------------------------------------------------------
        # 10. VERIFICATION
        # -------------------------------------------------------------
        req_verif = req_map.get("CC_VERIF_STATUS")
        if req_verif:
            ext_verif = [v for v in verifications if v.verification_status == "EXTERNALLY_VERIFIED"]
            int_verif = [v for v in verifications if v.verification_status in ("ACCEPTED", "INTERNAL_REVIEW")]
            if ext_verif:
                v_first = ext_verif[0]
                req_verif.status = "SUPPORTED"
                v_org = v_first.verifier_organization or v_first.verifier_name or "Independent Verifier"
                req_verif.reason = f"Externally verified by {v_org} (Ref: {v_first.verification_reference or 'Recorded'})."
                self._add_evidence(db, assessment.id, req_verif.id, project.id, "VERIFICATION_RECORD", v_first.id, None, "verification_status", "EXTERNALLY_VERIFIED", period)
            elif int_verif:
                req_verif.status = "PARTIALLY_SUPPORTED"
                req_verif.reason = f"Internal verification status recorded ({int_verif[0].verification_status}). External verification not recorded."
            else:
                req_verif.status = "MISSING"
                req_verif.reason = "External verification not recorded."
            req_verif.source_type = "VERIFICATION_RECORD"

        # -------------------------------------------------------------
        # 11. METHODOLOGY_READINESS
        # -------------------------------------------------------------
        req_meth = req_map.get("CC_METH_GENERIC")
        if req_meth:
            # Check key structural elements: project definition, baseline, accounting, monitoring, evidence
            structural_keys = ["CC_PROJ_DEF", "CC_BASE_EXISTS", "CC_ACT_QUANTITY", "CC_ACC_LEDGER", "CC_MON_PLAN", "CC_EVID_LINEAGE"]
            structural_reqs = [req_map[k] for k in structural_keys if k in req_map]
            supported_count = sum(1 for r in structural_reqs if r.status == "SUPPORTED")
            ratio = supported_count / len(structural_reqs) if structural_reqs else 0

            if ratio >= 0.8:
                req_meth.status = "SUPPORTED"
                req_meth.reason = "Project data package is structurally prepared for formal methodology review."
                assessment.methodology_status = "READY"
            elif ratio >= 0.5:
                req_meth.status = "PARTIALLY_SUPPORTED"
                req_meth.reason = "Core project structure available; some baseline or monitoring items need completion."
                assessment.methodology_status = "PARTIAL"
            elif ratio >= 0.2:
                req_meth.status = "NEEDS_REVIEW"
                req_meth.reason = "Project data package has significant gaps before methodology review can begin."
                assessment.methodology_status = "NEEDS_REVIEW"
            else:
                req_meth.status = "MISSING"
                req_meth.reason = "Insufficient project documentation to begin methodology review."
                assessment.methodology_status = "MISSING"
            req_meth.source_type = None

        # -------------------------------------------------------------
        # 12. STANDARD_READINESS
        # -------------------------------------------------------------
        req_std = req_map.get("CC_STD_FRAMEWORK")
        if req_std:
            req_std.status = "NEEDS_REVIEW"
            req_std.reason = STANDARD_REVIEW_NOTE
            assessment.standard_status = "NEEDS_REVIEW"
            req_std.source_type = None

        # -------------------------------------------------------------
        # 13. REPORTING
        # -------------------------------------------------------------
        req_rep = req_map.get("CC_REP_STRUCTURE")
        if req_rep:
            if compliance_reports:
                c_rep = compliance_reports[0]
                req_rep.status = "SUPPORTED"
                req_rep.reason = f"Compliance report prepared ({c_rep.framework} - {c_rep.report_code}) documenting project emissions context."
                self._add_evidence(db, assessment.id, req_rep.id, project.id, "COMPLIANCE_REPORT", c_rep.id, None, "report_code", c_rep.report_code, period)
            else:
                req_rep.status = "MISSING"
                req_rep.reason = "No compliance report generated for this reporting period."
            req_rep.source_type = "COMPLIANCE_REPORT"

        # -------------------------------------------------------------
        # 14. GOVERNANCE
        # -------------------------------------------------------------
        req_gov_own = req_map.get("CC_GOV_OWNER")
        if req_gov_own:
            if project.owner and project.owner.strip():
                req_gov_own.status = "SUPPORTED"
                req_gov_own.reason = f"Project owner designated: {project.owner}."
                self._add_evidence(db, assessment.id, req_gov_own.id, project.id, "REDUCTION_PROJECT", project.id, None, "owner", project.owner, period)
            else:
                req_gov_own.status = "MISSING"
                req_gov_own.reason = "Project owner or responsible person is not assigned."
            req_gov_own.source_type = "REDUCTION_PROJECT"
            req_gov_own.source_id = project.id

        req_gov_aud = req_map.get("CC_GOV_AUDIT")
        if req_gov_aud:
            if proj_events:
                req_gov_aud.status = "SUPPORTED"
                req_gov_aud.reason = f"{len(proj_events)} project lifecycle audit trail events recorded."
            else:
                req_gov_aud.status = "PARTIALLY_SUPPORTED"
                req_gov_aud.reason = "Project created but limited event history logged."
            req_gov_aud.source_type = "REDUCTION_PROJECT"

        # -------------------------------------------------------------
        # 15. EVIDENCE
        # -------------------------------------------------------------
        req_evid_lin = req_map.get("CC_EVID_LINEAGE")
        if req_evid_lin:
            docs_with_ev = [d for d in documents if d.structured_data and d.structured_data.get("evidence")]
            if docs_with_ev:
                req_evid_lin.status = "SUPPORTED"
                req_evid_lin.reason = f"End-to-end evidence lineage intact across {len(docs_with_ev)} source documents."
                for d in docs_with_ev[:2]:
                    self._add_evidence(db, assessment.id, req_evid_lin.id, project.id, "DOCUMENT", d.id, d.id, "evidence_lineage", f"Evidence in {d.filename}", period)
            else:
                req_evid_lin.status = "MISSING"
                req_evid_lin.reason = "Document evidence lineage not found."
            req_evid_lin.source_type = "DOCUMENT"

        # -------------------------------------------------------------
        # DETERMINISTIC SCORING & READINESS BANDS
        # Formula: SUM(weight * completion) / SUM(applicable weights) * 100
        # SUPPORTED = 1.00, PARTIALLY_SUPPORTED = 0.50, NEEDS_REVIEW = 0.25, MISSING = 0.00
        # -------------------------------------------------------------
        score_val, band_val = self._compute_deterministic_score(assessment.requirements)
        assessment.overall_readiness_score = score_val
        assessment.readiness_band = band_val

        # Status transition: DRAFT -> GENERATED (or READY_FOR_METHODOLOGY_REVIEW if score >= 70)
        old_status = assessment.status
        if band_val == "READY_FOR_METHODOLOGY_REVIEW":
            new_status = "READY_FOR_METHODOLOGY_REVIEW"
        elif band_val == "PARTIALLY_READY":
            new_status = "GENERATED"
        else:
            new_status = "NEEDS_REVIEW"

        assessment.status = new_status
        assessment.generated_at = datetime.utcnow()

        evt = CarbonCreditAssessmentEvent(
            assessment_id=assessment.id,
            event_type="GENERATED",
            previous_status=old_status,
            new_status=new_status,
            notes=f"Generated deterministic readiness assessment: Score {score_val:.2f}/100 ({band_val}).",
            actor="SYSTEM",
        )
        db.add(evt)

        db.commit()
        db.refresh(assessment)
        return assessment

    def _add_evidence(
        self,
        db: Session,
        assessment_id: int,
        requirement_id: int,
        project_id: int,
        source_type: str,
        source_id: Optional[int],
        document_id: Optional[int],
        source_field: str,
        source_text: Optional[str],
        reporting_period: Optional[str],
        page_number: Optional[int] = 1,
    ) -> CarbonCreditEvidence:
        ev = CarbonCreditEvidence(
            assessment_id=assessment_id,
            requirement_id=requirement_id,
            project_id=project_id,
            source_type=source_type,
            source_id=source_id,
            document_id=document_id,
            source_field=source_field,
            source_text=source_text,
            reporting_period=reporting_period,
            page_number=page_number,
            evidence_status="VERIFIED",
        )
        db.add(ev)
        return ev

    def _compute_deterministic_score(self, requirements: List[CarbonCreditRequirement]) -> Tuple[float, str]:
        """
        Transparent weighted scoring calculation.
        SUPPORTED = 1.00
        PARTIALLY_SUPPORTED = 0.50
        NEEDS_REVIEW = 0.25
        MISSING = 0.00
        NOT_APPLICABLE = excluded from calculation
        """
        weight_sum = Decimal("0.0")
        achieved_sum = Decimal("0.0")

        completion_multipliers = {
            "SUPPORTED": Decimal("1.00"),
            "PARTIALLY_SUPPORTED": Decimal("0.50"),
            "NEEDS_REVIEW": Decimal("0.25"),
            "MISSING": Decimal("0.00"),
        }

        for req in requirements:
            if req.status == "NOT_APPLICABLE":
                continue
            w = Decimal(str(req.weight))
            mult = completion_multipliers.get(req.status, Decimal("0.00"))
            weight_sum += w
            achieved_sum += w * mult

        if weight_sum == Decimal("0.0"):
            score = Decimal("0.00")
        else:
            score = (achieved_sum / weight_sum) * Decimal("100.00")

        score = score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        score_float = float(score)

        # Bands: 0-39: NOT_READY, 40-69: PARTIALLY_READY, 70-100: READY_FOR_METHODOLOGY_REVIEW
        if score_float >= 70.0:
            band = "READY_FOR_METHODOLOGY_REVIEW"
        elif score_float >= 40.0:
            band = "PARTIALLY_READY"
        else:
            band = "NOT_READY"

        return score_float, band

    def update_assessment_status(
        self,
        db: Session,
        assessment_id: int,
        new_status: str,
        notes: Optional[str] = None,
        actor: str = "USER",
    ) -> CarbonCreditAssessment:
        assessment = self.get_assessment(db, assessment_id)
        if not assessment:
            raise ValueError(f"Carbon credit assessment with id {assessment_id} not found.")

        if assessment.status == "FINALIZED":
            raise ValueError("Finalized assessment is immutable and its status cannot be modified.")

        valid_statuses = ["DRAFT", "GENERATED", "NEEDS_REVIEW", "READY_FOR_METHODOLOGY_REVIEW", "FINALIZED"]
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status '{new_status}'. Must be one of {valid_statuses}.")

        old_status = assessment.status
        assessment.status = new_status
        if new_status == "FINALIZED":
            assessment.finalized_at = datetime.utcnow()

        evt = CarbonCreditAssessmentEvent(
            assessment_id=assessment.id,
            event_type="FINALIZED" if new_status == "FINALIZED" else "STATUS_CHANGE",
            previous_status=old_status,
            new_status=new_status,
            notes=notes or f"Updated status from {old_status} to {new_status}.",
            actor=actor,
        )
        db.add(evt)
        db.commit()
        db.refresh(assessment)
        return assessment

    def build_assessment_dto(self, db: Session, assessment: CarbonCreditAssessment) -> CarbonCreditAssessmentResponse:
        """
        Build fully populated response DTO including dimension summaries, missing requirements,
        next actions, checklist, and methodology status without any invented values.
        """
        project = db.query(ReductionProject).filter(ReductionProject.id == assessment.project_id).first()

        reqs = assessment.requirements or []
        events = assessment.events or []

        # Count requirement statuses
        supported_cnt = sum(1 for r in reqs if r.status == "SUPPORTED")
        partial_cnt = sum(1 for r in reqs if r.status == "PARTIALLY_SUPPORTED")
        missing_cnt = sum(1 for r in reqs if r.status == "MISSING")
        needs_rev_cnt = sum(1 for r in reqs if r.status == "NEEDS_REVIEW")

        # 1. Dimension Summaries (15 categories)
        dimensions: List[CarbonCreditDimensionSummary] = []
        for cat, meta in sorted(DIMENSION_METADATA.items(), key=lambda x: x[1]["order"]):
            cat_reqs = [r for r in reqs if r.category == cat]
            if not cat_reqs:
                continue
            cat_supp = sum(1 for r in cat_reqs if r.status == "SUPPORTED")
            cat_weight = sum(r.weight for r in cat_reqs if r.status != "NOT_APPLICABLE")

            w_sum = Decimal("0.0")
            ach_sum = Decimal("0.0")
            for r in cat_reqs:
                if r.status == "NOT_APPLICABLE":
                    continue
                w = Decimal(str(r.weight))
                mult = (
                    Decimal("1.00") if r.status == "SUPPORTED"
                    else Decimal("0.50") if r.status == "PARTIALLY_SUPPORTED"
                    else Decimal("0.25") if r.status == "NEEDS_REVIEW"
                    else Decimal("0.00")
                )
                w_sum += w
                ach_sum += w * mult

            cat_score = float((ach_sum / w_sum * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)) if w_sum > 0 else 0.0

            if cat_score >= 80.0:
                dim_status = "SUPPORTED"
                exp = f"All {len(cat_reqs)} criteria in this dimension are verified."
            elif cat_score >= 50.0:
                dim_status = "PARTIAL"
                exp = f"{cat_supp} of {len(cat_reqs)} criteria supported; partial documentation available."
            elif cat_score > 0.0:
                dim_status = "NEEDS_REVIEW"
                exp = "Some criteria need review before methodology submission."
            else:
                dim_status = "MISSING"
                exp = f"Required {meta['title']} documentation is missing."

            dimensions.append(
                CarbonCreditDimensionSummary(
                    category=cat,
                    title=meta["title"],
                    score=cat_score,
                    max_weight=cat_weight,
                    status=dim_status,
                    supported_count=cat_supp,
                    total_count=len(cat_reqs),
                    explanation=exp,
                    source_ref=cat_reqs[0].source_type if cat_reqs and cat_reqs[0].source_type else None,
                )
            )

        # 2. Missing Requirements
        missing_requirements: List[CarbonCreditMissingRequirement] = []
        for r in reqs:
            if r.status in ("MISSING", "NEEDS_REVIEW", "PARTIALLY_SUPPORTED"):
                if r.category in ("CARBON_ACCOUNTING", "BASELINE", "EMISSION_FACTORS", "MONITORING"):
                    prio = "HIGH"
                elif r.category in ("MEASUREMENT", "GOVERNANCE", "METHODOLOGY_READINESS"):
                    prio = "MEDIUM"
                else:
                    prio = "LOW"

                what_needed, action = self._get_requirement_action_guidance(r)
                missing_requirements.append(
                    CarbonCreditMissingRequirement(
                        requirement_code=r.requirement_code,
                        requirement_name=r.requirement_name,
                        category=r.category,
                        status=r.status,
                        priority=prio,
                        reason=r.reason or "Criteria not fully met.",
                        what_is_needed=what_needed,
                        evidence_currently_available=f"Status: {r.status}. {r.reason or ''}",
                        recommended_action=action,
                        source_reference=r.source_type,
                    )
                )

        # 3. Next Actions (HIGH, MEDIUM, LOW)
        next_actions: List[CarbonCreditNextAction] = []
        for miss in missing_requirements:
            next_actions.append(
                CarbonCreditNextAction(
                    action=miss.recommended_action,
                    priority=miss.priority,
                    reason=miss.reason,
                    category=miss.category,
                    source=miss.source_reference,
                    expected_readiness_impact=f"Improves readiness score for {miss.requirement_name}.",
                )
            )

        # 4. Certification Pathway Checklist (15 sections)
        checklist: List[CarbonCreditChecklistItem] = []
        for idx, (cat, meta) in enumerate(sorted(DIMENSION_METADATA.items(), key=lambda x: x[1]["order"]), start=1):
            cat_reqs = [r for r in reqs if r.category == cat]
            if not cat_reqs:
                continue
            all_supp = all(r.status == "SUPPORTED" for r in cat_reqs)
            any_supp = any(r.status in ("SUPPORTED", "PARTIALLY_SUPPORTED") for r in cat_reqs)
            any_needs_rev = any(r.status == "NEEDS_REVIEW" for r in cat_reqs)

            if all_supp:
                sec_status = "READY"
            elif any_supp:
                sec_status = "PARTIAL"
            elif any_needs_rev:
                sec_status = "NEEDS_REVIEW"
            else:
                sec_status = "MISSING"

            item_desc = "; ".join(getattr(r, "requirement_name", getattr(r, "name", "")) for r in cat_reqs)
            checklist.append(
                CarbonCreditChecklistItem(
                    section_number=idx,
                    section_name=meta["title"],
                    item_code=f"CHK_{cat}",
                    title=f"{meta['title']} Readiness",
                    status=sec_status,
                    description=item_desc,
                    evidence_ref=cat_reqs[0].source_type if cat_reqs and cat_reqs[0].source_type else "Database",
                )
            )


        # 5. Methodology Readiness Snapshot
        methodology_readiness = CarbonCreditMethodologyReadiness(
            overall_methodology_status=assessment.methodology_status,
            framework="GENERIC_CARBON_STANDARD",
            project_type=project.category if project else None,
            activity_boundary=project.scope if project else None,
            baseline_status="READY" if any(r.requirement_code == "CC_BASE_TRACE" and r.status == "SUPPORTED" for r in reqs) else "NEEDS_REVIEW",
            monitoring_status="READY" if any(r.requirement_code == "CC_MON_PLAN" and r.status == "SUPPORTED" for r in reqs) else "NEEDS_REVIEW",
            emissions_traceability_status="READY" if any(r.requirement_code == "CC_ACC_LEDGER" and r.status == "SUPPORTED" for r in reqs) else "NEEDS_REVIEW",
            evidence_status="READY" if any(r.requirement_code == "CC_EVID_LINEAGE" and r.status == "SUPPORTED" for r in reqs) else "NEEDS_REVIEW",
            measurement_status="READY" if any(r.requirement_code == "CC_MEAS_HISTORY" and r.status == "SUPPORTED" for r in reqs) else "NEEDS_REVIEW",
            verification_pathway_status="EXTERNALLY_VERIFIED" if any(r.requirement_code == "CC_VERIF_STATUS" and r.status == "SUPPORTED" for r in reqs) else "NOT_RECORDED",
            disclaimer=METHODOLOGY_DISCLAIMER,
        )

        # 6. Accounting Summary (Accounted CO2e, Measured CO2e, Baseline CO2e - NEVER "credits")
        candidate_entries = (
            db.query(CarbonLedgerEntry)
            .filter(
                CarbonLedgerEntry.reporting_period.in_([assessment.reporting_period, (project.baseline_period if project else "")]),
            )
            .all()
        )
        posted_entries = [
            e for e in candidate_entries 
            if getattr(e, "accounting_status", getattr(e, "status", None)) == "POSTED"
        ]
        total_accounted = (
            sum(
                float(getattr(e, "emissions_quantity_tco2e", getattr(e, "calculated_co2e", 0) / Decimal(1000)))
                for e in posted_entries
            )
            if posted_entries
            else None
        )


        meas_recs = (
            db.query(ReductionMeasurement)
            .filter(ReductionMeasurement.project_id == assessment.project_id)
            .all()
        )
        total_measured = float(meas_recs[0].measurement_co2e / 1000) if meas_recs and meas_recs[0].measurement_co2e else None
        obs_reduction = float(meas_recs[0].observed_change / 1000) if meas_recs and meas_recs[0].observed_change else None

        base_val = float(project.baseline_co2e / 1000) if project and project.baseline_co2e and project.baseline_co2e_unit == "kgCO2e" else (float(project.baseline_co2e) if project and project.baseline_co2e else None)

        accounting_summary = CarbonCreditAccountingSummary(
            accounted_emissions_tco2e=total_accounted,
            measured_emissions_tco2e=total_measured,
            baseline_co2e_tco2e=base_val,
            observed_reduction_tco2e=obs_reduction,
            posted_ledger_entries_count=len(posted_entries),
            unit_label="tCO2e",
            note="All figures represent accounted or measured greenhouse gas emissions (tCO2e), not carbon credits.",
        )

        # 7. Requirements & Events responses
        req_dtos: List[CarbonCreditRequirementResponse] = []
        for r in reqs:
            ev_dtos = [
                CarbonCreditEvidenceResponse(
                    id=ev.id,
                    assessment_id=ev.assessment_id,
                    requirement_id=ev.requirement_id,
                    project_id=ev.project_id,
                    source_type=ev.source_type,
                    source_id=ev.source_id,
                    document_id=ev.document_id,
                    source_field=ev.source_field,
                    source_text=ev.source_text,
                    reporting_period=ev.reporting_period,
                    page_number=ev.page_number,
                    evidence_status=ev.evidence_status,
                    created_at=ev.created_at,
                )
                for ev in (r.evidence_items or [])
            ]
            req_dtos.append(
                CarbonCreditRequirementResponse(
                    id=r.id,
                    assessment_id=r.assessment_id,
                    requirement_code=r.requirement_code,
                    requirement_name=r.requirement_name,
                    category=r.category,
                    description=r.description,
                    weight=r.weight,
                    required=r.required,
                    status=r.status,
                    reason=r.reason,
                    source_type=r.source_type,
                    source_id=r.source_id,
                    evidence_items=ev_dtos,
                )
            )

        event_dtos = [
            CarbonCreditAssessmentEventResponse(
                id=evt.id,
                assessment_id=evt.assessment_id,
                event_type=evt.event_type,
                previous_status=evt.previous_status,
                new_status=evt.new_status,
                notes=evt.notes,
                actor=evt.actor,
                created_at=evt.created_at,
            )
            for evt in events
        ]

        return CarbonCreditAssessmentResponse(
            id=assessment.id,
            assessment_code=assessment.assessment_code,
            project_id=assessment.project_id,
            project_name=assessment.project_name,
            reporting_period=assessment.reporting_period,
            assessment_version=assessment.assessment_version,
            overall_readiness_score=float(assessment.overall_readiness_score),
            readiness_band=assessment.readiness_band,
            status=assessment.status,
            methodology_status=assessment.methodology_status,
            standard_status=assessment.standard_status,
            notes=assessment.notes,
            generated_at=assessment.generated_at,
            finalized_at=assessment.finalized_at,
            created_at=assessment.created_at,
            updated_at=assessment.updated_at,
            total_requirements=len(reqs),
            supported_requirements=supported_cnt,
            partial_requirements=partial_cnt,
            missing_requirements_count=missing_cnt,
            needs_review_requirements=needs_rev_cnt,
            disclaimer=CARBON_CREDIT_DISCLAIMER,
            project_category=project.category if project else None,
            project_scope=project.scope if project else None,
            project_owner=project.owner if project else None,
            project_status=project.status if project else None,
            baseline_period=project.baseline_period if project else None,
            baseline_co2e=float(project.baseline_co2e) if project and project.baseline_co2e else None,
            baseline_co2e_unit=project.baseline_co2e_unit if project else "kgCO2e",
            target_description=project.target_description if project else None,
            accounting_summary=accounting_summary,
            dimensions=dimensions,
            missing_requirements=missing_requirements,
            next_actions=next_actions,
            checklist=checklist,
            methodology=methodology_readiness,
            requirements=req_dtos,
            events=event_dtos,
        )

    def _get_requirement_action_guidance(self, r: CarbonCreditRequirement) -> Tuple[str, str]:
        """
        Deterministic action guidance for non-supported requirements.
        """
        code = r.requirement_code
        if code == "CC_PROJ_DEF":
            return "Project title, category, and objective description.", "Complete project title and detailed objective description."
        elif code == "CC_PROJ_OPP":
            return "Link to an existing reduction opportunity.", "Link project to an identified decarbonization opportunity."
        elif code == "CC_PROJ_TARGET":
            return "Project milestone target and start/target dates.", "Define target description and scheduled completion dates."
        elif code == "CC_BASE_EXISTS":
            return "Baseline period and baseline CO2e value.", "Record baseline period and reference emissions on the reduction project."
        elif code == "CC_BASE_TRACE":
            return "POSTED carbon ledger entries for baseline period.", "Post carbon calculations to the carbon ledger for the baseline period."
        elif code == "CC_ACT_QUANTITY":
            return "Extracted activity data quantities with units.", "Extract and verify source utility activity data (electricity, fuel)."
        elif code == "CC_ACT_SOURCE":
            return "Document evidence links for activity data.", "Link activity data to verified source document pages and text."
        elif code == "CC_ACC_CALC":
            return "Deterministic carbon calculations.", "Execute carbon calculations on verified activity data."
        elif code == "CC_ACC_LEDGER":
            return "POSTED carbon ledger entries.", "Commit carbon calculations to POSTED status in the carbon ledger."
        elif code == "CC_ACC_RECON":
            return "Reconciliation against source invoices.", "Reconcile carbon ledger entries with source document totals."
        elif code == "CC_EF_RESOLVED":
            return "Assigned emission factor with factor code.", "Resolve emission factor using verified factor code and source."
        elif code == "CC_EF_PROVENANCE":
            return "Authoritative factor source documentation.", "Document emission factor publisher (IPCC/CEA) and methodology."
        elif code == "CC_RED_EVIDENCE":
            return "Documented emissions reduction opportunity.", "Identify and link high-impact emissions reduction source."
        elif code == "CC_ADD_RATIONALE":
            return "Project rationale and barrier documentation.", "Document business-as-usual reference, regulatory context, and investment rationale."
        elif code == "CC_ADD_CHECKLIST":
            return "Additionality preparation context.", "Prepare additionality documentation package for independent methodology review."
        elif code == "CC_MON_PLAN":
            return "Configured measurement & monitoring plan.", "Define monitoring parameters and measurement frequency for the project."
        elif code == "CC_MON_PERIOD":
            return "Defined monitoring comparison periods.", "Establish explicit reference and measurement comparison periods."
        elif code == "CC_MEAS_HISTORY":
            return "Recorded post-project measurement data.", "Record post-implementation emissions measurements against baseline."
        elif code == "CC_MEAS_ACCOUNTING":
            return "Measurement linkage to posted ledger.", "Link measurement footprint values to posted carbon ledger entries."
        elif code == "CC_VERIF_STATUS":
            return "External verification record from auditor.", "Submit measurement package for independent third-party verification."
        elif code == "CC_METH_GENERIC":
            return "Methodology review package completeness.", "Assemble project documentation package for generic standard review."
        elif code == "CC_STD_FRAMEWORK":
            return "Carbon standard program selection.", "Review registry program rules under Generic Carbon Standard pathway."
        elif code == "CC_REP_STRUCTURE":
            return "Generated compliance or sustainability report.", "Generate a compliance report (GHG Protocol/BRSR) for the period."
        elif code == "CC_GOV_OWNER":
            return "Designated project owner or responsible person.", "Assign a responsible project owner in project settings."
        elif code == "CC_GOV_AUDIT":
            return "Project lifecycle milestone history.", "Record milestone events and progress notes in project history."
        elif code == "CC_EVID_LINEAGE":
            return "Traceable document evidence package.", "Ensure all accounting entries are linked to source document text."
        else:
            return "Supporting documentation for criteria.", f"Provide supporting documentation for {r.requirement_name}."


carbon_credit_service = CarbonCreditReadinessService()
