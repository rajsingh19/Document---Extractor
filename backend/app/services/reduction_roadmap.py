"""
services/reduction_roadmap.py — Deterministic Service for Personalized Reduction Roadmap Engine (Step 22B).

Converts verified carbon accounting actuals, Step 22A reduction priorities,
existing reduction opportunities, and existing reduction projects into a structured,
phased action roadmap aligned to a user-defined reduction target.

TRUTH HIERARCHY & BOUNDARIES:
- Baseline strictly sourced from POSTED CarbonLedgerEntry actuals.
- Target emissions and gap are deterministic mathematical calculations.
- Unverified reduction contributions are strictly NOT_QUANTIFIED with target_contribution=NULL.
- Separates Roadmap Progress (actions completed) from Emissions Reduction Progress (ledger actuals).
- Never mutates accounting truth or source records.
"""
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

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
    ACTION_TYPE_DATA_COLLECTION,
    ACTION_TYPE_DATA_QUALITY,
    ACTION_TYPE_BASELINE_REVIEW,
    ACTION_TYPE_INVESTIGATION,
    ACTION_TYPE_REDUCTION_PROJECT,
    ACTION_TYPE_MONITORING,
    ACTION_TYPE_MEASUREMENT,
    ACTION_TYPE_VERIFICATION,
    ACTION_TYPE_REPORTING,
    ROADMAP_STATUS_DRAFT,
    ROADMAP_STATUS_ACTIVE,
    ITEM_STATUS_NOT_STARTED,
    ITEM_STATUS_IN_PROGRESS,
    ITEM_STATUS_BLOCKED,
    ITEM_STATUS_COMPLETED,
    CONTRIBUTION_STATUS_NOT_QUANTIFIED,
    TARGET_FEASIBILITY_CALCULATED,
    TARGET_FEASIBILITY_UNKNOWN,
    TARGET_FEASIBILITY_DATA_INSUFFICIENT,
    TARGET_FEASIBILITY_SUPPORTED,
    EVENT_TYPE_CREATED,
    EVENT_TYPE_STATUS_CHANGED,
    EVENT_TYPE_ITEM_STATUS_CHANGED,
    EVENT_TYPE_REGENERATED,
    PRIORITY_CRITICAL,
    PRIORITY_HIGH,
    PRIORITY_MEDIUM,
    PRIORITY_LOW,
    EFFORT_LOW,
    EFFORT_MEDIUM,
    EFFORT_HIGH,
    DEFAULT_FEASIBILITY_NOTE,
    DEFAULT_MEASUREMENT_METHOD,
    DEFAULT_VERIFICATION_METHOD,
)
from backend.app.services.reduction_intelligence import ReductionIntelligenceService


class ReductionRoadmapService:
    """
    Deterministic planning engine for personalized carbon reduction roadmaps.
    """

    def __init__(self):
        self.version = REDUCTION_ROADMAP_VERSION
        self.intelligence_service = ReductionIntelligenceService()

    # ==========================================================================
    # 1. BASELINE SELECTION & TARGET ARITHMETIC
    # ==========================================================================

    def select_baseline(
        self,
        db: Session,
        document_id: Optional[int] = None,
        explicit_period: Optional[str] = None
    ) -> Tuple[str, Decimal, Decimal]:
        """
        Determines the accounting baseline strictly from POSTED CarbonLedgerEntry records.
        Returns: (baseline_period, baseline_emissions_kgco2e, baseline_emissions_tco2e)
        """
        query = db.query(CarbonLedgerEntry).filter(
            CarbonLedgerEntry.accounting_status == "POSTED"
        )
        if document_id is not None:
            query = query.filter(CarbonLedgerEntry.document_id == document_id)

        all_entries = query.all()
        if not all_entries:
            return ("UNAVAILABLE", Decimal("0.0"), Decimal("0.0"))

        if explicit_period:
            period_entries = [e for e in all_entries if e.reporting_period == explicit_period]
            if period_entries:
                kg = sum(Decimal(str(e.calculated_co2e or 0)) for e in period_entries)
                t = kg / Decimal("1000.0")
                return (explicit_period, kg, t)

        # Group by reporting_period
        by_period: Dict[str, List[CarbonLedgerEntry]] = {}
        for e in all_entries:
            p = e.reporting_period or "UNSPECIFIED"
            if p not in by_period:
                by_period[p] = []
            by_period[p].append(e)

        # Sort periods in reverse chronological order
        valid_periods = [p for p in by_period.keys() if p != "UNSPECIFIED"]
        if valid_periods:
            valid_periods.sort(reverse=True)
            chosen_period = valid_periods[0]
            entries = by_period[chosen_period]
            kg = sum(Decimal(str(e.calculated_co2e or 0)) for e in entries)
            t = kg / Decimal("1000.0")
            return (chosen_period, kg, t)

        # Fallback: all available actuals
        kg = sum(Decimal(str(e.calculated_co2e or 0)) for e in all_entries)
        t = kg / Decimal("1000.0")
        return ("ALL_AVAILABLE_ACTUALS", kg, t)

    def calculate_target_and_gap(
        self,
        baseline_kg: Decimal,
        baseline_t: Decimal,
        target_reduction_percent: Decimal
    ) -> Tuple[Decimal, Decimal, Decimal, Decimal]:
        """
        Deterministic target emissions and required reduction gap calculation.
        Returns: (target_emissions_kg, target_emissions_t, reduction_gap_kg, reduction_gap_t)
        """
        if baseline_kg <= Decimal("0.0"):
            return (Decimal("0.0"), Decimal("0.0"), Decimal("0.0"), Decimal("0.0"))

        factor = (Decimal("100.0") - target_reduction_percent) / Decimal("100.0")
        target_kg = (baseline_kg * factor).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        target_t = (baseline_t * factor).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

        gap_kg = (baseline_kg - target_kg).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        gap_t = (baseline_t - target_t).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

        return (target_kg, target_t, gap_kg, gap_t)

    # ==========================================================================
    # 2. ROADMAP CREATION & GENERATION
    # ==========================================================================

    def create_roadmap(
        self,
        db: Session,
        target_reduction_percent: Decimal,
        name: Optional[str] = None,
        document_id: Optional[int] = None,
        reporting_year: Optional[int] = None,
        baseline_period: Optional[str] = None,
        target_year: Optional[int] = None,
        target_period: Optional[str] = None,
    ) -> ReductionRoadmap:
        """
        Initializes and creates a new ReductionRoadmap with deterministic calculations and phased items.
        """
        # Validate inputs
        if target_reduction_percent < Decimal("0.0") or target_reduction_percent > Decimal("100.0"):
            raise ValueError("target_reduction_percent must be between 0 and 100")

        # Select baseline
        b_period, b_kg, b_t = self.select_baseline(
            db=db,
            document_id=document_id,
            explicit_period=baseline_period
        )

        # Calculate target and gap
        t_kg, t_t, gap_kg, gap_t = self.calculate_target_and_gap(
            baseline_kg=b_kg,
            baseline_t=b_t,
            target_reduction_percent=target_reduction_percent
        )

        # Determine feasibility status
        if b_kg <= Decimal("0.0"):
            target_status = TARGET_FEASIBILITY_DATA_INSUFFICIENT
            feasibility_note = "No posted emissions data available for baseline calculation."
        elif target_reduction_percent == Decimal("0.0"):
            target_status = TARGET_FEASIBILITY_SUPPORTED
            feasibility_note = "A 0% reduction target is already achieved by baseline emissions."
        else:
            target_status = TARGET_FEASIBILITY_UNKNOWN
            feasibility_note = DEFAULT_FEASIBILITY_NOTE

        # Generate unique code
        doc_suffix = f"DOC_{document_id}" if document_id else "PORTFOLIO"
        timestamp_code = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        roadmap_code = f"RDMP-{doc_suffix}-{int(target_reduction_percent)}PCT-{timestamp_code}"

        roadmap_name = name or f"Reduction Roadmap ({int(target_reduction_percent)}% Target)"

        roadmap = ReductionRoadmap(
            roadmap_code=roadmap_code,
            name=roadmap_name,
            document_id=document_id,
            reporting_year=reporting_year,
            baseline_period=b_period,
            baseline_emissions_kgco2e=b_kg,
            baseline_emissions_tco2e=b_t,
            target_reduction_percent=target_reduction_percent,
            target_year=target_year,
            target_period=target_period,
            target_emissions_kgco2e=t_kg,
            target_emissions_tco2e=t_t,
            reduction_gap_kgco2e=gap_kg,
            reduction_gap_tco2e=gap_t,
            target_status=target_status,
            status=ROADMAP_STATUS_ACTIVE if b_kg > 0 else ROADMAP_STATUS_DRAFT,
            confidence="HIGH" if b_kg > 0 else "LOW",
            feasibility_explanation=feasibility_note,
            roadmap_version=self.version,
            calculation_version="1.0",
        )

        db.add(roadmap)
        db.flush()

        # Record creation event
        self._record_event(
            db=db,
            roadmap_id=roadmap.id,
            event_type=EVENT_TYPE_CREATED,
            old_status=None,
            new_status=roadmap.status,
            actor="SYSTEM",
            notes=f"Roadmap initialized with {target_reduction_percent}% reduction target against {b_period} baseline ({b_t:.4f} tCO2e)."
        )

        # Generate phased action items
        self._generate_items_for_roadmap(db=db, roadmap=roadmap)

        db.commit()
        db.refresh(roadmap)
        return roadmap

    def generate_roadmap_items(self, db: Session, roadmap_id: int) -> ReductionRoadmap:
        """
        Regenerates all action items for an existing roadmap based on latest Step 22A priorities and projects.
        """
        roadmap = db.query(ReductionRoadmap).filter(ReductionRoadmap.id == roadmap_id).first()
        if not roadmap:
            raise ValueError(f"Roadmap #{roadmap_id} not found")

        # Delete existing items
        db.query(ReductionRoadmapItem).filter(ReductionRoadmapItem.roadmap_id == roadmap.id).delete()
        db.flush()

        # Regenerate items
        self._generate_items_for_roadmap(db=db, roadmap=roadmap)

        # Record regeneration event
        self._record_event(
            db=db,
            roadmap_id=roadmap.id,
            event_type=EVENT_TYPE_REGENERATED,
            old_status=roadmap.status,
            new_status=roadmap.status,
            actor="SYSTEM",
            notes="Action items regenerated deterministically from latest Step 22A reduction priorities."
        )

        db.commit()
        db.refresh(roadmap)
        return roadmap

    def _generate_items_for_roadmap(self, db: Session, roadmap: ReductionRoadmap):
        """
        Internal deterministic synthesizer creating 4-phase structured action items.
        """
        doc_id = roadmap.document_id

        # 1. Fetch or generate Step 22A priorities
        priorities = db.query(ReductionPriority)
        if doc_id is not None:
            priorities = priorities.filter(ReductionPriority.document_id == doc_id)
        priorities = priorities.order_by(ReductionPriority.priority_rank.asc()).all()

        if not priorities:
            # Evaluate priorities on the fly
            priorities = self.intelligence_service.evaluate_priorities(
                db=db,
                document_id=doc_id,
                save_to_db=True
            )

        # 2. Fetch existing projects and opportunities
        all_projects = db.query(ReductionProject).all()
        proj_by_opp_id: Dict[int, ReductionProject] = {}
        proj_by_act: Dict[str, ReductionProject] = {}
        for p in all_projects:
            if p.opportunity_id:
                proj_by_opp_id[p.opportunity_id] = p
            if p.activity_type:
                proj_by_act[p.activity_type] = p

        all_opps = db.query(ReductionOpportunity).all()
        opp_by_id = {o.id: o for o in all_opps}

        # 3. Phased item buckets
        p1_items: List[Dict[str, Any]] = []
        p2_items: List[Dict[str, Any]] = []
        p3_items: List[Dict[str, Any]] = []
        p4_items: List[Dict[str, Any]] = []

        has_data_quality_gap = False

        for priority in priorities:
            is_dq = (
                priority.category == "DATA_QUALITY"
                or (priority.current_emissions_kgco2e == Decimal("0.0") and priority.opportunity_id is not None)
                or "data gap" in priority.title.lower()
            )

            matched_opp = opp_by_id.get(priority.opportunity_id) if priority.opportunity_id else None
            matched_proj = None
            if priority.project_id:
                matched_proj = db.query(ReductionProject).filter(ReductionProject.id == priority.project_id).first()
            elif matched_opp and matched_opp.id in proj_by_opp_id:
                matched_proj = proj_by_opp_id[matched_opp.id]
            elif priority.activity_type and priority.activity_type in proj_by_act:
                matched_proj = proj_by_act[priority.activity_type]

            # Case A: Data Quality / Blocker Priority
            if is_dq:
                has_data_quality_gap = True
                p1_items.append({
                    "phase": PHASE_1_FOUNDATION,
                    "title": f"Resolve Data Gap: {priority.title}",
                    "action_type": ACTION_TYPE_DATA_QUALITY,
                    "priority_id": priority.id,
                    "opportunity_id": priority.opportunity_id,
                    "project_id": None,
                    "category": priority.category or "DATA_QUALITY",
                    "scope": priority.scope,
                    "current_emissions_kgco2e": priority.current_emissions_kgco2e,
                    "current_emissions_tco2e": priority.current_emissions_tco2e,
                    "target_contribution_kgco2e": None,
                    "target_contribution_tco2e": None,
                    "contribution_status": CONTRIBUTION_STATUS_NOT_QUANTIFIED,
                    "priority": PRIORITY_HIGH,
                    "effort_level": EFFORT_LOW,
                    "dependency": None,
                    "prerequisite": "Required prior to verified reduction accounting and project baseline validation.",
                    "required_data": "Verified regional emission factor / registry entry and metering records.",
                    "measurement_method": "Validate factor in EmissionFactorResolver registry.",
                    "verification_method": "Re-run ActivityData normalization and CarbonCalculation ledger posting.",
                    "status": ITEM_STATUS_NOT_STARTED,
                    "evidence_reference": priority.evidence_reference,
                    "reason": priority.reason,
                    "limitation": "Does not quantify direct emissions reduction until factor is resolved.",
                })
                continue

            # Case B: Operational Emission Source with Existing Project
            if matched_proj:
                proj_status = matched_proj.status or "PLANNED"

                if proj_status == "IN_PROGRESS":
                    p2_items.append({
                        "phase": PHASE_2_ACTION,
                        "title": f"Continue Existing Project: {matched_proj.title}",
                        "action_type": ACTION_TYPE_REDUCTION_PROJECT,
                        "priority_id": priority.id,
                        "opportunity_id": matched_opp.id if matched_opp else None,
                        "project_id": matched_proj.id,
                        "category": priority.category,
                        "scope": priority.scope,
                        "current_emissions_kgco2e": priority.current_emissions_kgco2e,
                        "current_emissions_tco2e": priority.current_emissions_tco2e,
                        "target_contribution_kgco2e": None,
                        "target_contribution_tco2e": None,
                        "contribution_status": CONTRIBUTION_STATUS_NOT_QUANTIFIED,
                        "priority": priority.priority_level or PRIORITY_HIGH,
                        "effort_level": EFFORT_MEDIUM,
                        "dependency": "Resolve data quality gaps" if has_data_quality_gap else None,
                        "prerequisite": "Project baseline established; currently executing.",
                        "required_data": "Operational telemetry and fuel/power logs.",
                        "measurement_method": DEFAULT_MEASUREMENT_METHOD,
                        "verification_method": DEFAULT_VERIFICATION_METHOD,
                        "status": ITEM_STATUS_IN_PROGRESS,
                        "evidence_reference": f"ReductionProject #{matched_proj.id} ({matched_proj.project_code})",
                        "reason": f"Project is already in progress addressing {priority.title}.",
                        "limitation": "Post-implementation savings will be quantified upon project completion.",
                    })
                    p3_items.append({
                        "phase": PHASE_3_MEASUREMENT,
                        "title": f"Measure Post-Project Emissions: {matched_proj.title}",
                        "action_type": ACTION_TYPE_MEASUREMENT,
                        "priority_id": priority.id,
                        "opportunity_id": matched_opp.id if matched_opp else None,
                        "project_id": matched_proj.id,
                        "category": priority.category,
                        "scope": priority.scope,
                        "current_emissions_kgco2e": priority.current_emissions_kgco2e,
                        "current_emissions_tco2e": priority.current_emissions_tco2e,
                        "target_contribution_kgco2e": None,
                        "target_contribution_tco2e": None,
                        "contribution_status": CONTRIBUTION_STATUS_NOT_QUANTIFIED,
                        "priority": PRIORITY_HIGH,
                        "effort_level": EFFORT_LOW,
                        "dependency": f"Continue Existing Project: {matched_proj.title}",
                        "prerequisite": "Completion of project implementation milestone.",
                        "required_data": "POSTED CarbonLedgerEntry records for comparison period.",
                        "measurement_method": DEFAULT_MEASUREMENT_METHOD,
                        "verification_method": DEFAULT_VERIFICATION_METHOD,
                        "status": ITEM_STATUS_NOT_STARTED,
                        "evidence_reference": f"Project {matched_proj.project_code}",
                        "reason": "Verify observed accounting reduction against baseline period.",
                        "limitation": "Observed change does not prove causality without external M&V.",
                    })
                    p4_items.append({
                        "phase": PHASE_4_VERIFICATION,
                        "title": f"Verify Reduction & Update Accounting: {matched_proj.title}",
                        "action_type": ACTION_TYPE_VERIFICATION,
                        "priority_id": priority.id,
                        "opportunity_id": matched_opp.id if matched_opp else None,
                        "project_id": matched_proj.id,
                        "category": priority.category,
                        "scope": priority.scope,
                        "current_emissions_kgco2e": priority.current_emissions_kgco2e,
                        "current_emissions_tco2e": priority.current_emissions_tco2e,
                        "target_contribution_kgco2e": None,
                        "target_contribution_tco2e": None,
                        "contribution_status": CONTRIBUTION_STATUS_NOT_QUANTIFIED,
                        "priority": PRIORITY_MEDIUM,
                        "effort_level": EFFORT_LOW,
                        "dependency": f"Measure Post-Project Emissions: {matched_proj.title}",
                        "prerequisite": "ReductionMeasurement record generated.",
                        "required_data": "VerificationRecord and auditor documentation.",
                        "measurement_method": DEFAULT_MEASUREMENT_METHOD,
                        "verification_method": DEFAULT_VERIFICATION_METHOD,
                        "status": ITEM_STATUS_NOT_STARTED,
                        "evidence_reference": f"Verification workflow for {matched_proj.project_code}",
                        "reason": "Formal accounting sign-off and target progress update.",
                        "limitation": "Third-party validation required for compliance reporting.",
                    })

                elif proj_status == "COMPLETED":
                    p3_items.append({
                        "phase": PHASE_3_MEASUREMENT,
                        "title": f"Audit & Measure Completed Project: {matched_proj.title}",
                        "action_type": ACTION_TYPE_MEASUREMENT,
                        "priority_id": priority.id,
                        "opportunity_id": matched_opp.id if matched_opp else None,
                        "project_id": matched_proj.id,
                        "category": priority.category,
                        "scope": priority.scope,
                        "current_emissions_kgco2e": priority.current_emissions_kgco2e,
                        "current_emissions_tco2e": priority.current_emissions_tco2e,
                        "target_contribution_kgco2e": None,
                        "target_contribution_tco2e": None,
                        "contribution_status": CONTRIBUTION_STATUS_NOT_QUANTIFIED,
                        "priority": PRIORITY_HIGH,
                        "effort_level": EFFORT_LOW,
                        "dependency": None,
                        "prerequisite": "Project completed.",
                        "required_data": "POSTED ledger data for post-project period.",
                        "measurement_method": DEFAULT_MEASUREMENT_METHOD,
                        "verification_method": DEFAULT_VERIFICATION_METHOD,
                        "status": ITEM_STATUS_IN_PROGRESS,
                        "evidence_reference": f"Completed Project #{matched_proj.id}",
                        "reason": "Project completed; measure observed impact.",
                        "limitation": "Requires consecutive post-project billing periods.",
                    })
                    p4_items.append({
                        "phase": PHASE_4_VERIFICATION,
                        "title": f"Finalize Verification for {matched_proj.title}",
                        "action_type": ACTION_TYPE_VERIFICATION,
                        "priority_id": priority.id,
                        "opportunity_id": matched_opp.id if matched_opp else None,
                        "project_id": matched_proj.id,
                        "category": priority.category,
                        "scope": priority.scope,
                        "current_emissions_kgco2e": priority.current_emissions_kgco2e,
                        "current_emissions_tco2e": priority.current_emissions_tco2e,
                        "target_contribution_kgco2e": None,
                        "target_contribution_tco2e": None,
                        "contribution_status": CONTRIBUTION_STATUS_NOT_QUANTIFIED,
                        "priority": PRIORITY_MEDIUM,
                        "effort_level": EFFORT_LOW,
                        "dependency": f"Audit & Measure Completed Project: {matched_proj.title}",
                        "prerequisite": "Measurement record complete.",
                        "required_data": "VerificationRecord sign-off.",
                        "measurement_method": DEFAULT_MEASUREMENT_METHOD,
                        "verification_method": DEFAULT_VERIFICATION_METHOD,
                        "status": ITEM_STATUS_NOT_STARTED,
                        "evidence_reference": f"Verification for Project #{matched_proj.id}",
                        "reason": "Close out project verification.",
                        "limitation": "External assurance required for market credit claims.",
                    })

                else:  # PLANNED
                    p1_items.append({
                        "phase": PHASE_1_FOUNDATION,
                        "title": f"Establish Reference Baseline for {priority.title}",
                        "action_type": ACTION_TYPE_BASELINE_REVIEW,
                        "priority_id": priority.id,
                        "opportunity_id": matched_opp.id if matched_opp else None,
                        "project_id": matched_proj.id,
                        "category": priority.category,
                        "scope": priority.scope,
                        "current_emissions_kgco2e": priority.current_emissions_kgco2e,
                        "current_emissions_tco2e": priority.current_emissions_tco2e,
                        "target_contribution_kgco2e": None,
                        "target_contribution_tco2e": None,
                        "contribution_status": CONTRIBUTION_STATUS_NOT_QUANTIFIED,
                        "priority": priority.priority_level or PRIORITY_HIGH,
                        "effort_level": EFFORT_LOW,
                        "dependency": "Resolve data quality gaps" if has_data_quality_gap else None,
                        "prerequisite": "Verified POSTED CarbonLedgerEntry records.",
                        "required_data": "Consecutive monthly utility bills and POSTED ledger entries.",
                        "measurement_method": "Lock reference period ledger entries.",
                        "verification_method": "Accounting ledger audit trail.",
                        "status": ITEM_STATUS_NOT_STARTED,
                        "evidence_reference": priority.source_reference,
                        "reason": f"Baseline reference needed before initiating planned project '{matched_proj.title}'.",
                        "limitation": "Baseline must not be altered once project commences.",
                    })
                    p2_items.append({
                        "phase": PHASE_2_ACTION,
                        "title": f"Initiate Planned Project: {matched_proj.title}",
                        "action_type": ACTION_TYPE_REDUCTION_PROJECT,
                        "priority_id": priority.id,
                        "opportunity_id": matched_opp.id if matched_opp else None,
                        "project_id": matched_proj.id,
                        "category": priority.category,
                        "scope": priority.scope,
                        "current_emissions_kgco2e": priority.current_emissions_kgco2e,
                        "current_emissions_tco2e": priority.current_emissions_tco2e,
                        "target_contribution_kgco2e": None,
                        "target_contribution_tco2e": None,
                        "contribution_status": CONTRIBUTION_STATUS_NOT_QUANTIFIED,
                        "priority": priority.priority_level or PRIORITY_HIGH,
                        "effort_level": EFFORT_HIGH,
                        "dependency": f"Establish Reference Baseline for {priority.title}",
                        "prerequisite": "Budget approval and baseline confirmation.",
                        "required_data": "Implementation schedule and contractor specifications.",
                        "measurement_method": DEFAULT_MEASUREMENT_METHOD,
                        "verification_method": DEFAULT_VERIFICATION_METHOD,
                        "status": ITEM_STATUS_NOT_STARTED,
                        "evidence_reference": f"Planned Project #{matched_proj.id}",
                        "reason": matched_proj.description or f"Address primary emission source {priority.title}.",
                        "limitation": "Savings depend on operational adoption.",
                    })
                    p3_items.append({
                        "phase": PHASE_3_MEASUREMENT,
                        "title": f"Monitor & Measure Emissions: {matched_proj.title}",
                        "action_type": ACTION_TYPE_MEASUREMENT,
                        "priority_id": priority.id,
                        "opportunity_id": matched_opp.id if matched_opp else None,
                        "project_id": matched_proj.id,
                        "category": priority.category,
                        "scope": priority.scope,
                        "current_emissions_kgco2e": priority.current_emissions_kgco2e,
                        "current_emissions_tco2e": priority.current_emissions_tco2e,
                        "target_contribution_kgco2e": None,
                        "target_contribution_tco2e": None,
                        "contribution_status": CONTRIBUTION_STATUS_NOT_QUANTIFIED,
                        "priority": PRIORITY_HIGH,
                        "effort_level": EFFORT_LOW,
                        "dependency": f"Initiate Planned Project: {matched_proj.title}",
                        "prerequisite": "Project commissioned and operating.",
                        "required_data": "Sub-meter readings and post-implementation invoices.",
                        "measurement_method": DEFAULT_MEASUREMENT_METHOD,
                        "verification_method": DEFAULT_VERIFICATION_METHOD,
                        "status": ITEM_STATUS_NOT_STARTED,
                        "evidence_reference": f"Project {matched_proj.project_code}",
                        "reason": "Track observed change against reference period.",
                        "limitation": "Weather and production volume normalization may be needed.",
                    })
                    p4_items.append({
                        "phase": PHASE_4_VERIFICATION,
                        "title": f"Submit for Verification & Target Review: {matched_proj.title}",
                        "action_type": ACTION_TYPE_VERIFICATION,
                        "priority_id": priority.id,
                        "opportunity_id": matched_opp.id if matched_opp else None,
                        "project_id": matched_proj.id,
                        "category": priority.category,
                        "scope": priority.scope,
                        "current_emissions_kgco2e": priority.current_emissions_kgco2e,
                        "current_emissions_tco2e": priority.current_emissions_tco2e,
                        "target_contribution_kgco2e": None,
                        "target_contribution_tco2e": None,
                        "contribution_status": CONTRIBUTION_STATUS_NOT_QUANTIFIED,
                        "priority": PRIORITY_MEDIUM,
                        "effort_level": EFFORT_LOW,
                        "dependency": f"Monitor & Measure Emissions: {matched_proj.title}",
                        "prerequisite": "At least 1 complete post-project reporting period.",
                        "required_data": "VerificationRecord evidence package.",
                        "measurement_method": DEFAULT_MEASUREMENT_METHOD,
                        "verification_method": DEFAULT_VERIFICATION_METHOD,
                        "status": ITEM_STATUS_NOT_STARTED,
                        "evidence_reference": f"Verification protocol for {matched_proj.project_code}",
                        "reason": "Formal audit of claimed reductions toward target.",
                        "limitation": "Compliance standards require third-party review.",
                    })

            # Case C: Operational Emission Source with NO Existing Project
            else:
                p1_items.append({
                    "phase": PHASE_1_FOUNDATION,
                    "title": f"Investigate Reduction Measures: {priority.title}",
                    "action_type": ACTION_TYPE_INVESTIGATION,
                    "priority_id": priority.id,
                    "opportunity_id": matched_opp.id if matched_opp else None,
                    "project_id": None,
                    "category": priority.category,
                    "scope": priority.scope,
                    "current_emissions_kgco2e": priority.current_emissions_kgco2e,
                    "current_emissions_tco2e": priority.current_emissions_tco2e,
                    "target_contribution_kgco2e": None,
                    "target_contribution_tco2e": None,
                    "contribution_status": CONTRIBUTION_STATUS_NOT_QUANTIFIED,
                    "priority": priority.priority_level or PRIORITY_MEDIUM,
                    "effort_level": EFFORT_LOW,
                    "dependency": "Resolve data quality gaps" if has_data_quality_gap else None,
                    "prerequisite": "Accounting footprint confirmed.",
                    "required_data": "Sub-meter logs and equipment inventories.",
                    "measurement_method": "Facility energy / fuel audit.",
                    "verification_method": "Engineering review.",
                    "status": ITEM_STATUS_NOT_STARTED,
                    "evidence_reference": priority.source_reference,
                    "reason": f"Ranked priority #{priority.priority_rank} ({priority.current_emissions_tco2e:.4f} tCO2e). Detailed investigation required to specify intervention.",
                    "limitation": "No specific project defined yet.",
                })
                p2_items.append({
                    "phase": PHASE_2_ACTION,
                    "title": f"Design & Launch Reduction Initiative for {priority.title}",
                    "action_type": ACTION_TYPE_REDUCTION_PROJECT,
                    "priority_id": priority.id,
                    "opportunity_id": matched_opp.id if matched_opp else None,
                    "project_id": None,
                    "category": priority.category,
                    "scope": priority.scope,
                    "current_emissions_kgco2e": priority.current_emissions_kgco2e,
                    "current_emissions_tco2e": priority.current_emissions_tco2e,
                    "target_contribution_kgco2e": None,
                    "target_contribution_tco2e": None,
                    "contribution_status": CONTRIBUTION_STATUS_NOT_QUANTIFIED,
                    "priority": priority.priority_level or PRIORITY_MEDIUM,
                    "effort_level": EFFORT_HIGH,
                    "dependency": f"Investigate Reduction Measures: {priority.title}",
                    "prerequisite": "Investigation completed and vendor selected.",
                    "required_data": "Approved project scope and operational baseline.",
                    "measurement_method": DEFAULT_MEASUREMENT_METHOD,
                    "verification_method": DEFAULT_VERIFICATION_METHOD,
                    "status": ITEM_STATUS_NOT_STARTED,
                    "evidence_reference": priority.source_reference,
                    "reason": f"Execute approved reduction intervention for {priority.title}.",
                    "limitation": "Intervention must be verified before claiming target credit.",
                })
                p3_items.append({
                    "phase": PHASE_3_MEASUREMENT,
                    "title": f"Measure Post-Implementation Emissions for {priority.title}",
                    "action_type": ACTION_TYPE_MEASUREMENT,
                    "priority_id": priority.id,
                    "opportunity_id": matched_opp.id if matched_opp else None,
                    "project_id": None,
                    "category": priority.category,
                    "scope": priority.scope,
                    "current_emissions_kgco2e": priority.current_emissions_kgco2e,
                    "current_emissions_tco2e": priority.current_emissions_tco2e,
                    "target_contribution_kgco2e": None,
                    "target_contribution_tco2e": None,
                    "contribution_status": CONTRIBUTION_STATUS_NOT_QUANTIFIED,
                    "priority": PRIORITY_MEDIUM,
                    "effort_level": EFFORT_LOW,
                    "dependency": f"Design & Launch Reduction Initiative for {priority.title}",
                    "prerequisite": "Commissioning complete.",
                    "required_data": "Monthly POSTED CarbonLedgerEntry records.",
                    "measurement_method": DEFAULT_MEASUREMENT_METHOD,
                    "verification_method": DEFAULT_VERIFICATION_METHOD,
                    "status": ITEM_STATUS_NOT_STARTED,
                    "evidence_reference": priority.source_reference,
                    "reason": "Determine observed difference in carbon ledger.",
                    "limitation": "Must distinguish organic volume variance from efficiency gains.",
                })
                p4_items.append({
                    "phase": PHASE_4_VERIFICATION,
                    "title": f"Verify Outcomes for {priority.title}",
                    "action_type": ACTION_TYPE_VERIFICATION,
                    "priority_id": priority.id,
                    "opportunity_id": matched_opp.id if matched_opp else None,
                    "project_id": None,
                    "category": priority.category,
                    "scope": priority.scope,
                    "current_emissions_kgco2e": priority.current_emissions_kgco2e,
                    "current_emissions_tco2e": priority.current_emissions_tco2e,
                    "target_contribution_kgco2e": None,
                    "target_contribution_tco2e": None,
                    "contribution_status": CONTRIBUTION_STATUS_NOT_QUANTIFIED,
                    "priority": PRIORITY_LOW,
                    "effort_level": EFFORT_LOW,
                    "dependency": f"Measure Post-Implementation Emissions for {priority.title}",
                    "prerequisite": "Measurement record complete.",
                    "required_data": "Verification documentation.",
                    "measurement_method": DEFAULT_MEASUREMENT_METHOD,
                    "verification_method": DEFAULT_VERIFICATION_METHOD,
                    "status": ITEM_STATUS_NOT_STARTED,
                    "evidence_reference": priority.source_reference,
                    "reason": "Finalize verification of reduction.",
                    "limitation": "Third-party audit recommended.",
                })

        # Combine items in phase sequence and assign sequence numbers
        all_ordered = p1_items + p2_items + p3_items + p4_items

        for idx, item_data in enumerate(all_ordered, start=1):
            db_item = ReductionRoadmapItem(
                roadmap_id=roadmap.id,
                sequence=idx,
                phase=item_data["phase"],
                title=item_data["title"],
                action_type=item_data["action_type"],
                priority_id=item_data["priority_id"],
                opportunity_id=item_data["opportunity_id"],
                project_id=item_data["project_id"],
                category=item_data["category"],
                scope=item_data["scope"],
                current_emissions_kgco2e=item_data["current_emissions_kgco2e"],
                current_emissions_tco2e=item_data["current_emissions_tco2e"],
                target_contribution_kgco2e=item_data["target_contribution_kgco2e"],
                target_contribution_tco2e=item_data["target_contribution_tco2e"],
                contribution_status=item_data["contribution_status"],
                priority=item_data["priority"],
                effort_level=item_data["effort_level"],
                dependency=item_data["dependency"],
                prerequisite=item_data["prerequisite"],
                required_data=item_data["required_data"],
                measurement_method=item_data["measurement_method"],
                verification_method=item_data["verification_method"],
                status=item_data["status"],
                evidence_reference=item_data["evidence_reference"],
                reason=item_data["reason"],
                limitation=item_data["limitation"],
            )
            db.add(db_item)

        db.flush()

    # ==========================================================================
    # 3. GETTERS, QUERIES & UPDATES
    # ==========================================================================

    def get_roadmap(self, db: Session, roadmap_id: int) -> Optional[ReductionRoadmap]:
        """
        Retrieves a roadmap with items and events populated.
        """
        return db.query(ReductionRoadmap).filter(ReductionRoadmap.id == roadmap_id).first()

    def get_roadmap_by_code(self, db: Session, roadmap_code: str) -> Optional[ReductionRoadmap]:
        """
        Retrieves a roadmap by its unique roadmap_code.
        """
        return db.query(ReductionRoadmap).filter(ReductionRoadmap.roadmap_code == roadmap_code).first()

    def list_roadmaps(
        self,
        db: Session,
        document_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[ReductionRoadmap]:
        """
        Lists roadmaps with optional filters.
        """
        query = db.query(ReductionRoadmap)
        if document_id is not None:
            query = query.filter(ReductionRoadmap.document_id == document_id)
        if status is not None:
            query = query.filter(ReductionRoadmap.status == status)

        return query.order_by(ReductionRoadmap.created_at.desc()).all()

    def update_roadmap(
        self,
        db: Session,
        roadmap_id: int,
        name: Optional[str] = None,
        status: Optional[str] = None,
        confidence: Optional[str] = None,
        target_year: Optional[int] = None,
        target_period: Optional[str] = None,
    ) -> ReductionRoadmap:
        """
        Updates metadata or status for a roadmap.
        """
        roadmap = db.query(ReductionRoadmap).filter(ReductionRoadmap.id == roadmap_id).first()
        if not roadmap:
            raise ValueError(f"Roadmap #{roadmap_id} not found")

        old_status = roadmap.status

        if name is not None:
            roadmap.name = name
        if confidence is not None:
            roadmap.confidence = confidence
        if target_year is not None:
            roadmap.target_year = target_year
        if target_period is not None:
            roadmap.target_period = target_period
        if status is not None and status != old_status:
            roadmap.status = status
            self._record_event(
                db=db,
                roadmap_id=roadmap.id,
                event_type=EVENT_TYPE_STATUS_CHANGED,
                old_status=old_status,
                new_status=status,
                actor="USER",
                notes=f"Roadmap status changed from {old_status} to {status}."
            )

        db.commit()
        db.refresh(roadmap)
        return roadmap

    def update_item_status(
        self,
        db: Session,
        roadmap_id: int,
        item_id: int,
        new_status: str,
        notes: Optional[str] = None
    ) -> ReductionRoadmapItem:
        """
        Updates the execution status of an individual roadmap item and records an audit event.
        """
        item = db.query(ReductionRoadmapItem).filter(
            ReductionRoadmapItem.id == item_id,
            ReductionRoadmapItem.roadmap_id == roadmap_id
        ).first()
        if not item:
            raise ValueError(f"Roadmap item #{item_id} not found in roadmap #{roadmap_id}")

        old_status = item.status
        item.status = new_status

        self._record_event(
            db=db,
            roadmap_id=roadmap_id,
            event_type=EVENT_TYPE_ITEM_STATUS_CHANGED,
            old_status=old_status,
            new_status=new_status,
            actor="USER",
            notes=notes or f"Item #{item.sequence} ('{item.title}') status changed from {old_status} to {new_status}."
        )

        db.commit()
        db.refresh(item)
        return item

    # ==========================================================================
    # 4. PROGRESS CALCULATION (Roadmap Progress vs Emissions Progress)
    # ==========================================================================

    def calculate_progress(self, db: Session, roadmap_id: int) -> Dict[str, Any]:
        """
        Computes deterministic roadmap progress (actions completed) vs emissions reduction progress (accounting actuals).
        """
        roadmap = self.get_roadmap(db=db, roadmap_id=roadmap_id)
        if not roadmap:
            raise ValueError(f"Roadmap #{roadmap_id} not found")

        items = roadmap.items or []
        total_items = len(items)
        completed_items = sum(1 for i in items if i.status == ITEM_STATUS_COMPLETED)
        in_progress_items = sum(1 for i in items if i.status == ITEM_STATUS_IN_PROGRESS)
        blocked_items = sum(1 for i in items if i.status == ITEM_STATUS_BLOCKED)
        not_started_items = sum(1 for i in items if i.status == ITEM_STATUS_NOT_STARTED)

        roadmap_pct = (completed_items / total_items * 100.0) if total_items > 0 else 0.0

        # Emissions Reduction Progress from latest POSTED actuals
        query = db.query(CarbonLedgerEntry).filter(
            CarbonLedgerEntry.accounting_status == "POSTED"
        )
        if roadmap.document_id is not None:
            query = query.filter(CarbonLedgerEntry.document_id == roadmap.document_id)

        all_entries = query.all()

        # Group by reporting_period
        by_period: Dict[str, List[CarbonLedgerEntry]] = {}
        for e in all_entries:
            p = e.reporting_period or "UNSPECIFIED"
            if p not in by_period:
                by_period[p] = []
            by_period[p].append(e)

        valid_periods = [p for p in by_period.keys() if p != "UNSPECIFIED"]
        valid_periods.sort(reverse=True)

        emissions_progress_status = "INSUFFICIENT_POST_PROJECT_DATA"
        actual_change_pct = None
        actual_change_tco2e = None
        latest_period = None
        latest_emissions_tco2e = None

        if len(valid_periods) >= 2:
            latest_period = valid_periods[0]
            if latest_period != roadmap.baseline_period:
                latest_entries = by_period[latest_period]
                latest_kg = sum(Decimal(str(e.calculated_co2e or 0)) for e in latest_entries)
                latest_t = latest_kg / Decimal("1000.0")
                latest_emissions_tco2e = float(latest_t)

                b_t = Decimal(str(roadmap.baseline_emissions_tco2e or 0))
                if b_t > Decimal("0.0"):
                    diff_t = latest_t - b_t
                    actual_change_tco2e = float(diff_t)
                    actual_change_pct = float((diff_t / b_t) * Decimal("100.0"))
                    emissions_progress_status = "OBSERVED_ACTUAL_CHANGE"

        return {
            "roadmap_id": roadmap.id,
            "roadmap_code": roadmap.roadmap_code,
            "target_reduction_percent": float(roadmap.target_reduction_percent),
            "baseline_emissions_tco2e": float(roadmap.baseline_emissions_tco2e),
            "target_emissions_tco2e": float(roadmap.target_emissions_tco2e),
            "reduction_gap_tco2e": float(roadmap.reduction_gap_tco2e),
            "total_items": total_items,
            "completed_items": completed_items,
            "in_progress_items": in_progress_items,
            "blocked_items": blocked_items,
            "not_started_items": not_started_items,
            "roadmap_progress_percent": round(roadmap_pct, 2),
            "emissions_progress_status": emissions_progress_status,
            "actual_change_percent": round(actual_change_pct, 2) if actual_change_pct is not None else None,
            "actual_change_tco2e": round(actual_change_tco2e, 6) if actual_change_tco2e is not None else None,
            "latest_actual_period": latest_period,
            "latest_actual_emissions_tco2e": latest_emissions_tco2e,
            "feasibility_status": roadmap.target_status,
            "feasibility_explanation": roadmap.feasibility_explanation or DEFAULT_FEASIBILITY_NOTE,
        }

    # ==========================================================================
    # 5. AUDIT EVENT RECORDER
    # ==========================================================================

    def _record_event(
        self,
        db: Session,
        roadmap_id: int,
        event_type: str,
        old_status: Optional[str],
        new_status: Optional[str],
        actor: str = "SYSTEM",
        notes: Optional[str] = None
    ) -> ReductionRoadmapEvent:
        event = ReductionRoadmapEvent(
            roadmap_id=roadmap_id,
            event_type=event_type,
            old_status=old_status,
            new_status=new_status,
            actor=actor,
            notes=notes,
            created_at=datetime.utcnow(),
        )
        db.add(event)
        db.flush()
        return event

    def get_roadmap_events(self, db: Session, roadmap_id: int) -> List[ReductionRoadmapEvent]:
        """
        Returns full audit event history for a roadmap.
        """
        return db.query(ReductionRoadmapEvent).filter(
            ReductionRoadmapEvent.roadmap_id == roadmap_id
        ).order_by(ReductionRoadmapEvent.created_at.asc()).all()
