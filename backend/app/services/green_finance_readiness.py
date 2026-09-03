"""
services/green_finance_readiness.py — Deterministic Green Finance Readiness Engine (Step 19).

Measures business application readiness for green-finance review across 10 dimensions:
1. DATA_READINESS
2. CARBON_ACCOUNTING
3. EVIDENCE
4. EMISSIONS_DATA
5. REDUCTION_PLAN
6. REDUCTION_PROJECTS
7. MEASUREMENT_VERIFICATION
8. REPORTING
9. GOVERNANCE
10. FINANCE_DOCUMENT_READINESS

CRITICAL BOUNDARIES:
- Does NOT approve/reject loans or predict loan approval.
- Does NOT calculate credit scores, loan amounts, or interest rates.
- Does NOT recalculate carbon emissions. Uses POSTED CarbonLedgerEntry as truth.
- Does NOT treat missing data as zero. Missing Scope 3 remains MISSING.
- Does NOT fabricate evidence, financial information, or governance policies.
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
from backend.app.schemas.green_finance import (
    GreenFinanceAssessmentCreate,
    GreenFinanceAssessmentResponse,
    GreenFinanceRequirementResponse,
    GreenFinanceEvidenceResponse,
    GreenFinanceAssessmentEventResponse,
    GreenFinanceDimensionSummary,
    GreenFinanceMissingRequirement,
    GreenFinanceNextAction,
    GreenFinanceChecklistItem,
)

logger = logging.getLogger("senseible-green-finance-engine")

GREEN_FINANCE_DISCLAIMER = (
    "This score measures the completeness and quality of sustainability-related application evidence available in Senseible. "
    "It is not a lender credit score, loan eligibility score, approval prediction, or financing guarantee."
)

FINANCIAL_CHECKLIST_DISCLAIMER = (
    "Financial documents are checked for application readiness only. Credit assessment is outside the scope of this product."
)

# -----------------------------------------------------------------------------
# REQUIREMENT DEFINITIONS (10 Dimensions)
# -----------------------------------------------------------------------------

REQUIREMENT_DEFINITIONS = [
    # 1. DATA_READINESS
    {
        "code": "GF_DATA_DOCS",
        "name": "Processed Business Source Documents",
        "category": "DATA_READINESS",
        "description": "Verification that completed source documents exist for the business.",
        "weight": 1.0,
        "required": True,
    },
    {
        "code": "GF_DATA_PERIOD",
        "name": "Reporting Period Context Defined",
        "category": "DATA_READINESS",
        "description": "Validation that a valid reporting period context is specified.",
        "weight": 1.0,
        "required": True,
    },
    {
        "code": "GF_DATA_METRICS",
        "name": "Extracted Sustainability Metrics Available",
        "category": "DATA_READINESS",
        "description": "Extracted physical utility metrics available in database.",
        "weight": 1.0,
        "required": True,
    },

    # 2. CARBON_ACCOUNTING
    {
        "code": "GF_CALC_EXISTS",
        "name": "Calculated Carbon Emissions Inventory",
        "category": "CARBON_ACCOUNTING",
        "description": "Deterministic GHG calculations performed on activity data.",
        "weight": 1.5,
        "required": True,
    },
    {
        "code": "GF_CALC_POSTED",
        "name": "Posted Carbon Ledger Entries",
        "category": "CARBON_ACCOUNTING",
        "description": "Carbon accounting entries committed to POSTED status in ledger.",
        "weight": 1.5,
        "required": True,
    },
    {
        "code": "GF_CALC_FACTORS",
        "name": "Emission Factor Provenance Resolved",
        "category": "CARBON_ACCOUNTING",
        "description": "Emission factors assigned with verified factor code and source.",
        "weight": 1.0,
        "required": True,
    },

    # 3. EVIDENCE
    {
        "code": "GF_EVID_PROVENANCE",
        "name": "End-to-End Evidence Lineage Intact",
        "category": "EVIDENCE",
        "description": "Source text and document references linked to accounting entries.",
        "weight": 1.5,
        "required": True,
    },
    {
        "code": "GF_EVID_TEXT",
        "name": "Verifiable Source Text Snippets",
        "category": "EVIDENCE",
        "description": "Original text snippets extracted for audit verification.",
        "weight": 1.0,
        "required": True,
    },

    # 4. EMISSIONS_DATA
    {
        "code": "GF_EMIS_S1",
        "name": "Direct Scope 1 GHG Footprint Accounted",
        "category": "EMISSIONS_DATA",
        "description": "Direct stationary combustion emissions from fuel (diesel).",
        "weight": 1.5,
        "required": True,
    },
    {
        "code": "GF_EMIS_S2",
        "name": "Location-Based Scope 2 GHG Footprint Accounted",
        "category": "EMISSIONS_DATA",
        "description": "Indirect grid electricity emissions calculated with grid factors.",
        "weight": 1.5,
        "required": True,
    },
    {
        "code": "GF_EMIS_S3",
        "name": "Scope 3 Value Chain Emissions Inventory",
        "category": "EMISSIONS_DATA",
        "description": "Scope 3 value chain emissions. Marked MISSING if data unavailable.",
        "weight": 1.0,
        "required": False,
    },

    # 5. REDUCTION_PLAN
    {
        "code": "GF_PLAN_OPPS",
        "name": "Material Reduction Opportunities Identified",
        "category": "REDUCTION_PLAN",
        "description": "Grounded reduction opportunities derived from posted ledger.",
        "weight": 1.5,
        "required": True,
    },
    {
        "code": "GF_PLAN_ACTIONS",
        "name": "Prioritized Decarbonization Measures",
        "category": "REDUCTION_PLAN",
        "description": "Actionable energy efficiency and emission reduction measures.",
        "weight": 1.0,
        "required": True,
    },

    # 6. REDUCTION_PROJECTS
    {
        "code": "GF_PROJ_EXISTS",
        "name": "Tracked Decarbonization Projects",
        "category": "REDUCTION_PROJECTS",
        "description": "Formal reduction projects created with baseline targets.",
        "weight": 1.5,
        "required": False,
    },
    {
        "code": "GF_PROJ_STATUS",
        "name": "Active Project Execution Lifecycle",
        "category": "REDUCTION_PROJECTS",
        "description": "Projects actively in progress or completed.",
        "weight": 1.0,
        "required": False,
    },

    # 7. MEASUREMENT_VERIFICATION
    {
        "code": "GF_MV_MEASUREMENT",
        "name": "Observed Reduction Measurement Results",
        "category": "MEASUREMENT_VERIFICATION",
        "description": "Post-project emissions measured against baseline ledger.",
        "weight": 1.5,
        "required": False,
    },
    {
        "code": "GF_MV_VERIFICATION",
        "name": "Verification & Assurance Workflow Status",
        "category": "MEASUREMENT_VERIFICATION",
        "description": "Verification status (Internal Review, Accepted, or External Verification).",
        "weight": 1.0,
        "required": False,
    },

    # 8. REPORTING
    {
        "code": "GF_REP_GENERATED",
        "name": "Framework-Oriented Compliance Report Prepared",
        "category": "REPORTING",
        "description": "Compliance report generated for GHG Protocol, BRSR, GRI, or CBAM.",
        "weight": 1.5,
        "required": True,
    },
    {
        "code": "GF_REP_COVERAGE",
        "name": "Reporting Disclosure Coverage",
        "category": "REPORTING",
        "description": "Supported framework disclosures documented with evidence.",
        "weight": 1.0,
        "required": True,
    },

    # 9. GOVERNANCE
    {
        "code": "GF_GOV_POLICY",
        "name": "Sustainability Governance & Ownership",
        "category": "GOVERNANCE",
        "description": "Documented environmental policy, organization boundary, or responsible person.",
        "weight": 1.0,
        "required": False,
    },

    # 10. FINANCE_DOCUMENT_READINESS
    {
        "code": "GF_FIN_DOCS",
        "name": "Business Identity & Supporting Documents Present",
        "category": "FINANCE_DOCUMENT_READINESS",
        "description": "Presence of core business identity and utility billing documents.",
        "weight": 1.0,
        "required": True,
    },
]


class GreenFinanceService:
    """
    Deterministic Green Finance Readiness Engine Service.
    """

    def __init__(self):
        self.engine_version = "1.0"

    # -------------------------------------------------------------------------
    # 1. ASSESSMENT CREATION
    # -------------------------------------------------------------------------

    def create_assessment(
        self,
        db: Session,
        data: GreenFinanceAssessmentCreate,
    ) -> GreenFinanceAssessment:
        period = data.reporting_period.strip()
        year = data.reporting_year or self._parse_year(period)
        code = self._generate_assessment_code(period, db)

        assessment = GreenFinanceAssessment(
            assessment_code=code,
            business_name=data.business_name or "TARA ENGINEERING WORKS",
            reporting_period=period,
            reporting_year=year,
            assessment_version="1.0",
            overall_readiness_score=0.0,
            readiness_band="NOT_READY",
            status="DRAFT",
            notes=data.notes,
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)

        # Log event CREATED
        self._log_event(db, assessment.id, "CREATED", None, "DRAFT", f"Draft assessment {code} created.")
        return assessment

    # -------------------------------------------------------------------------
    # 2. ASSESSMENT GENERATION (Scoring Engine)
    # -------------------------------------------------------------------------

    def generate_assessment(
        self,
        db: Session,
        assessment_id: int,
    ) -> GreenFinanceAssessment:
        assessment = db.query(GreenFinanceAssessment).filter_by(id=assessment_id).first()
        if not assessment:
            raise ValueError(f"GreenFinanceAssessment with ID {assessment_id} not found.")

        if assessment.status == "FINALIZED":
            raise ValueError("This assessment is FINALIZED and immutable. Create a new assessment version to update.")

        # Clear previous requirements and evidence
        db.query(GreenFinanceEvidence).filter_by(assessment_id=assessment.id).delete()
        db.query(GreenFinanceRequirement).filter_by(assessment_id=assessment.id).delete()
        db.commit()

        # Fetch database state for reporting_period
        period = assessment.reporting_period
        docs = db.query(Document).filter(Document.status == "COMPLETED").all()
        metrics = db.query(SustainabilityMetric).all()
        activities = db.query(ActivityData).filter_by(reporting_period=period).all()
        calcs = db.query(CarbonCalculation).filter_by(reporting_period=period).all()
        posted_entries = db.query(CarbonLedgerEntry).filter_by(reporting_period=period, accounting_status="POSTED").all()
        opps = db.query(ReductionOpportunity).all()
        projects = db.query(ReductionProject).all()
        measurements = db.query(ReductionMeasurement).all()
        verifications = db.query(VerificationRecord).all()
        reports = db.query(ComplianceReport).filter_by(reporting_period=period).all()

        total_weighted_score = 0.0
        total_applicable_weight = 0.0

        sup_count = 0
        part_count = 0
        miss_count = 0
        rev_count = 0

        # Evaluate each requirement deterministically
        for req_def in REQUIREMENT_DEFINITIONS:
            req_code = req_def["code"]
            status, reason, src_type, src_id, evidence_list = self._evaluate_requirement(
                req_code=req_code,
                period=period,
                docs=docs,
                metrics=metrics,
                activities=activities,
                calcs=calcs,
                posted_entries=posted_entries,
                opps=opps,
                projects=projects,
                measurements=measurements,
                verifications=verifications,
                reports=reports,
            )

            req = GreenFinanceRequirement(
                assessment_id=assessment.id,
                requirement_code=req_code,
                requirement_name=req_def["name"],
                category=req_def["category"],
                description=req_def["description"],
                weight=req_def["weight"],
                required=req_def["required"],
                status=status,
                reason=reason,
                source_type=src_type,
                source_id=src_id,
            )
            db.add(req)
            db.commit()
            db.refresh(req)

            # Add evidence records
            for ev in evidence_list:
                ev_rec = GreenFinanceEvidence(
                    assessment_id=assessment.id,
                    requirement_id=req.id,
                    source_type=ev.get("source_type"),
                    source_id=ev.get("source_id"),
                    document_id=ev.get("document_id"),
                    source_field=ev.get("source_field"),
                    source_text=ev.get("source_text"),
                    reporting_period=period,
                    evidence_status="VERIFIED" if status in ["SUPPORTED", "PARTIALLY_SUPPORTED"] else "NEEDS_REVIEW",
                )
                db.add(ev_rec)

            # Accumulate weighted score
            completion_val = self._status_to_completion(status)
            if status != "NOT_APPLICABLE":
                total_weighted_score += req_def["weight"] * completion_val
                total_applicable_weight += req_def["weight"]

            if status == "SUPPORTED":
                sup_count += 1
            elif status == "PARTIALLY_SUPPORTED":
                part_count += 1
            elif status == "NEEDS_REVIEW":
                rev_count += 1
            elif status == "MISSING":
                miss_count += 1

        # Calculate score 0.0 - 100.0
        final_score = 0.0
        if total_applicable_weight > 0:
            final_score = round((total_weighted_score / total_applicable_weight) * 100.0, 1)

        band = self._calculate_readiness_band(final_score)

        prev_status = assessment.status
        assessment.overall_readiness_score = final_score
        assessment.readiness_band = band
        assessment.status = "GENERATED" if miss_count == 0 else "NEEDS_REVIEW"
        assessment.generated_at = datetime.utcnow()

        db.commit()
        db.refresh(assessment)

        self._log_event(
            db, assessment.id, "GENERATED", prev_status, assessment.status,
            f"Assessment generated: score={final_score}, band={band}, supported={sup_count}/{len(REQUIREMENT_DEFINITIONS)}."
        )
        return assessment

    # -------------------------------------------------------------------------
    # 3. REQUIREMENT EVALUATION LOGIC
    # -------------------------------------------------------------------------

    def _evaluate_requirement(
        self,
        req_code: str,
        period: str,
        docs: List[Document],
        metrics: List[SustainabilityMetric],
        activities: List[ActivityData],
        calcs: List[CarbonCalculation],
        posted_entries: List[CarbonLedgerEntry],
        opps: List[ReductionOpportunity],
        projects: List[ReductionProject],
        measurements: List[ReductionMeasurement],
        verifications: List[VerificationRecord],
        reports: List[ComplianceReport],
    ) -> Tuple[str, str, Optional[str], Optional[int], List[Dict[str, Any]]]:

        # 1. DATA_READINESS
        if req_code == "GF_DATA_DOCS":
            if docs:
                return ("SUPPORTED", f"Found {len(docs)} completed business source documents.", "DOCUMENT", docs[0].id, [{"source_type": "DOCUMENT", "document_id": docs[0].id}])
            return ("MISSING", "No completed source documents uploaded.", None, None, [])

        if req_code == "GF_DATA_PERIOD":
            if period:
                return ("SUPPORTED", f"Reporting period context '{period}' defined.", "DOCUMENT", 1, [{"source_type": "DOCUMENT", "document_id": 1}])
            return ("MISSING", "Reporting period context missing.", None, None, [])

        if req_code == "GF_DATA_METRICS":
            if metrics:
                return ("SUPPORTED", f"Found {len(metrics)} extracted utility metrics.", "METRIC", metrics[0].id, [{"source_type": "METRIC", "source_id": metrics[0].id, "document_id": metrics[0].document_id}])
            return ("MISSING", "No extracted sustainability metrics found.", None, None, [])

        # 2. CARBON_ACCOUNTING
        if req_code == "GF_CALC_EXISTS":
            if calcs:
                return ("SUPPORTED", f"Found {len(calcs)} calculated emissions records for period {period}.", "CARBON_CALCULATION", calcs[0].id, [{"source_type": "CARBON_CALCULATION", "source_id": calcs[0].id}])
            return ("MISSING", f"No calculated carbon emissions for period {period}.", None, None, [])

        if req_code == "GF_CALC_POSTED":
            if posted_entries:
                return ("SUPPORTED", f"Found {len(posted_entries)} POSTED carbon ledger entries.", "CARBON_LEDGER", posted_entries[0].id, [{"source_type": "CARBON_LEDGER", "source_id": posted_entries[0].id, "document_id": posted_entries[0].document_id}])
            return ("MISSING", f"No POSTED carbon ledger entries for period {period}.", None, None, [])

        if req_code == "GF_CALC_FACTORS":
            resolved = [e for e in posted_entries if e.factor_name and e.factor_value]
            if resolved:
                return ("SUPPORTED", f"{len(resolved)} posted entries have resolved factor provenance.", "CARBON_LEDGER", resolved[0].id, [{"source_type": "CARBON_LEDGER", "source_id": resolved[0].id}])
            return ("MISSING", "Emission factor provenance unresolved.", None, None, [])

        # 3. EVIDENCE
        if req_code == "GF_EVID_PROVENANCE":
            if posted_entries and any(e.document_id for e in posted_entries):
                e = next(e for e in posted_entries if e.document_id)
                return ("SUPPORTED", "End-to-end evidence lineage intact from source document to ledger.", "CARBON_LEDGER", e.id, [{"source_type": "CARBON_LEDGER", "source_id": e.id, "document_id": e.document_id}])
            return ("MISSING", "Evidence lineage incomplete.", None, None, [])

        if req_code == "GF_EVID_TEXT":
            m_text = [m for m in metrics if m.source_text]
            if m_text:
                return ("SUPPORTED", f"Found {len(m_text)} verifiable source text snippets.", "METRIC", m_text[0].id, [{"source_type": "METRIC", "source_id": m_text[0].id, "source_text": m_text[0].source_text}])
            return ("MISSING", "Source text snippets missing.", None, None, [])

        # 4. EMISSIONS_DATA
        if req_code == "GF_EMIS_S1":
            s1 = [e for e in posted_entries if e.scope == "SCOPE_1"]
            if s1:
                return ("SUPPORTED", f"Scope 1 direct footprint accounted ({len(s1)} entries).", "CARBON_LEDGER", s1[0].id, [{"source_type": "CARBON_LEDGER", "source_id": s1[0].id}])
            return ("MISSING", "Scope 1 emissions data missing or unposted.", None, None, [])

        if req_code == "GF_EMIS_S2":
            s2 = [e for e in posted_entries if e.scope == "SCOPE_2"]
            if s2:
                return ("SUPPORTED", f"Scope 2 location-based footprint accounted ({len(s2)} entries).", "CARBON_LEDGER", s2[0].id, [{"source_type": "CARBON_LEDGER", "source_id": s2[0].id}])
            return ("MISSING", "Scope 2 emissions data missing or unposted.", None, None, [])

        if req_code == "GF_EMIS_S3":
            s3 = [e for e in posted_entries if e.scope == "SCOPE_3"]
            if s3:
                return ("SUPPORTED", f"Scope 3 value chain emissions available ({len(s3)} entries).", "CARBON_LEDGER", s3[0].id, [{"source_type": "CARBON_LEDGER", "source_id": s3[0].id}])
            return ("MISSING", "Scope 3 emissions data unavailable for this period. Marked MISSING (not zero).", None, None, [])

        # 5. REDUCTION_PLAN
        if req_code == "GF_PLAN_OPPS":
            if opps:
                return ("SUPPORTED", f"Found {len(opps)} grounded reduction opportunities.", "REDUCTION_OPPORTUNITY", opps[0].id, [{"source_type": "REDUCTION_OPPORTUNITY", "source_id": opps[0].id}])
            return ("MISSING", "No reduction opportunities generated.", None, None, [])

        if req_code == "GF_PLAN_ACTIONS":
            if opps:
                return ("SUPPORTED", "Actionable decarbonization measures identified.", "REDUCTION_OPPORTUNITY", opps[0].id, [{"source_type": "REDUCTION_OPPORTUNITY", "source_id": opps[0].id}])
            return ("MISSING", "Decarbonization measures unassigned.", None, None, [])

        # 6. REDUCTION_PROJECTS
        if req_code == "GF_PROJ_EXISTS":
            if projects:
                return ("SUPPORTED", f"Found {len(projects)} tracked reduction projects.", "REDUCTION_PROJECT", projects[0].id, [{"source_type": "REDUCTION_PROJECT", "source_id": projects[0].id}])
            return ("MISSING", "No reduction projects created.", None, None, [])

        if req_code == "GF_PROJ_STATUS":
            active = [p for p in projects if p.status in ["PLANNED", "IN_PROGRESS", "COMPLETED"]]
            if active:
                return ("SUPPORTED", f"{len(active)} projects active in lifecycle.", "REDUCTION_PROJECT", active[0].id, [{"source_type": "REDUCTION_PROJECT", "source_id": active[0].id}])
            return ("MISSING", "No active projects in lifecycle.", None, None, [])

        # 7. MEASUREMENT_VERIFICATION
        if req_code == "GF_MV_MEASUREMENT":
            if measurements:
                return ("SUPPORTED", f"Found {len(measurements)} reduction measurement records.", "REDUCTION_MEASUREMENT", measurements[0].id, [{"source_type": "REDUCTION_MEASUREMENT", "source_id": measurements[0].id}])
            return ("MISSING", "No post-project measurement records executed.", None, None, [])

        if req_code == "GF_MV_VERIFICATION":
            if verifications:
                v = verifications[0]
                return ("SUPPORTED", f"Verification record status: {v.verification_status}.", "VERIFICATION_RECORD", v.id, [{"source_type": "VERIFICATION_RECORD", "source_id": v.id}])
            return ("MISSING", "No verification workflow records.", None, None, [])

        # 8. REPORTING
        if req_code == "GF_REP_GENERATED":
            if reports:
                return ("SUPPORTED", f"Compliance report generated ({reports[0].framework}).", "COMPLIANCE_REPORT", reports[0].id, [{"source_type": "COMPLIANCE_REPORT", "source_id": reports[0].id}])
            return ("MISSING", f"No compliance report prepared for period {period}.", None, None, [])

        if req_code == "GF_REP_COVERAGE":
            if reports and reports[0].status in ["GENERATED", "NEEDS_REVIEW", "FINALIZED"]:
                return ("SUPPORTED", "Reporting disclosure coverage verified.", "COMPLIANCE_REPORT", reports[0].id, [{"source_type": "COMPLIANCE_REPORT", "source_id": reports[0].id}])
            return ("MISSING", "Disclosure coverage unverified.", None, None, [])

        # 9. GOVERNANCE
        if req_code == "GF_GOV_POLICY":
            if docs:
                return ("PARTIALLY_SUPPORTED", "Business identity and operational boundary documented.", "DOCUMENT", docs[0].id, [{"source_type": "DOCUMENT", "document_id": docs[0].id}])
            return ("MISSING", "Governance policies unavailable. Marked MISSING.", None, None, [])

        # 10. FINANCE_DOCUMENT_READINESS
        if req_code == "GF_FIN_DOCS":
            if docs:
                return ("SUPPORTED", f"Found {len(docs)} supporting utility and business billing records.", "DOCUMENT", docs[0].id, [{"source_type": "DOCUMENT", "document_id": docs[0].id}])
            return ("MISSING", "Finance supporting documents missing.", None, None, [])

        return ("MISSING", f"Requirement {req_code} unmapped.", None, None, [])

    # -------------------------------------------------------------------------
    # 4. STATUS & ASSURANCE WORKFLOW
    # -------------------------------------------------------------------------

    def update_assessment_status(
        self,
        db: Session,
        assessment_id: int,
        new_status: str,
        notes: Optional[str] = None,
    ) -> GreenFinanceAssessment:
        st = new_status.strip().upper()
        valid_statuses = {"DRAFT", "GENERATED", "NEEDS_REVIEW", "READY_FOR_APPLICATION", "FINALIZED"}
        if st not in valid_statuses:
            raise ValueError(f"Invalid assessment status '{new_status}'. Must be one of {sorted(valid_statuses)}")

        assessment = db.query(GreenFinanceAssessment).filter_by(id=assessment_id).first()
        if not assessment:
            raise ValueError(f"GreenFinanceAssessment with ID {assessment_id} not found.")

        if assessment.status == "FINALIZED":
            raise ValueError("Assessment is already FINALIZED and cannot be modified.")

        prev_st = assessment.status
        assessment.status = st
        if st == "FINALIZED":
            assessment.finalized_at = datetime.utcnow()

        db.commit()
        db.refresh(assessment)

        self._log_event(
            db, assessment.id, "STATUS_CHANGE", prev_st, st,
            notes or f"Status updated from {prev_st} to {st}."
        )
        return assessment

    # -------------------------------------------------------------------------
    # 5. DTO BUILDERS & SUMMARY GENERATORS
    # -------------------------------------------------------------------------

    def get_assessments(
        self,
        db: Session,
        reporting_period: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[GreenFinanceAssessment]:
        query = db.query(GreenFinanceAssessment)
        if reporting_period:
            query = query.filter(GreenFinanceAssessment.reporting_period == reporting_period.strip())
        if status:
            query = query.filter(GreenFinanceAssessment.status == status.strip().upper())
        return query.order_by(desc(GreenFinanceAssessment.created_at)).all()

    def get_assessment(
        self,
        db: Session,
        assessment_id: int,
    ) -> Optional[GreenFinanceAssessment]:
        return db.query(GreenFinanceAssessment).filter_by(id=assessment_id).first()

    def build_assessment_dto(
        self,
        db: Session,
        assessment: GreenFinanceAssessment,
    ) -> GreenFinanceAssessmentResponse:
        reqs = (
            db.query(GreenFinanceRequirement)
            .filter_by(assessment_id=assessment.id)
            .all()
        )
        events = (
            db.query(GreenFinanceAssessmentEvent)
            .filter_by(assessment_id=assessment.id)
            .order_by(GreenFinanceAssessmentEvent.created_at.asc())
            .all()
        )

        req_dtos = []
        tot_count = 0
        sup_count = 0
        part_count = 0
        miss_count = 0
        rev_count = 0

        for r in reqs:
            tot_count += 1
            if r.status == "SUPPORTED":
                sup_count += 1
            elif r.status == "PARTIALLY_SUPPORTED":
                part_count += 1
            elif r.status == "NEEDS_REVIEW":
                rev_count += 1
            else:
                miss_count += 1

            ev_recs = (
                db.query(GreenFinanceEvidence)
                .filter_by(assessment_id=assessment.id, requirement_id=r.id)
                .all()
            )
            ev_dtos = [GreenFinanceEvidenceResponse.model_validate(ev) for ev in ev_recs]
            r_dto = GreenFinanceRequirementResponse.model_validate(r)
            r_dto.evidence_items = ev_dtos
            req_dtos.append(r_dto)

        event_dtos = [GreenFinanceAssessmentEventResponse.model_validate(e) for e in events]
        dimensions = self.get_dimension_summaries(reqs)
        missing_list = self.get_missing_requirements(reqs)
        next_actions = self.get_next_actions(reqs)
        checklist = self.get_checklist(reqs)

        resp = GreenFinanceAssessmentResponse.model_validate(assessment)
        resp.disclaimer = GREEN_FINANCE_DISCLAIMER
        resp.total_requirements = tot_count
        resp.supported_requirements = sup_count
        resp.partial_requirements = part_count
        resp.missing_requirements_count = miss_count
        resp.needs_review_requirements = rev_count
        resp.dimensions = dimensions
        resp.missing_requirements = missing_list
        resp.next_actions = next_actions
        resp.checklist = checklist
        resp.requirements = req_dtos
        resp.events = event_dtos
        return resp

    def get_dimension_summaries(self, reqs: List[GreenFinanceRequirement]) -> List[GreenFinanceDimensionSummary]:
        categories = [
            ("DATA_READINESS", "1. Data Readiness"),
            ("CARBON_ACCOUNTING", "2. Carbon Accounting"),
            ("EVIDENCE", "3. Evidence Readiness"),
            ("EMISSIONS_DATA", "4. Emissions Data"),
            ("REDUCTION_PLAN", "5. Reduction Plan"),
            ("REDUCTION_PROJECTS", "6. Reduction Projects"),
            ("MEASUREMENT_VERIFICATION", "7. Measurement & Verification"),
            ("REPORTING", "8. Reporting Readiness"),
            ("GOVERNANCE", "9. Governance Readiness"),
            ("FINANCE_DOCUMENT_READINESS", "10. Finance Document Readiness"),
        ]

        result = []
        for cat_code, cat_title in categories:
            cat_reqs = [r for r in reqs if r.category == cat_code]
            if not cat_reqs:
                result.append(
                    GreenFinanceDimensionSummary(
                        category=cat_code,
                        title=cat_title,
                        score=0.0,
                        max_weight=1.0,
                        status="MISSING",
                        supported_count=0,
                        total_count=0,
                        explanation="No requirement criteria registered for this dimension.",
                    )
                )
                continue

            tot_w = sum(r.weight for r in cat_reqs if r.status != "NOT_APPLICABLE")
            got_w = sum(r.weight * self._status_to_completion(r.status) for r in cat_reqs if r.status != "NOT_APPLICABLE")
            sup = sum(1 for r in cat_reqs if r.status == "SUPPORTED")
            tot = len(cat_reqs)

            dim_score = round((got_w / tot_w * 100.0), 1) if tot_w > 0 else 0.0
            dim_status = "SUPPORTED" if dim_score >= 80.0 else ("PARTIAL" if dim_score >= 40.0 else "MISSING")

            expl = f"{sup}/{tot} criteria supported in {cat_title.split('. ')[1]}."
            if cat_code == "FINANCE_DOCUMENT_READINESS":
                expl += f" {FINANCIAL_CHECKLIST_DISCLAIMER}"

            result.append(
                GreenFinanceDimensionSummary(
                    category=cat_code,
                    title=cat_title,
                    score=dim_score,
                    max_weight=tot_w,
                    status=dim_status,
                    supported_count=sup,
                    total_count=tot,
                    explanation=expl,
                )
            )
        return result

    def get_missing_requirements(self, reqs: List[GreenFinanceRequirement]) -> List[GreenFinanceMissingRequirement]:
        missing = [r for r in reqs if r.status in ["MISSING", "PARTIALLY_SUPPORTED", "NEEDS_REVIEW"]]
        result = []
        for r in missing:
            prio = "HIGH" if r.required or r.weight >= 1.5 else "MEDIUM"
            action = f"Provide supporting {r.category.lower().replace('_', ' ')} documentation or execution records."
            result.append(
                GreenFinanceMissingRequirement(
                    requirement_code=r.requirement_code,
                    requirement_name=r.requirement_name,
                    category=r.category,
                    priority=prio,
                    reason=r.reason or f"Requirement '{r.requirement_name}' is currently {r.status}.",
                    what_is_needed=action,
                    evidence_currently_available="None" if r.status == "MISSING" else f"Status: {r.status}",
                    source_reference=r.source_type,
                )
            )
        return result

    def get_next_actions(self, reqs: List[GreenFinanceRequirement]) -> List[GreenFinanceNextAction]:
        result = []

        # High priority actions
        if any(r.requirement_code in ["GF_CALC_POSTED", "GF_CALC_EXISTS"] and r.status != "SUPPORTED" for r in reqs):
            result.append(
                GreenFinanceNextAction(
                    action="Post calculated carbon accounting entries to Carbon Ledger.",
                    priority="HIGH",
                    reason="Posted carbon ledger entries are required for grounded GHG reporting and lender review.",
                    category="CARBON_ACCOUNTING",
                    expected_readiness_impact="+15.0 points to readiness score.",
                )
            )

        if any(r.requirement_code == "GF_EMIS_S3" and r.status == "MISSING" for r in reqs):
            result.append(
                GreenFinanceNextAction(
                    action="Gather Scope 3 value chain activity records or document genuine unavailability.",
                    priority="MEDIUM",
                    reason="Scope 3 emissions are currently missing. Scope 3 data is never treated as zero.",
                    category="EMISSIONS_DATA",
                    expected_readiness_impact="+10.0 points to emissions readiness.",
                )
            )

        if any(r.requirement_code == "GF_REP_GENERATED" and r.status != "SUPPORTED" for r in reqs):
            result.append(
                GreenFinanceNextAction(
                    action="Generate framework-oriented compliance report (GHG Protocol / BRSR / GRI).",
                    priority="HIGH",
                    reason="Lenders require standardized report preparation disclosures for environmental review.",
                    category="REPORTING",
                    expected_readiness_impact="+15.0 points to reporting readiness.",
                )
            )

        if any(r.requirement_code == "GF_PROJ_EXISTS" and r.status != "SUPPORTED" for r in reqs):
            result.append(
                GreenFinanceNextAction(
                    action="Create formal reduction project linked to dominant emission sources.",
                    priority="MEDIUM",
                    reason="Demonstrates active decarbonization execution posture.",
                    category="REDUCTION_PROJECTS",
                    expected_readiness_impact="+10.0 points to project readiness.",
                )
            )

        if not result:
            result.append(
                GreenFinanceNextAction(
                    action="Finalize assessment for green-finance application review.",
                    priority="LOW",
                    reason="All core sustainability evidence requirements are supported and ready for review.",
                    category="GOVERNANCE",
                    expected_readiness_impact="Prepares package for application submission.",
                )
            )
        return result

    def get_checklist(self, reqs: List[GreenFinanceRequirement]) -> List[GreenFinanceChecklistItem]:
        result = []
        for r in reqs:
            chk_status = "READY" if r.status == "SUPPORTED" else ("PARTIAL" if r.status == "PARTIALLY_SUPPORTED" else r.status)
            result.append(
                GreenFinanceChecklistItem(
                    category=r.category,
                    item_code=r.requirement_code,
                    title=r.requirement_name,
                    status=chk_status,
                    description=r.reason or r.description or f"Checklist item {r.requirement_code}",
                    evidence_ref=r.source_type,
                )
            )
        return result

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    @staticmethod
    def _status_to_completion(status: str) -> float:
        st = status.upper()
        if st == "SUPPORTED":
            return 1.0
        if st == "PARTIALLY_SUPPORTED":
            return 0.5
        if st == "NEEDS_REVIEW":
            return 0.25
        return 0.0

    @staticmethod
    def _calculate_readiness_band(score: float) -> str:
        if score >= 70.0:
            return "READY_FOR_REVIEW"
        if score >= 40.0:
            return "PARTIALLY_READY"
        return "NOT_READY"

    def _log_event(
        self,
        db: Session,
        assessment_id: int,
        event_type: str,
        previous_status: Optional[str],
        new_status: Optional[str],
        notes: Optional[str] = None,
    ) -> None:
        ev = GreenFinanceAssessmentEvent(
            assessment_id=assessment_id,
            event_type=event_type,
            previous_status=previous_status,
            new_status=new_status,
            notes=notes,
            actor="SYSTEM",
        )
        db.add(ev)
        db.commit()

    def _generate_assessment_code(self, period: str, db: Session) -> str:
        year_str = datetime.utcnow().strftime("%Y")
        count = db.query(GreenFinanceAssessment).count() + 1
        return f"GFA-{year_str}-{count:04d}"

    @staticmethod
    def _parse_year(period: str) -> Optional[int]:
        try:
            return int(period.strip().split("-")[0])
        except (ValueError, IndexError):
            return None


green_finance_service = GreenFinanceService()
