"""
services/reduction_opportunity.py — Deterministic Carbon Reduction Opportunity Engine (Step 16).

Identifies evidence-backed operational investigation opportunities exclusively from POSTED CarbonLedgerEntry data and data coverage indicators.
ZERO LLM calls. ZERO recalculation of emissions. ZERO invented reduction % or monetary savings.
"""
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.models.reduction_opportunity import ReductionOpportunity
from backend.app.models.carbon_ledger import CarbonLedgerEntry
from backend.app.models.carbon_calculation import CarbonCalculation
from backend.app.models.document import Document
from backend.app.services.carbon_dashboard import carbon_dashboard_service

logger = logging.getLogger("senseible-reduction-opportunity-service")


class ReductionOpportunityService:
    """
    Deterministic Reduction Opportunity Engine.
    Evaluates POSTED accounting ledger records and coverage audit trails to formulate investigation opportunities.
    """

    def __init__(self):
        self.opportunity_engine_version = "1.0"

    def generate_opportunities(
        self,
        db: Session,
        document_id: Optional[int] = None,
    ) -> List[ReductionOpportunity]:
        """
        Deterministically evaluates ledger records and produces deduplicated reduction opportunities.
        """
        generated: List[ReductionOpportunity] = []

        # 1. Fetch dashboard analytics for the scope
        summary = carbon_dashboard_service.get_dashboard_summary(db, document_id=document_id)
        scopes = carbon_dashboard_service.get_scope_breakdown(db, document_id=document_id)
        activities = carbon_dashboard_service.get_activity_breakdown(db, document_id=document_id)
        trends = carbon_dashboard_service.get_trends(db, document_id=document_id)
        coverage = carbon_dashboard_service.get_data_coverage(db, document_id=document_id)

        doc_suffix = f"DOC_{document_id}" if document_id is not None else "GLOBAL"

        total_kg = Decimal(str(summary.total_calculated_co2e_kg)) if summary.total_calculated_co2e_kg is not None else Decimal("0.0")

        # ------------------------------------------------------------------
        # RULE A: HIGH EMISSION SOURCES / DOMINANT SCOPE & ACTIVITIES
        # ------------------------------------------------------------------
        if total_kg > Decimal("0.0") and activities.items:
            # Top activity
            top_act = activities.items[0]
            top_kg = Decimal(str(top_act.co2e_kg))
            top_pct = Decimal(str(top_act.percentage_of_total)) if top_act.percentage_of_total is not None else Decimal("0.0")

            # Look up primary ledger entry for evidence
            led_query = db.query(CarbonLedgerEntry).filter(
                CarbonLedgerEntry.accounting_status == "POSTED",
                CarbonLedgerEntry.activity_type == top_act.activity_type
            )
            if document_id is not None:
                led_query = led_query.filter(CarbonLedgerEntry.document_id == document_id)
            primary_led = led_query.order_by(desc(CarbonLedgerEntry.calculated_co2e)).first()

            if top_act.category == "ENERGY" or "electricity" in top_act.activity_type:
                code = f"ENERGY_GRID_DOMINANT_{doc_suffix}"
                priority = "HIGH" if top_pct >= Decimal("50.0") else "MEDIUM"
                opp = self._upsert_opportunity(
                    db=db,
                    opportunity_code=code,
                    title="Investigate Grid Electricity Consumption & Procurement",
                    description=(
                        f"Grid electricity is the primary calculated emission source, accounting for "
                        f"{top_act.co2e_t:.4f} tCO2e ({top_pct:.1f}% of total calculated footprint)."
                    ),
                    category="ENERGY",
                    activity_type=top_act.activity_type,
                    scope=top_act.scope or "SCOPE_2",
                    priority=priority,
                    trigger_type="HIGH_ENERGY_USE" if top_pct >= Decimal("50.0") else "HIGH_EMISSION_SOURCE",
                    evidence_document_id=primary_led.document_id if primary_led else document_id,
                    evidence_ledger_entry_id=primary_led.id if primary_led else None,
                    current_value=Decimal(str(primary_led.quantity)) if primary_led and primary_led.quantity is not None else None,
                    current_unit=primary_led.activity_unit if primary_led else "kWh",
                    calculated_co2e=top_kg,
                    calculated_co2e_unit="kgCO2e",
                    rationale=(
                        f"Dominant emission source rule: Activity '{top_act.activity_type}' accounts for "
                        f"{top_pct:.1f}% of total posted emissions (threshold: >= 50.0% for HIGH priority)."
                    ),
                    recommended_action=(
                        "Investigate electrical equipment operational efficiency, HVAC scheduling, power factor optimization, "
                        "and feasibility of renewable electricity tariffs or on-site solar generation."
                    ),
                    limitations=(
                        "Recommendation indicates an area for operational investigation. It is not a guaranteed emission reduction."
                    ),
                )
                generated.append(opp)

            elif top_act.category == "FUEL" or "diesel" in top_act.activity_type:
                code = f"FUEL_DIESEL_DOMINANT_{doc_suffix}"
                priority = "HIGH" if top_pct >= Decimal("50.0") else "MEDIUM"
                opp = self._upsert_opportunity(
                    db=db,
                    opportunity_code=code,
                    title="Investigate Stationary & Mobile Fuel Consumption",
                    description=(
                        f"Fuel combustion ({top_act.activity_type}) is a major emission contributor, generating "
                        f"{top_act.co2e_t:.4f} tCO2e ({top_pct:.1f}% of total calculated footprint)."
                    ),
                    category="FUEL",
                    activity_type=top_act.activity_type,
                    scope=top_act.scope or "SCOPE_1",
                    priority=priority,
                    trigger_type="HIGH_FUEL_USE",
                    evidence_document_id=primary_led.document_id if primary_led else document_id,
                    evidence_ledger_entry_id=primary_led.id if primary_led else None,
                    current_value=Decimal(str(primary_led.quantity)) if primary_led and primary_led.quantity is not None else None,
                    current_unit=primary_led.activity_unit if primary_led else "L",
                    calculated_co2e=top_kg,
                    calculated_co2e_unit="kgCO2e",
                    rationale=(
                        f"Fuel source rule: Activity '{top_act.activity_type}' contributes {top_pct:.1f}% "
                        f"to total calculated emissions."
                    ),
                    recommended_action=(
                        "Conduct generator and vehicle maintenance audits, assess runtime logs, eliminate unnecessary idling, "
                        "and evaluate feasibility of equipment electrification or cleaner alternative fuels."
                    ),
                    limitations=(
                        "Recommendation indicates an area for operational investigation. It is not a guaranteed emission reduction."
                    ),
                )
                generated.append(opp)

        # ------------------------------------------------------------------
        # RULE B: SECONDARY FUEL OPPORTUNITY (Scope 1 Diesel when Scope 2 is primary)
        # ------------------------------------------------------------------
        for act in activities.items[1:]:
            if "diesel" in act.activity_type or act.category == "FUEL":
                code = f"FUEL_DIESEL_SCOPE1_{doc_suffix}"
                act_kg = Decimal(str(act.co2e_kg))
                act_pct = Decimal(str(act.percentage_of_total)) if act.percentage_of_total is not None else Decimal("0.0")

                led_rec = db.query(CarbonLedgerEntry).filter(
                    CarbonLedgerEntry.accounting_status == "POSTED",
                    CarbonLedgerEntry.activity_type == act.activity_type
                )
                if document_id is not None:
                    led_rec = led_rec.filter(CarbonLedgerEntry.document_id == document_id)
                led_match = led_rec.first()

                opp = self._upsert_opportunity(
                    db=db,
                    opportunity_code=code,
                    title="Audit Diesel Fuel Use & Generator Run Hours",
                    description=(
                        f"Diesel fuel combustion generates {act.co2e_t:.4f} tCO2e of direct Scope 1 emissions "
                        f"({act_pct:.1f}% of total calculated footprint)."
                    ),
                    category="FUEL",
                    activity_type=act.activity_type,
                    scope="SCOPE_1",
                    priority="MEDIUM" if act_pct >= Decimal("2.0") else "LOW",
                    trigger_type="HIGH_FUEL_USE",
                    evidence_document_id=led_match.document_id if led_match else document_id,
                    evidence_ledger_entry_id=led_match.id if led_match else None,
                    current_value=Decimal(str(led_match.quantity)) if led_match and led_match.quantity is not None else None,
                    current_unit=led_match.activity_unit if led_match else "L",
                    calculated_co2e=act_kg,
                    calculated_co2e_unit="kgCO2e",
                    rationale=(
                        f"Direct combustion rule: Diesel is an active Scope 1 emission source contributing "
                        f"{act_pct:.1f}% to posted footprint."
                    ),
                    recommended_action=(
                        "Monitor specific diesel consumption (L/hour or L/kWh generated), perform preventive engine maintenance, "
                        "and minimize backup generator reliance through grid power reliability improvements."
                    ),
                    limitations=(
                        "Recommendation indicates an area for operational investigation. It is not a guaranteed emission reduction."
                    ),
                )
                generated.append(opp)

        # ------------------------------------------------------------------
        # RULE C: HISTORICAL INCREASE DETECTION (> 10% and > 25%)
        # ------------------------------------------------------------------
        if trends.comparison and trends.comparison.comparison_available:
            comp = trends.comparison
            pct_change = comp.percentage_change
            abs_change = comp.absolute_change_t

            if pct_change is not None and pct_change >= 10.0:
                code = f"EMISSIONS_INCREASE_{comp.previous_period}_{comp.current_period}_{doc_suffix}"
                priority = "HIGH" if pct_change >= 25.0 else "MEDIUM"
                opp = self._upsert_opportunity(
                    db=db,
                    opportunity_code=code,
                    title=f"Investigate Footprint Increase in {comp.current_period}",
                    description=(
                        f"Calculated emissions increased by {pct_change:.1f}% ({abs_change:+.4f} tCO2e) from "
                        f"{comp.previous_period} to {comp.current_period}."
                    ),
                    category="EMISSIONS",
                    scope=None,
                    priority=priority,
                    trigger_type="INCREASING_EMISSIONS",
                    evidence_document_id=document_id,
                    previous_value=Decimal(str(comp.previous_co2e_t)) if comp.previous_co2e_t is not None else None,
                    previous_unit="tCO2e",
                    current_value=Decimal(str(comp.current_co2e_t)) if comp.current_co2e_t is not None else None,
                    current_unit="tCO2e",
                    change_absolute=Decimal(str(abs_change)) if abs_change is not None else None,
                    change_percentage=Decimal(str(pct_change)) if pct_change is not None else None,
                    rationale=(
                        f"Historical period change rule: Increase of {pct_change:.1f}% exceeds detection "
                        f"threshold (>= 10.0% for MEDIUM, >= 25.0% for HIGH)."
                    ),
                    recommended_action=(
                        "Review operational activity data and utility logs for the period to identify specific equipment or operational drivers of the increase."
                    ),
                    limitations=(
                        "Recommendation indicates an area for operational investigation. It is not a guaranteed emission reduction."
                    ),
                )
                generated.append(opp)

        # ------------------------------------------------------------------
        # RULE D: REPEATED 3-PERIOD CONSECUTIVE INCREASE
        # ------------------------------------------------------------------
        if len(trends.periods) >= 3:
            p1, p2, p3 = trends.periods[-3], trends.periods[-2], trends.periods[-1]
            if p1.total_co2e_t < p2.total_co2e_t < p3.total_co2e_t:
                code = f"REPEATED_INCREASE_{p1.reporting_period}_{p2.reporting_period}_{p3.reporting_period}_{doc_suffix}"
                opp = self._upsert_opportunity(
                    db=db,
                    opportunity_code=code,
                    title="Address Multi-Period Emission Upward Trend",
                    description=(
                        f"Calculated emissions increased across three consecutive reporting periods: "
                        f"{p1.reporting_period} ({p1.total_co2e_t:.4f} t) → {p2.reporting_period} ({p2.total_co2e_t:.4f} t) → {p3.reporting_period} ({p3.total_co2e_t:.4f} t)."
                    ),
                    category="EMISSIONS",
                    scope=None,
                    priority="HIGH",
                    trigger_type="REPEATED_INCREASE",
                    evidence_document_id=document_id,
                    previous_value=Decimal(str(p1.total_co2e_t)),
                    previous_unit="tCO2e",
                    current_value=Decimal(str(p3.total_co2e_t)),
                    current_unit="tCO2e",
                    change_absolute=Decimal(str(p3.total_co2e_t - p1.total_co2e_t)),
                    change_percentage=Decimal(str(((p3.total_co2e_t - p1.total_co2e_t) / p1.total_co2e_t) * 100)) if p1.total_co2e_t > 0 else None,
                    rationale=(
                        "Consecutive increase rule: 3 consecutive reporting periods exhibit monotonically increasing emissions."
                    ),
                    recommended_action=(
                        "Conduct a comprehensive energy and operational audit to halt sustained emissions growth and establish baseline controls."
                    ),
                    limitations=(
                        "Recommendation indicates an area for operational investigation. It is not a guaranteed emission reduction."
                    ),
                )
                generated.append(opp)

        # ------------------------------------------------------------------
        # RULE E: DATA QUALITY & UNRESOLVED FACTOR OPPORTUNITIES
        # ------------------------------------------------------------------
        if coverage.no_factor_records > 0 or coverage.ineligible_records > 0:
            # Check for solar or other uncredited zero-emission / no-factor items
            solar_calc = db.query(CarbonCalculation).filter(
                CarbonCalculation.status == "NO_FACTOR"
            )
            if document_id is not None:
                solar_calc = solar_calc.filter(CarbonCalculation.document_id == document_id)
            solar_match = solar_calc.first()

            if solar_match:
                code = f"DATA_NO_FACTOR_SOLAR_{doc_suffix}"
                opp = self._upsert_opportunity(
                    db=db,
                    opportunity_code=code,
                    title="Register On-Site Solar Generation Factor & Accounting Rule",
                    description=(
                        f"On-site solar generation ({float(solar_match.quantity):.1f} {solar_match.activity_unit}) was excluded from accounting "
                        "because no regional emission avoidance factor or registry rule was matched."
                    ),
                    category="DATA_QUALITY",
                    activity_type=solar_match.activity_type,
                    scope="SCOPE_2",
                    priority="HIGH",
                    trigger_type="UNRESOLVED_FACTOR",
                    evidence_document_id=solar_match.document_id,
                    current_value=solar_match.quantity,
                    current_unit=solar_match.activity_unit,
                    rationale=(
                        "Data quality rule: Renewable on-site solar activity exists but lacks matched emission factor, "
                        "limiting complete avoided-emissions accounting."
                    ),
                    recommended_action=(
                        "Configure and register appropriate grid-displacement factor or verify net-metering credits in the Emission Factor Registry."
                    ),
                    limitations=(
                        "Excluded records are not treated as zero emissions. Factored displacement requires verified registry configuration."
                    ),
                )
                generated.append(opp)

        return generated

    def _upsert_opportunity(
        self,
        db: Session,
        opportunity_code: str,
        title: str,
        description: str,
        category: str,
        priority: str,
        trigger_type: str,
        rationale: str,
        recommended_action: str,
        limitations: str,
        activity_type: Optional[str] = None,
        scope: Optional[str] = None,
        evidence_document_id: Optional[int] = None,
        evidence_metric_id: Optional[int] = None,
        evidence_ledger_entry_id: Optional[int] = None,
        current_value: Optional[Decimal] = None,
        current_unit: Optional[str] = None,
        previous_value: Optional[Decimal] = None,
        previous_unit: Optional[str] = None,
        change_absolute: Optional[Decimal] = None,
        change_percentage: Optional[Decimal] = None,
        calculated_co2e: Optional[Decimal] = None,
        calculated_co2e_unit: str = "kgCO2e",
    ) -> ReductionOpportunity:
        """
        Idempotent upsert of ReductionOpportunity based on opportunity_code.
        Preserves non-OPEN user statuses (ACKNOWLEDGED, IN_PROGRESS, COMPLETED, DISMISSED).
        """
        existing = db.query(ReductionOpportunity).filter_by(opportunity_code=opportunity_code).first()

        if existing:
            # Update fields in-place
            existing.title = title
            existing.description = description
            existing.category = category
            existing.activity_type = activity_type
            existing.scope = scope
            existing.priority = priority
            existing.trigger_type = trigger_type
            existing.evidence_document_id = evidence_document_id
            existing.evidence_metric_id = evidence_metric_id
            existing.evidence_ledger_entry_id = evidence_ledger_entry_id
            existing.current_value = current_value
            existing.current_unit = current_unit
            existing.previous_value = previous_value
            existing.previous_unit = previous_unit
            existing.change_absolute = change_absolute
            existing.change_percentage = change_percentage
            existing.calculated_co2e = calculated_co2e
            existing.calculated_co2e_unit = calculated_co2e_unit
            existing.rationale = rationale
            existing.recommended_action = recommended_action
            existing.limitations = limitations
            existing.detection_version = self.opportunity_engine_version
            db.commit()
            db.refresh(existing)
            return existing

        # Create new opportunity
        new_opp = ReductionOpportunity(
            opportunity_code=opportunity_code,
            title=title,
            description=description,
            category=category,
            activity_type=activity_type,
            scope=scope,
            priority=priority,
            trigger_type=trigger_type,
            status="OPEN",
            evidence_document_id=evidence_document_id,
            evidence_metric_id=evidence_metric_id,
            evidence_ledger_entry_id=evidence_ledger_entry_id,
            current_value=current_value,
            current_unit=current_unit,
            previous_value=previous_value,
            previous_unit=previous_unit,
            change_absolute=change_absolute,
            change_percentage=change_percentage,
            calculated_co2e=calculated_co2e,
            calculated_co2e_unit=calculated_co2e_unit,
            rationale=rationale,
            recommended_action=recommended_action,
            limitations=limitations,
            detection_version=self.opportunity_engine_version,
        )
        db.add(new_opp)
        db.commit()
        db.refresh(new_opp)
        return new_opp

    def get_opportunities(
        self,
        db: Session,
        category: Optional[str] = None,
        scope: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        activity_type: Optional[str] = None,
        document_id: Optional[int] = None,
    ) -> List[ReductionOpportunity]:
        """
        Query and filter reduction opportunities.
        """
        query = db.query(ReductionOpportunity)
        if document_id is not None:
            query = query.filter(ReductionOpportunity.evidence_document_id == document_id)
        if category:
            query = query.filter(ReductionOpportunity.category == category.strip().upper())
        if scope:
            query = query.filter(ReductionOpportunity.scope == scope.strip().upper())
        if priority:
            query = query.filter(ReductionOpportunity.priority == priority.strip().upper())
        if status:
            query = query.filter(ReductionOpportunity.status == status.strip().upper())
        if activity_type:
            query = query.filter(ReductionOpportunity.activity_type == activity_type.strip())

        # Sort priority HIGH -> MEDIUM -> LOW, then newest
        priority_order = {"HIGH": 1, "MEDIUM": 2, "LOW": 3}
        opps = query.all()
        return sorted(opps, key=lambda x: (priority_order.get(x.priority, 4), x.id))

    def get_opportunity(self, db: Session, opp_id: int) -> Optional[ReductionOpportunity]:
        return db.query(ReductionOpportunity).filter(ReductionOpportunity.id == opp_id).first()

    def update_status(self, db: Session, opp_id: int, new_status: str) -> Optional[ReductionOpportunity]:
        """
        Update status of an opportunity with validation.
        """
        valid_statuses = {"OPEN", "ACKNOWLEDGED", "IN_PROGRESS", "COMPLETED", "DISMISSED"}
        st = new_status.strip().upper()
        if st not in valid_statuses:
            raise ValueError(f"Invalid status '{new_status}'. Must be one of {valid_statuses}")

        opp = self.get_opportunity(db, opp_id)
        if not opp:
            return None

        opp.status = st
        db.commit()
        db.refresh(opp)
        return opp

    def get_summary(self, db: Session) -> Dict[str, Any]:
        """
        Aggregate count summary of all reduction opportunities.
        """
        all_opps = db.query(ReductionOpportunity).all()
        total = len(all_opps)

        open_cnt = sum(1 for o in all_opps if o.status == "OPEN")
        ack_cnt = sum(1 for o in all_opps if o.status == "ACKNOWLEDGED")
        prog_cnt = sum(1 for o in all_opps if o.status == "IN_PROGRESS")
        comp_cnt = sum(1 for o in all_opps if o.status == "COMPLETED")
        dism_cnt = sum(1 for o in all_opps if o.status == "DISMISSED")

        high_cnt = sum(1 for o in all_opps if o.priority == "HIGH")
        med_cnt = sum(1 for o in all_opps if o.priority == "MEDIUM")
        low_cnt = sum(1 for o in all_opps if o.priority == "LOW")

        by_cat: Dict[str, int] = {}
        by_sc: Dict[str, int] = {}

        for o in all_opps:
            by_cat[o.category] = by_cat.get(o.category, 0) + 1
            if o.scope:
                by_sc[o.scope] = by_sc.get(o.scope, 0) + 1

        return {
            "total_opportunities": total,
            "open_count": open_cnt,
            "acknowledged_count": ack_cnt,
            "in_progress_count": prog_cnt,
            "completed_count": comp_cnt,
            "dismissed_count": dism_cnt,
            "high_priority_count": high_cnt,
            "medium_priority_count": med_cnt,
            "low_priority_count": low_cnt,
            "by_category": by_cat,
            "by_scope": by_sc,
        }


reduction_opportunity_service = ReductionOpportunityService()
