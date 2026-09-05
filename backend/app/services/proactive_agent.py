"""
services/proactive_agent.py — Deterministic Proactive AI Sustainability Agent Engine (Step 23 & Improvement Patches).

Orchestrates decision intelligence across:
- Step 14 POSTED CarbonLedgerEntry (Numerical Truth Level 1)
- Step 22A Reduction Opportunity Intelligence (Single Source of Priority Truth)
- Step 22B Personalized Reduction Roadmap Engine
- Step 22C Emissions Scenario & What-If Engine
- Step 21 Predictive Emission Analytics Engine
- Step 17/18 Reduction Projects & M&V Workflow
- Step 16 Compliance Reports & Data Quality Review Flags

CRITICAL SAFETY & NUMERICAL BOUNDARIES:
- Strictly deterministic decision support layer.
- Never mutates historical ledger entries or recalculates emissions independently.
- Never invents numbers, savings, ROI, payback periods, or operational causality.
- Inherits priority scores directly from Step 22A without overriding or re-ranking.
- Strict queue separation: Queue A (REDUCTION) vs Queue B (DATA_QUALITY).
- Implements deterministic Action Dependency Graph (parent/blocked/ready).
- Explicit labeling: ACTUAL, FORECAST — NOT ACTUAL, SCENARIO — NOT ACTUAL.
"""
import hashlib
import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from backend.app.models.proactive_agent import AgentAction, AgentActionEvent
from backend.app.models.carbon_ledger import CarbonLedgerEntry
from backend.app.models.carbon_calculation import CarbonCalculation
from backend.app.models.activity_data import ActivityData
from backend.app.models.emission_scenario import EmissionScenario
from backend.app.models.reduction_roadmap import ReductionRoadmap, ReductionRoadmapItem
from backend.app.models.reduction_intelligence import ReductionPriority
from backend.app.models.reduction_project import ReductionProject
from backend.app.models.reduction_measurement import ReductionMeasurement
from backend.app.models.compliance_report import ComplianceReport
from backend.app.models.document import Document
from backend.app.services.reduction_intelligence import reduction_intelligence_service
from backend.app.services.reduction_roadmap import ReductionRoadmapService
from backend.app.services.emission_scenario import EmissionScenarioService
from backend.app.services.emission_forecasting import emission_forecasting_service
from backend.app.schemas.emission_forecast import ForecastRequest

logger = logging.getLogger("senseible-proactive-agent")

AGENT_VERSION = "1.0"

reduction_roadmap_service = ReductionRoadmapService()
emission_scenario_service = EmissionScenarioService()


class AgentRunResult(dict):
    """Dict compatible with AgentRunResponse, but also iterable like a list of actions."""
    def __init__(self, data: dict, actions: List[AgentAction]):
        super().__init__(data)
        self.actions = actions

    def __iter__(self):
        return iter(self.actions)

    def __len__(self):
        return len(self.actions)

    def __getitem__(self, item):
        if isinstance(item, int):
            return self.actions[item]
        return super().__getitem__(item)


class BriefResult(dict):
    """Dict compatible with AgentBriefResponse, allowing attribute access."""
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)


class ExplanationResult(dict):
    """Dict compatible with AgentExplanationResponse, allowing attribute access."""
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)


class ProactiveAgentService:
    """
    Deterministic Decision Support & Orchestration Service.
    """

    def __init__(self, db: Optional[Session] = None):
        self.agent_version = AGENT_VERSION
        self._last_evaluated: Optional[datetime] = None
        self.db = db

    def get_last_evaluated(self) -> Optional[datetime]:
        return self._last_evaluated

    def _resolve_db_and_id(self, args, kwargs, id_name="action_id"):
        db = None
        target_id = None
        if len(args) >= 2:
            db = args[0]
            target_id = args[1]
        elif len(args) == 1:
            if isinstance(args[0], (int, str)):
                target_id = int(args[0])
                db = self.db
            else:
                db = args[0]
        if target_id is None:
            target_id = kwargs.pop(id_name, None)
        if db is None:
            db = kwargs.pop("db", None) or self.db
        if db is None:
            raise ValueError("Database session required")
        return db, target_id

    # -------------------------------------------------------------------------
    # 1. EVALUATION & ACTION GENERATION (Idempotent)
    # -------------------------------------------------------------------------

    def evaluate_actions(
        self,
        db: Optional[Session] = None,
        document_id: Optional[int] = None,
        force_recalculate: bool = False
    ) -> Any:
        """
        Deterministically evaluates candidate actions across all subsystems.
        Applies Step 22A priority inheritance, queue separation, dependency linking,
        and idempotent deduplication.
        """
        db = db or self.db
        if not db:
            raise ValueError("Database session is required")
        now = datetime.utcnow()
        self._last_evaluated = now

        candidate_actions: List[Dict[str, Any]] = []

        # A. Evaluate Step 22A Reduction Priorities (Single Source of Priority Truth, Patch 1)
        self._gather_reduction_intelligence_actions(db, document_id, candidate_actions)

        # B. Evaluate Step 22B Roadmap Milestones
        self._gather_roadmap_actions(db, document_id, candidate_actions)

        # C. Evaluate Data Quality: Unresolved Factors & Missing Activity Data (Queue B, Patch 2)
        factor_actions_map = self._gather_data_quality_factor_actions(db, document_id, candidate_actions)

        # D. Evaluate Step 22C Scenarios (Quantified vs Unquantifiable with Dependency Link, Patch 3)
        self._gather_scenario_actions(db, document_id, candidate_actions, factor_actions_map)

        # E. Evaluate Reduction Projects & Measurement / Verification Readiness
        self._gather_project_mv_actions(db, document_id, candidate_actions)

        # F. Evaluate Compliance Report Review Flags (Queue B)
        self._gather_compliance_actions(db, document_id, candidate_actions)

        # G. Evaluate Step 21 Predictive Forecast Signal (Labeled: FORECAST — NOT ACTUAL)
        self._gather_forecast_actions(db, document_id, candidate_actions)

        # Reconcile candidates with persistent AgentAction table (Idempotent Deduplication, Patch 7)
        actions_created = 0
        actions_updated = 0
        persisted_actions: List[AgentAction] = []

        for cand in candidate_actions:
            dedup_key = cand["dedup_key"]
            existing = db.query(AgentAction).filter(AgentAction.dedup_key == dedup_key).first()

            if existing:
                # Update attributes if open or in_progress without duplicating
                if existing.status in ("OPEN", "IN_PROGRESS"):
                    existing.title = cand["title"]
                    existing.summary = cand["summary"]
                    existing.why_it_matters = cand["why_it_matters"]
                    existing.recommended_action = cand["recommended_action"]
                    existing.what = cand.get("what")
                    existing.why = cand.get("why")
                    existing.next_step = cand.get("next_step")
                    existing.evidence = cand.get("evidence")
                    existing.follow_up = cand.get("follow_up")
                    existing.limitation = cand.get("limitation")
                    existing.priority = cand["priority"]
                    existing.priority_score = cand["priority_score"]
                    existing.priority_source = cand["priority_source"]
                    existing.deterministic_score = cand["deterministic_score"]
                    existing.metric_value = cand.get("metric_value")
                    existing.metric_unit = cand.get("metric_unit")
                    existing.evidence_reference = cand.get("evidence_reference")
                    if existing.dependency_status != "COMPLETED":
                        existing.dependency_status = cand.get("dependency_status", "NONE")
                    existing.updated_at = now
                    actions_updated += 1
                persisted_actions.append(existing)
            else:
                new_action = AgentAction(
                    document_id=cand.get("document_id"),
                    action_type=cand["action_type"],
                    category=cand["category"],
                    queue_type=cand.get("queue_type", "REDUCTION"),
                    priority=cand["priority"],
                    priority_score=cand["priority_score"],
                    priority_source=cand["priority_source"],
                    deterministic_score=cand["deterministic_score"],
                    title=cand["title"],
                    summary=cand["summary"],
                    why_it_matters=cand["why_it_matters"],
                    recommended_action=cand["recommended_action"],
                    what=cand.get("what"),
                    why=cand.get("why"),
                    next_step=cand.get("next_step"),
                    evidence=cand.get("evidence"),
                    follow_up=cand.get("follow_up"),
                    limitation=cand.get("limitation"),
                    parent_action_id=cand.get("parent_action_id"),
                    blocks_action_id=cand.get("blocks_action_id"),
                    dependency_status=cand.get("dependency_status", "NONE"),
                    source_type=cand["source_type"],
                    source_id=cand.get("source_id"),
                    source_document_id=cand.get("source_document_id"),
                    reporting_period=cand.get("reporting_period"),
                    metric_value=cand.get("metric_value"),
                    metric_unit=cand.get("metric_unit"),
                    evidence_reference=cand.get("evidence_reference"),
                    status="OPEN",
                    due_context=cand.get("due_context"),
                    dedup_key=dedup_key,
                    agent_version=self.agent_version,
                    created_at=now,
                    updated_at=now,
                )
                db.add(new_action)
                db.flush()

                # Audit Event: CREATED
                event = AgentActionEvent(
                    action_id=new_action.id,
                    event_type="CREATED",
                    previous_status=None,
                    new_status="OPEN",
                    actor_type="SYSTEM",
                    reason="Deterministic agent candidate generation",
                    created_at=now,
                )
                db.add(event)
                actions_created += 1
                persisted_actions.append(new_action)

        # Resolve inter-action dependency links for newly created items
        self._link_dependencies(db, persisted_actions)

        db.commit()

        total_active = db.query(AgentAction).filter(
            AgentAction.status.in_(["OPEN", "IN_PROGRESS"])
        ).count()

        all_actions = db.query(AgentAction).all()

        return AgentRunResult({
            "status": "SUCCESS",
            "actions_evaluated": len(candidate_actions),
            "new_actions_created": actions_created,
            "updated_actions": actions_updated,
            "active_actions_count": total_active,
            "last_evaluated": now,
            "agent_version": self.agent_version,
        }, all_actions)

    # -------------------------------------------------------------------------
    # 2. SUBSYSTEM CANDIDATE GATHERERS
    # -------------------------------------------------------------------------

    def _gather_reduction_intelligence_actions(
        self,
        db: Session,
        document_id: Optional[int],
        candidates: List[Dict[str, Any]]
    ):
        """
        Step 22A Reduction Priorities — SINGLE SOURCE OF PRIORITY TRUTH (Patch 1 & 2).
        Directly inherits priority_score and priority_level without recalculation.
        """
        existing_priorities = db.query(ReductionPriority)
        if document_id is not None:
            existing_priorities = existing_priorities.filter(ReductionPriority.document_id == document_id)
        priorities = existing_priorities.all()

        if not priorities:
            try:
                priorities = reduction_intelligence_service.evaluate_priorities(db, document_id=document_id)
            except Exception as e:
                logger.warning(f"Error evaluating reduction priorities: {e}")
                priorities = []

        for p in priorities:
            # Only generate actions for actionable priorities
            score = float(p.priority_score or 0.0)
            level = p.priority_level or "MEDIUM"

            # Format grounded contract (Patch 5)
            tco2e_val = float(p.current_emissions_tco2e or 0.0)
            what_text = f"{p.title} ({tco2e_val:.4f} tCO2e posted emissions)"
            why_text = f"{p.reason} (Authoritative 22A Score: {score:.1f}/100 - {level})"
            next_text = f"Initiate operational efficiency or procurement review for {p.activity_type or p.category}."
            evidence_text = f"Posted ledger records: {tco2e_val:.4f} tCO2e across Scope {p.scope or '2'}."
            follow_up_text = "Compare subsequent reporting period posted ledger entries against baseline."
            limitation_text = "This recommendation does not guarantee reduction; operational recommendations highlight reduction opportunities and verified savings require independent intervention and M&V."

            cond_code = f"22A_{p.priority_code or p.id}"
            dedup_key = self._build_dedup_key(
                "REDUCE_EMISSIONS", p.category or "EMISSIONS", "REDUCTION_PRIORITY",
                str(p.id), str(p.document_id or ""), cond_code
            )

            candidates.append({
                "document_id": p.document_id,
                "action_type": "REDUCE_EMISSIONS",
                "category": p.category or "ENERGY",
                "queue_type": "REDUCTION",  # Queue A (Patch 2)
                "priority": level,          # Inherited from 22A (Patch 1)
                "priority_score": score,    # Inherited from 22A (Patch 1)
                "priority_source": "REDUCTION_INTELLIGENCE",
                "deterministic_score": score,
                "title": f"Reduce {p.title}",
                "summary": p.reason,
                "why_it_matters": why_text,
                "recommended_action": next_text,
                "what": what_text,
                "why": why_text,
                "next_step": next_text,
                "evidence": evidence_text,
                "follow_up": follow_up_text,
                "limitation": limitation_text,
                "source_type": "REDUCTION_PRIORITY",
                "source_id": str(p.id),
                "source_document_id": p.document_id,
                "metric_value": tco2e_val,
                "metric_unit": "tCO2e",
                "evidence_reference": evidence_text,
                "dependency_status": "READY",
                "due_context": "Next reporting cycle",
                "dedup_key": dedup_key,
            })

    def _gather_roadmap_actions(
        self,
        db: Session,
        document_id: Optional[int],
        candidates: List[Dict[str, Any]]
    ):
        """
        Step 22B Roadmap Milestones — Actionable foundation milestones (Queue A).
        """
        try:
            roadmaps = reduction_roadmap_service.list_roadmaps(db, document_id=document_id)
        except Exception as e:
            logger.warning(f"Error fetching roadmaps: {e}")
            return

        for r in roadmaps:
            if not r.items:
                continue
            for item in r.items:
                if item.status == "COMPLETED":
                    continue
                # Focus on Phase 1 or high priority items
                if item.phase in ("PHASE_1_FOUNDATION", "PHASE_2_ACTION"):
                    is_p1 = item.phase == "PHASE_1_FOUNDATION"
                    p_score = 65.0 if is_p1 else 50.0
                    p_level = "HIGH" if is_p1 else "MEDIUM"

                    what_text = f"Roadmap Milestone: {item.title} ({item.phase})"
                    why_text = f"{item.reason or 'Foundational reduction step in active decarbonization roadmap.'}"
                    next_text = f"Execute milestone action: {item.action_type}."
                    evidence_text = f"Roadmap #{r.id} ({r.roadmap_code}) Item #{item.sequence}"
                    follow_up_text = "Mark roadmap item status as IN_PROGRESS / COMPLETED upon execution."
                    limitation_text = item.limitation or "Target contribution is modeled and contingent on implementation."

                    has_dep = bool(item.dependency and item.dependency.strip())
                    dep_status = "BLOCKED" if has_dep else "READY"

                    cond_code = f"ROADMAP_ITEM_{item.id}"
                    dedup_key = self._build_dedup_key(
                        "ROADMAP_MILESTONE", "ROADMAP", "ROADMAP_ITEM",
                        str(item.id), str(r.document_id or ""), cond_code
                    )

                    candidates.append({
                        "document_id": r.document_id,
                        "action_type": "ROADMAP_MILESTONE",
                        "category": "ROADMAP",
                        "queue_type": "REDUCTION",
                        "priority": p_level,
                        "priority_score": p_score,
                        "priority_source": "ROADMAP",
                        "deterministic_score": p_score,
                        "title": f"Milestone: {item.title}",
                        "summary": item.reason or item.title,
                        "why_it_matters": why_text,
                        "recommended_action": next_text,
                        "what": what_text,
                        "why": why_text,
                        "next_step": next_text,
                        "evidence": evidence_text,
                        "follow_up": follow_up_text,
                        "limitation": limitation_text,
                        "source_type": "ROADMAP_ITEM",
                        "source_id": str(item.id),
                        "source_document_id": r.document_id,
                        "dependency_status": dep_status,
                        "due_context": f"Phase {item.phase}",
                        "dedup_key": dedup_key,
                    })

    def _gather_data_quality_factor_actions(
        self,
        db: Session,
        document_id: Optional[int],
        candidates: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Data Quality Queue (Queue B, Patch 2).
        Identifies unquantified activities due to unresolved factors (e.g. Solar factor unresolved).
        A DATA_QUALITY blocker must NEVER automatically appear as an emissions reduction opportunity.
        Returns a mapping of activity_type -> dedup_key for dependency linking.
        """
        factor_actions_map = {}
        query = db.query(CarbonCalculation).filter(
            CarbonCalculation.status.in_(["NO_FACTOR", "MULTIPLE_FACTORS", "MISSING_GEOGRAPHY", "MISSING_YEAR"])
        )
        if document_id:
            query = query.filter(CarbonCalculation.document_id == document_id)

        unresolved_calcs = query.all()

        # Group by activity_type to deduplicate cleanly
        seen_types = set()
        for calc in unresolved_calcs:
            act_type = calc.activity_type or "unspecified"
            if act_type in seen_types:
                continue
            seen_types.add(act_type)

            cond_code = f"FACTOR_UNRESOLVED_{act_type}"
            dedup_key = self._build_dedup_key(
                "RESOLVE_FACTOR", "DATA_QUALITY", "EMISSION_FACTOR",
                str(calc.id), str(calc.document_id or ""), cond_code
            )
            factor_actions_map[act_type.lower()] = dedup_key

            qty_str = f"{float(calc.quantity):.2f} {calc.activity_unit}" if calc.quantity else "recorded quantity"
            what_text = f"Resolve emission factor for {act_type.replace('_', ' ')}"
            why_text = f"Activity data ({qty_str}) cannot be quantified without an authoritative emission factor. Missing factors are NOT treated as zero."
            next_text = f"Assign or resolve an authoritative emission factor for {act_type.replace('_', ' ')} in the Emission Factor Registry."
            evidence_text = f"CarbonCalculation #{calc.id} (Document #{calc.document_id}) - Status: {calc.status}"
            follow_up_text = "Recalculate affected calculations and dependent scenarios after factor resolution."
            limitation_text = "Emissions for this source remain unquantified until factor is resolved."

            candidates.append({
                "document_id": calc.document_id,
                "action_type": "RESOLVE_EMISSION_FACTOR",
                "category": "DATA_QUALITY",
                "queue_type": "DATA_QUALITY",  # Queue B (Patch 2)
                "priority": "HIGH",
                "priority_score": 85.0,
                "priority_source": "DATA_QUALITY_ENGINE",
                "deterministic_score": 85.0,
                "title": f"Resolve emission factor for {act_type.replace('_', ' ')}",
                "summary": f"Unresolved emission factor for {act_type} prevents carbon ledger posting and scenario quantification.",
                "why_it_matters": why_text,
                "recommended_action": next_text,
                "what": what_text,
                "why": why_text,
                "next_step": next_text,
                "evidence": evidence_text,
                "follow_up": follow_up_text,
                "limitation": limitation_text,
                "source_type": "EMISSION_FACTOR",
                "source_id": str(calc.id),
                "source_document_id": calc.document_id,
                "metric_value": float(calc.quantity) if calc.quantity else None,
                "metric_unit": calc.activity_unit,
                "evidence_reference": evidence_text,
                "dependency_status": "READY",  # Ready to be acted upon first (Patch 3)
                "due_context": "Immediate data quality blocker",
                "dedup_key": dedup_key,
            })

        return factor_actions_map

    def _gather_scenario_actions(
        self,
        db: Session,
        document_id: Optional[int],
        candidates: List[Dict[str, Any]],
        factor_actions_map: Dict[str, str]
    ):
        """
        Step 22C Scenarios — Quantified vs Unquantifiable Scenarios (Patch 3 & Patch 8).
        Labels explicitly: SCENARIO — NOT ACTUAL.
        Links unquantifiable scenarios as BLOCKED child of the corresponding factor blocker.
        """
        try:
            scenarios = emission_scenario_service.list_scenarios(db, document_id=document_id)
        except Exception as e:
            logger.warning(f"Error listing scenarios: {e}")
            return

        for sc in scenarios:
            if sc.status == "ARCHIVED":
                continue

            if sc.status == "NOT_QUANTIFIABLE":
                # Action: Recalculate Scenario (BLOCKED until factor resolved, Patch 3)
                cond_code = f"SCENARIO_NOT_QUANTIFIABLE_{sc.id}"
                dedup_key = self._build_dedup_key(
                    "RECALCULATE_SCENARIO", "SCENARIO", "SCENARIO",
                    str(sc.id), str(sc.document_id or ""), cond_code
                )

                what_text = f"Scenario '{sc.name}' is unquantifiable (SCENARIO — NOT ACTUAL)"
                why_text = f"Prerequisite factor or activity input is unresolved. {sc.factor_resolution_notes or ''}"
                next_text = "Resolve prerequisite emission factor, then recalculate scenario."
                evidence_text = f"EmissionScenario #{sc.id} ({sc.scenario_code}) - Status: NOT_QUANTIFIABLE"
                follow_up_text = "Evaluate scenario reduction delta against roadmap target once quantified."
                limitation_text = "Scenario results are strictly hypothetical simulations and do not represent actual historical reductions."

                # Check if factor action exists for dependency linking
                candidates.append({
                    "document_id": sc.document_id,
                    "action_type": "RECALCULATE_SCENARIO",
                    "category": "SCENARIO",
                    "queue_type": "REDUCTION",
                    "priority": "MEDIUM",
                    "priority_score": 55.0,
                    "priority_source": "SCENARIO",
                    "deterministic_score": 55.0,
                    "title": f"Recalculate scenario: {sc.name}",
                    "summary": f"Scenario '{sc.name}' is currently NOT_QUANTIFIABLE pending factor resolution.",
                    "why_it_matters": why_text,
                    "recommended_action": next_text,
                    "what": what_text,
                    "why": why_text,
                    "next_step": next_text,
                    "evidence": evidence_text,
                    "follow_up": follow_up_text,
                    "limitation": limitation_text,
                    "source_type": "SCENARIO",
                    "source_id": str(sc.id),
                    "source_document_id": sc.document_id,
                    "dependency_status": "BLOCKED",  # Blocked on factor resolution (Patch 3)
                    "due_context": "Post factor-resolution",
                    "dedup_key": dedup_key,
                })
            elif sc.status == "QUANTIFIED" or (sc.reduction_tco2e and float(sc.reduction_tco2e) > 0):
                delta_t = float(getattr(sc, "delta_co2e_tonnes", None) or getattr(sc, "reduction_tco2e", None) or 0.0)
                if delta_t != 0:
                    cond_code = f"SCENARIO_QUANTIFIED_{sc.id}"
                    dedup_key = self._build_dedup_key(
                        "EVALUATE_SCENARIO", "SCENARIO", "SCENARIO",
                        str(sc.id), str(sc.document_id or ""), cond_code
                    )
                    what_text = f"Evaluated Scenario: {sc.name} (SCENARIO — NOT ACTUAL)"
                    why_text = f"Modeled reduction of {abs(delta_t):.4f} tCO2e compared to baseline."
                    next_text = "Translate modeled scenario into operational reduction project and define M&V plan."
                    evidence_text = f"EmissionScenario #{sc.id} ({sc.scenario_code}) - Delta: {delta_t:.4f} tCO2e."
                    follow_up_text = "Establish pre-intervention baseline measurement period."
                    limitation_text = "SCENARIO — NOT ACTUAL: Modeled outcome depends on verified implementation fidelity."

                    candidates.append({
                        "document_id": sc.document_id,
                        "action_type": "EVALUATE_SCENARIO",
                        "category": "SCENARIO",
                        "queue_type": "REDUCTION",
                        "priority": "MEDIUM",
                        "priority_score": 60.0,
                        "priority_source": "SCENARIO",
                        "deterministic_score": 60.0,
                        "title": f"Review Scenario: {sc.name}",
                        "summary": why_text,
                        "why_it_matters": why_text,
                        "recommended_action": next_text,
                        "what": what_text,
                        "why": why_text,
                        "next_step": next_text,
                        "evidence": evidence_text,
                        "follow_up": follow_up_text,
                        "limitation": limitation_text,
                        "source_type": "SCENARIO",
                        "source_id": str(sc.id),
                        "source_document_id": sc.document_id,
                        "metric_value": abs(delta_t),
                        "metric_unit": "tCO2e (modeled)",
                        "dependency_status": "READY",
                        "due_context": "Planning",
                        "dedup_key": dedup_key,
                    })

    def _gather_project_mv_actions(
        self,
        db: Session,
        document_id: Optional[int],
        candidates: List[Dict[str, Any]]
    ):
        """
        Step 17 & 18 Reduction Projects and M&V Readiness (Queue A).
        """
        # Active projects needing measurement
        projects = db.query(ReductionProject).filter(
            ReductionProject.status.in_(["IN_PROGRESS", "COMPLETED"])
        ).all()

        for prj in projects:
            cond_code = f"PROJECT_MV_{prj.id}"
            dedup_key = self._build_dedup_key(
                "MEASURE_PROJECT", "REDUCTION", "REDUCTION_PROJECT",
                str(prj.id), str(document_id or ""), cond_code
            )
            what_text = f"M&V verification for Project: {prj.title}"
            why_text = f"Project '{prj.title}' ({prj.status}) requires post-intervention activity data collection."
            next_text = "Upload post-intervention billing period data to calculate verified reductions."
            evidence_text = f"ReductionProject #{prj.id} ({prj.project_code})"
            follow_up_text = "Generate third-party verification record after measurement calculation."
            limitation_text = "Reductions cannot be claimed without completed M&V verification."

            candidates.append({
                "document_id": document_id,
                "action_type": "MEASURE_PROJECT",
                "category": "VERIFICATION",
                "queue_type": "REDUCTION",
                "priority": "HIGH" if prj.status == "COMPLETED" else "MEDIUM",
                "priority_score": 70.0 if prj.status == "COMPLETED" else 50.0,
                "priority_source": "VERIFICATION",
                "deterministic_score": 70.0 if prj.status == "COMPLETED" else 50.0,
                "title": f"Conduct M&V: {prj.title}",
                "summary": why_text,
                "why_it_matters": why_text,
                "recommended_action": next_text,
                "what": what_text,
                "why": why_text,
                "next_step": next_text,
                "evidence": evidence_text,
                "follow_up": follow_up_text,
                "limitation": limitation_text,
                "source_type": "REDUCTION_PROJECT",
                "source_id": str(prj.id),
                "source_document_id": document_id,
                "dependency_status": "READY",
                "due_context": "Post-intervention cycle",
                "dedup_key": dedup_key,
            })

    def _gather_compliance_actions(
        self,
        db: Session,
        document_id: Optional[int],
        candidates: List[Dict[str, Any]]
    ):
        """
        Compliance Reports requiring review (Queue B, Patch 2).
        """
        query = db.query(ComplianceReport).filter(
            (ComplianceReport.status.in_(["NEEDS_REVIEW", "DRAFT"])) |
            (ComplianceReport.completeness_status.in_(["NEEDS_REVIEW", "INCOMPLETE"]))
        )

        reports = query.all()
        for rep in reports:
            cond_code = f"COMPLIANCE_REVIEW_{rep.id}"
            dedup_key = self._build_dedup_key(
                "COMPLIANCE_REVIEW_REQUIRED", "COMPLIANCE", "COMPLIANCE_REPORT",
                str(rep.id), str(document_id or ""), cond_code
            )
            what_text = f"Complete compliance review for {rep.framework}"
            why_text = f"Compliance report #{rep.id} has missing disclosures or pending verification items."
            next_text = "Review unverified disclosures in Compliance Reports section."
            evidence_text = f"ComplianceReport #{rep.id} ({rep.framework})"
            follow_up_text = "Re-evaluate compliance readiness score following review."
            limitation_text = "Compliance readiness reflects document completeness, not external legal assurance."

            candidates.append({
                "document_id": document_id,
                "action_type": "COMPLIANCE_REVIEW_REQUIRED",
                "category": "COMPLIANCE",
                "queue_type": "DATA_QUALITY",  # Queue B (Patch 2)
                "priority": "MEDIUM",
                "priority_score": 60.0,
                "priority_source": "COMPLIANCE",
                "deterministic_score": 60.0,
                "title": f"Review Compliance Disclosures: {rep.framework}",
                "summary": why_text,
                "why_it_matters": why_text,
                "recommended_action": next_text,
                "what": what_text,
                "why": why_text,
                "next_step": next_text,
                "evidence": evidence_text,
                "follow_up": follow_up_text,
                "limitation": limitation_text,
                "source_type": "COMPLIANCE_REPORT",
                "source_id": str(rep.id),
                "source_document_id": document_id,
                "dependency_status": "READY",
                "due_context": "Compliance cycle",
                "dedup_key": dedup_key,
            })

    def _gather_forecast_actions(
        self,
        db: Session,
        document_id: Optional[int],
        candidates: List[Dict[str, Any]]
    ):
        """
        Step 21 Forecast Signals — Labeled explicitly: FORECAST — NOT ACTUAL (Patch 8).
        """
        try:
            from backend.app.models.emission_forecast import EmissionForecast
            existing_fc = db.query(EmissionForecast).filter(EmissionForecast.forecast_status == "GENERATED").all()
            trend = "INCREASING" if existing_fc else "STABLE"
            if not existing_fc:
                forecast_data = emission_forecasting_service.generate_forecast(
                    db, ForecastRequest(periods_ahead=3, document_id=document_id)
                )
                trend = getattr(forecast_data, "trend_direction", "STABLE")
            if trend == "INCREASING":
                cond_code = "FORECAST_UPWARD_TREND"
                dedup_key = self._build_dedup_key(
                    "FORECAST_TREND", "FORECAST", "FORECAST",
                    "TREND", str(document_id or ""), cond_code
                )
                what_text = "Projected upward emission trend (FORECAST — NOT ACTUAL)"
                why_text = "Predictive emission analytics indicate increasing trend across consecutive periods."
                next_text = "Prioritize grid electricity and fuel optimization to prevent forecasted escalation."
                evidence_text = f"Step 21 projection: {existing_fc[0].forecast_code}" if existing_fc else "Step 21 linear regression across posted carbon ledger history."
                follow_up_text = "Evaluate next actual period against forecast trajectory."
                limitation_text = "FORECAST — NOT ACTUAL: Statistical projection based on historical trends; does not represent actual recorded emissions."

                candidates.append({
                    "document_id": document_id,
                    "action_type": "FORECAST_TREND",
                    "category": "FORECAST",
                    "queue_type": "REDUCTION",
                    "priority": "HIGH",
                    "priority_score": 65.0,
                    "priority_source": "FORECAST",
                    "deterministic_score": 65.0,
                    "title": "Address Projected Emissions Increase (FORECAST — NOT ACTUAL)",
                    "summary": why_text,
                    "why_it_matters": why_text,
                    "recommended_action": next_text,
                    "what": what_text,
                    "why": why_text,
                    "next_step": next_text,
                    "evidence": evidence_text,
                    "follow_up": follow_up_text,
                    "limitation": limitation_text,
                    "source_type": "FORECAST",
                    "source_id": "PREDICTIVE_FORECAST",
                    "source_document_id": document_id,
                    "dependency_status": "READY",
                    "due_context": "Forward planning",
                    "dedup_key": dedup_key,
                })
        except Exception as e:
            logger.info(f"Forecast evaluation skipped or unavailable: {e}")

    # -------------------------------------------------------------------------
    # 3. DEPENDENCY LINKING (Patch 3)
    # -------------------------------------------------------------------------

    def _link_dependencies(self, db: Session, actions: List[AgentAction]):
        """
        Deterministically connects parent and blocked actions.
        Example: RESOLVE_FACTOR (parent) -> RECALCULATE_SCENARIO (blocked child).
        """
        # Find factor resolution actions
        factor_actions = [a for a in actions if a.action_type == "RESOLVE_FACTOR" and a.status != "COMPLETED"]
        scenario_actions = [a for a in actions if a.action_type == "RECALCULATE_SCENARIO" and a.status != "COMPLETED"]

        if factor_actions and scenario_actions:
            parent = factor_actions[0]
            for child in scenario_actions:
                if child.parent_action_id != parent.id:
                    child.parent_action_id = parent.id
                    child.dependency_status = "BLOCKED"
                    if parent.blocks_action_id is None:
                        parent.blocks_action_id = child.id

    @staticmethod
    def _build_dedup_key(
        action_type: str,
        category: str,
        source_type: str,
        source_id: str,
        doc_id: str,
        condition_code: str
    ) -> str:
        """
        Deterministic deduplication key based on condition identity (Patch 7).
        """
        raw = f"{action_type}:{category}:{source_type}:{source_id}:{doc_id}:{condition_code}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

    _generate_dedup_key = _build_dedup_key

    # -------------------------------------------------------------------------
    # 4. ACTION LIFECYCLE MANAGEMENT (Audit Events)
    # -------------------------------------------------------------------------

    def start_action(self, *args, **kwargs) -> AgentAction:
        db, action_id = self._resolve_db_and_id(args, kwargs, "action_id")
        actor_type = kwargs.pop("actor", None) or kwargs.pop("actor_type", "USER")
        reason = kwargs.pop("reason", None) or kwargs.pop("note", None)

        action = db.query(AgentAction).filter(AgentAction.id == action_id).first()
        if not action:
            raise ValueError(f"AgentAction #{action_id} not found.")
        if action.status == "COMPLETED":
            raise ValueError(f"Cannot start completed action #{action_id}")

        old_status = action.status
        action.status = "IN_PROGRESS"
        action.updated_at = datetime.utcnow()

        event = AgentActionEvent(
            action_id=action.id,
            event_type="STARTED",
            previous_status=old_status,
            new_status="IN_PROGRESS",
            actor_type=actor_type,
            reason=reason or "Action marked in progress by user",
            created_at=datetime.utcnow(),
        )
        db.add(event)
        db.commit()
        db.refresh(action)
        return action

    def complete_action(self, *args, **kwargs) -> AgentAction:
        db, action_id = self._resolve_db_and_id(args, kwargs, "action_id")
        actor_type = kwargs.pop("actor", None) or kwargs.pop("actor_type", "USER")
        reason = kwargs.pop("reason", None) or kwargs.pop("note", None)

        action = db.query(AgentAction).filter(AgentAction.id == action_id).first()
        if not action:
            raise ValueError(f"AgentAction #{action_id} not found.")

        old_status = action.status
        action.status = "COMPLETED"
        action.completed_at = datetime.utcnow()
        action.updated_at = datetime.utcnow()

        event = AgentActionEvent(
            action_id=action.id,
            event_type="COMPLETED",
            previous_status=old_status,
            new_status="COMPLETED",
            actor_type=actor_type,
            reason=reason or "Action completed by user",
            created_at=datetime.utcnow(),
        )
        db.add(event)

        # Unblock dependent actions (Patch 3)
        blocked_children = db.query(AgentAction).filter(
            AgentAction.parent_action_id == action.id,
            AgentAction.status.in_(["OPEN", "IN_PROGRESS"])
        ).all()

        for child in blocked_children:
            child.dependency_status = "READY"
            child_event = AgentActionEvent(
                action_id=child.id,
                event_type="PRIORITIZED",
                previous_status=child.status,
                new_status=child.status,
                actor_type="SYSTEM",
                reason=f"Prerequisite parent action #{action.id} completed. Action is now READY.",
                created_at=datetime.utcnow(),
            )
            db.add(child_event)

        db.commit()
        db.refresh(action)
        return action

    def dismiss_action(self, *args, **kwargs) -> AgentAction:
        db, action_id = self._resolve_db_and_id(args, kwargs, "action_id")
        actor_type = kwargs.pop("actor", None) or kwargs.pop("actor_type", "USER")
        reason = kwargs.pop("reason", None) or kwargs.pop("note", None)

        action = db.query(AgentAction).filter(AgentAction.id == action_id).first()
        if not action:
            raise ValueError(f"AgentAction #{action_id} not found.")

        old_status = action.status
        action.status = "DISMISSED"
        action.dismissed_at = datetime.utcnow()
        action.updated_at = datetime.utcnow()

        event = AgentActionEvent(
            action_id=action.id,
            event_type="DISMISSED",
            previous_status=old_status,
            new_status="DISMISSED",
            actor_type=actor_type,
            reason=reason or "Action dismissed by user",
            created_at=datetime.utcnow(),
        )
        db.add(event)
        db.commit()
        db.refresh(action)
        return action

    # -------------------------------------------------------------------------
    # 5. AI SUSTAINABILITY BRIEF (Patch 4 & 8)
    # -------------------------------------------------------------------------

    def get_sustainability_brief(
        self,
        db: Optional[Session] = None,
        document_id: Optional[int] = None
    ) -> Any:
        """
        Generates the authoritative AI Sustainability Brief.
        Strictly separates Actuals, Forecasts (FORECAST — NOT ACTUAL), and Scenarios (SCENARIO — NOT ACTUAL).
        Never manufactures changes if no prior actual period exists.
        """
        db = db or self.db
        if not db:
            raise ValueError("Database session required")

        now = datetime.utcnow()

        # 1. Current posted footprint & period
        entries_query = db.query(CarbonLedgerEntry).filter(
            CarbonLedgerEntry.accounting_status == "POSTED"
        )
        if document_id:
            entries_query = entries_query.filter(CarbonLedgerEntry.document_id == document_id)

        all_entries = entries_query.all()

        current_period = None
        current_posted_footprint = 0.0

        if all_entries:
            # Group by reporting_period
            periods = sorted(list({e.reporting_period for e in all_entries if e.reporting_period}))
            if periods:
                current_period = periods[-1]
                period_entries = [e for e in all_entries if e.reporting_period == current_period]
                total_kg = sum(Decimal(str(e.calculated_co2e or 0)) for e in period_entries)
                current_posted_footprint = float(total_kg / Decimal("1000"))

        # 2. Recent Actual Changes (strictly between real periods, no manufactured delta)
        recent_changes: List[Dict[str, Any]] = []
        distinct_periods = sorted(list({e.reporting_period for e in all_entries if e.reporting_period}))
        if len(distinct_periods) >= 2:
            prev_period = distinct_periods[-2]
            curr_period = distinct_periods[-1]

            prev_kg = sum(Decimal(str(e.calculated_co2e or 0)) for e in all_entries if e.reporting_period == prev_period)
            curr_kg = sum(Decimal(str(e.calculated_co2e or 0)) for e in all_entries if e.reporting_period == curr_period)

            delta_tco2e = float((curr_kg - prev_kg) / Decimal("1000"))
            pct_change = float(((curr_kg - prev_kg) / prev_kg) * 100) if prev_kg > 0 else 0.0

            recent_changes.append({
                "metric_name": "Total Posted Footprint",
                "previous_period": prev_period,
                "current_period": curr_period,
                "previous_value_tco2e": float(prev_kg / Decimal("1000")),
                "current_value_tco2e": float(curr_kg / Decimal("1000")),
                "delta_tco2e": delta_tco2e,
                "change_percent": pct_change,
                "is_increase": delta_tco2e > 0,
            })

        # 3. Queue A: Top Reduction Actions
        actions_query = db.query(AgentAction).filter(
            AgentAction.status.in_(["OPEN", "IN_PROGRESS"])
        )
        if document_id:
            actions_query = actions_query.filter(AgentAction.document_id == document_id)

        all_open_actions = actions_query.all()
        if not all_open_actions:
            self.evaluate_actions(db=db, document_id=document_id)
            all_open_actions = actions_query.all()

        reduction_actions = [
            a for a in all_open_actions if a.queue_type == "REDUCTION"
        ]
        reduction_actions.sort(key=lambda x: float(x.priority_score or 0.0), reverse=True)

        data_quality_blockers = [
            a for a in all_open_actions if a.queue_type == "DATA_QUALITY"
        ]
        data_quality_blockers.sort(key=lambda x: float(x.priority_score or 0.0), reverse=True)

        ready_actions = [
            a for a in all_open_actions if a.dependency_status == "READY"
        ]

        critical_count = sum(1 for a in all_open_actions if a.priority == "CRITICAL")
        high_count = sum(1 for a in all_open_actions if a.priority == "HIGH")

        # 4. Forecast Signal (Labeled: FORECAST — NOT ACTUAL, Patch 8)
        forecast_signal = {
            "status": "UNAVAILABLE",
            "label": "FORECAST — NOT ACTUAL",
            "trend": "STABLE",
            "explanation": "Insufficient historical periods to generate forecast."
        }
        try:
            fc = emission_forecasting_service.generate_forecast(
                db, ForecastRequest(periods_ahead=3, document_id=document_id)
            )
            if fc and fc.predictions:
                forecast_signal = {
                    "status": "AVAILABLE",
                    "label": "FORECAST — NOT ACTUAL",
                    "trend": getattr(fc, "trend_direction", "STABLE"),
                    "confidence_score": float(getattr(fc, "confidence_score", 0.0) or 0.0),
                    "projected_tco2e": float(fc.predictions[0].predicted_emissions_tco2e or 0.0),
                    "explanation": f"Statistical regression projects {getattr(fc, 'trend_direction', 'stable')} trend for upcoming periods."
                }
        except Exception:
            pass

        # 5. Roadmap Status
        roadmap_status = {
            "has_roadmap": False,
            "phase": "NONE",
            "completed_items": 0,
            "total_items": 0,
            "progress_percent": 0.0
        }
        try:
            rm_list = reduction_roadmap_service.list_roadmaps(db, document_id=document_id)
            if rm_list:
                active_rm = rm_list[0]
                tot = len(active_rm.items) if active_rm.items else 0
                done = sum(1 for i in active_rm.items if i.status == "COMPLETED") if active_rm.items else 0
                pct = (done / tot * 100.0) if tot > 0 else 0.0
                roadmap_status = {
                    "has_roadmap": True,
                    "roadmap_id": active_rm.id,
                    "phase": active_rm.items[0].phase if active_rm.items else "PHASE_1_FOUNDATION",
                    "completed_items": done,
                    "total_items": tot,
                    "progress_percent": round(pct, 1)
                }
        except Exception:
            pass

        # 6. Scenario Status (Labeled: SCENARIO — NOT ACTUAL, Patch 8)
        scenario_status = {
            "total_scenarios": 0,
            "quantified_count": 0,
            "unquantifiable_count": 0,
            "label": "SCENARIO — NOT ACTUAL",
            "notes": "No active what-if scenarios modeled."
        }
        try:
            sc_list = emission_scenario_service.list_scenarios(db, document_id=document_id)
            if sc_list:
                active_sc = [s for s in sc_list if s.status != "ARCHIVED"]
                q_cnt = sum(1 for s in active_sc if s.status == "QUANTIFIED")
                uq_cnt = sum(1 for s in active_sc if s.status == "NOT_QUANTIFIABLE")
                scenario_status = {
                    "total_scenarios": len(active_sc),
                    "quantified_count": q_cnt,
                    "unquantifiable_count": uq_cnt,
                    "label": "SCENARIO — NOT ACTUAL",
                    "notes": f"{q_cnt} quantified scenario(s), {uq_cnt} unquantifiable scenario(s) pending factor resolution."
                }
        except Exception:
            pass

        delta_val = recent_changes[0]["delta_tco2e"] if recent_changes else None
        q_a_cnt = len(reduction_actions)
        q_b_cnt = len(data_quality_blockers)
        attn_cnt = len(all_open_actions)
        ready_cnt = len(ready_actions)

        summary_text = (
            f"Based on posted accounting records through {current_period or 'latest upload'}, "
            f"total footprint stands at {current_posted_footprint:.4f} tCO2e. "
            f"There are {attn_cnt} items requiring attention ({q_a_cnt} reduction opportunities, "
            f"{q_b_cnt} data quality blockers). {ready_cnt} actions are ready for execution."
        )

        return BriefResult({
            "title": "AI Sustainability Brief",
            "executive_summary": summary_text,
            "generated_at": now,
            "agent_version": self.agent_version,
            "current_period": current_period,
            "latest_actual_reporting_period": current_period,
            "current_posted_footprint": current_posted_footprint,
            "actual_footprint_tco2e": current_posted_footprint,
            "period_to_period_delta_tco2e": delta_val,
            "last_evaluated": self._last_evaluated or now,
            "last_evaluated_at": self._last_evaluated or now,
            "open_action_count": attn_cnt,
            "attention_count": attn_cnt,
            "queue_a_count": q_a_cnt,
            "queue_b_count": q_b_cnt,
            "ready_actions_count": ready_cnt,
            "critical_count": critical_count,
            "high_count": high_count,
            "top_actions": [a.to_dict() for a in reduction_actions[:5]],
            "data_quality_blockers": [a.to_dict() for a in data_quality_blockers[:5]],
            "ready_actions": [a.to_dict() for a in ready_actions[:5]],
            "recent_changes": recent_changes,
            "forecast_signal": forecast_signal,
            "roadmap_status": roadmap_status,
            "scenario_status": scenario_status,
        })

    # -------------------------------------------------------------------------
    # 6. STRUCTURED EXPLANATION CONTRACT (Patch 5)
    # -------------------------------------------------------------------------

    def explain_action(self, *args, **kwargs) -> Any:
        """
        Returns structured WHAT, WHY, NEXT, EVIDENCE, FOLLOW_UP, LIMITATION.
        Identical contract across API, UI, and Copilot.
        """
        db, action_id = self._resolve_db_and_id(args, kwargs, "action_id")
        action = db.query(AgentAction).filter(AgentAction.id == action_id).first()
        if not action:
            raise ValueError(f"AgentAction #{action_id} not found.")

        return ExplanationResult({
            "action_id": action.id,
            "title": action.title,
            "what": action.what or action.title,
            "why": action.why or action.why_it_matters,
            "next": action.next_step or action.recommended_action,
            "evidence": action.evidence or action.evidence_reference or "Document lineage records",
            "follow_up": action.follow_up or "Monitor subsequent reporting periods for verification.",
            "limitation": action.limitation or "This recommendation does not guarantee future emissions reduction.",
        })

    def get_actions(self, *args, **kwargs) -> List[AgentAction]:
        db = kwargs.pop("db", None) or (args[0] if args and not isinstance(args[0], int) else self.db)
        if not db:
            raise ValueError("Database session required")
        document_id = kwargs.pop("document_id", None)
        queue = kwargs.pop("queue", None) or kwargs.pop("action_queue", None)
        status = kwargs.pop("status", None)
        priority = kwargs.pop("priority", None) or kwargs.pop("priority_level", None)
        limit = kwargs.pop("limit", 100)
        offset = kwargs.pop("offset", 0)

        query = db.query(AgentAction)
        if document_id is not None:
            query = query.filter(AgentAction.document_id == document_id)
        if status is not None:
            query = query.filter(AgentAction.status == status)
        if priority is not None:
            query = query.filter(AgentAction.priority == priority)
        if queue is not None:
            query = query.filter(AgentAction.queue_type == queue)
        return query.order_by(desc(AgentAction.priority_score)).offset(offset).limit(limit).all()

    def get_action(self, *args, **kwargs) -> Optional[AgentAction]:
        db, action_id = self._resolve_db_and_id(args, kwargs, "action_id")
        return db.query(AgentAction).filter(AgentAction.id == action_id).first()

    def get_next_ready_action(self, *args, **kwargs) -> Optional[AgentAction]:
        db = kwargs.pop("db", None) or (args[0] if args and not isinstance(args[0], int) else self.db)
        if not db:
            raise ValueError("Database session required")
        document_id = kwargs.pop("document_id", None)
        queue = kwargs.pop("queue", None) or kwargs.pop("action_queue", None)

        query = db.query(AgentAction).filter(
            AgentAction.status == "OPEN",
            AgentAction.dependency_status == "READY"
        )
        if document_id is not None:
            query = query.filter(AgentAction.document_id == document_id)
        if queue is not None:
            query = query.filter(AgentAction.queue_type == queue)
        return query.order_by(desc(AgentAction.priority_score)).first()

    def get_agent_status(self, *args, **kwargs) -> Dict[str, Any]:
        db = kwargs.pop("db", None) or (args[0] if args and not isinstance(args[0], int) else self.db)
        active_count = db.query(AgentAction).filter(AgentAction.status.in_(["OPEN", "IN_PROGRESS"])).count() if db else 0
        return {
            "engine_version": self.agent_version,
            "agent_version": self.agent_version,
            "status": "OPERATIONAL",
            "last_evaluated": self._last_evaluated,
            "active_actions_count": active_count,
        }

    def get_action_events(self, *args, **kwargs) -> List[AgentActionEvent]:
        db, action_id = self._resolve_db_and_id(args, kwargs, "action_id")
        return db.query(AgentActionEvent).filter(AgentActionEvent.action_id == action_id).order_by(AgentActionEvent.created_at.asc()).all()


proactive_agent_service = ProactiveAgentService()
