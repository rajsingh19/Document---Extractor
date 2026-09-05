"""
services/reduction_intelligence.py — Deterministic Reduction Opportunity Intelligence Engine (Step 22A).

Evaluates POSTED CarbonLedgerEntry history, historical trends, Step 21 predictive emissions analytics,
ReductionOpportunities, and ReductionProjects to deterministically rank reduction focus areas.

CRITICAL PRODUCT BOUNDARIES:
- Strictly deterministic decision support layer.
- Never mutates CarbonLedgerEntry, CarbonCalculation, SustainabilityMetric, ActivityData, or ReductionOpportunity.
- Never fabricates emission savings, reduction percentages, ROI, payback periods, or operational causality.
- Does NOT treat missing historical periods as zero.
- Uses exact Decimal arithmetic for all calculations.
"""
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from backend.app.models.carbon_ledger import CarbonLedgerEntry
from backend.app.models.reduction_opportunity import ReductionOpportunity
from backend.app.models.reduction_project import ReductionProject
from backend.app.models.sustainability_metric import SustainabilityMetric
from backend.app.models.document import Document
from backend.app.models.reduction_intelligence import ReductionPriority
from backend.app.schemas.emission_forecast import ForecastRequest
from backend.app.services.emission_forecasting import emission_forecasting_service
from backend.app.config.reduction_intelligence import (
    REDUCTION_INTELLIGENCE_VERSION,
    IMPACT_WEIGHT,
    TREND_WEIGHT,
    FORECAST_WEIGHT,
    PERSISTENCE_WEIGHT,
    ACTIONABILITY_WEIGHT,
    DATA_QUALITY_WEIGHT,
    BLOCKER_WEIGHT,
    IMPACT_TIER_VERY_HIGH_PCT,
    IMPACT_TIER_HIGH_PCT,
    IMPACT_TIER_MEDIUM_PCT,
    IMPACT_SCORE_VERY_HIGH,
    IMPACT_SCORE_HIGH,
    IMPACT_SCORE_MEDIUM,
    IMPACT_SCORE_LOW,
    IMPACT_SCORE_ZERO,
    TREND_TIER_STRONG_INCREASE_PCT,
    TREND_TIER_MODERATE_INCREASE_PCT,
    TREND_TIER_WEAK_INCREASE_PCT,
    TREND_SCORE_STRONG,
    TREND_SCORE_MODERATE,
    TREND_SCORE_WEAK,
    TREND_SCORE_STABLE_OR_DECREASING,
    TREND_REPEATED_INCREASE_BONUS,
    FORECAST_SCORE_INCREASE,
    FORECAST_SCORE_UNCERTAIN,
    FORECAST_SCORE_DECREASE,
    FORECAST_SCORE_UNAVAILABLE,
    PERSISTENCE_PERIODS_STRONG,
    PERSISTENCE_PERIODS_MODERATE,
    PERSISTENCE_PERIODS_LOW,
    PERSISTENCE_SCORE_STRONG,
    PERSISTENCE_SCORE_MODERATE,
    PERSISTENCE_SCORE_LOW,
    PERSISTENCE_SCORE_ZERO,
    ACTIONABILITY_SCORE_CONCRETE,
    ACTIONABILITY_SCORE_ANALYSIS,
    ACTIONABILITY_SCORE_DATA_GAP,
    ACTIONABILITY_SCORE_NONE,
    DATA_QUALITY_SCORE_UNRESOLVED_FACTOR,
    DATA_QUALITY_SCORE_REVIEW_REQUIRED,
    DATA_QUALITY_SCORE_MISSING_DATA,
    DATA_QUALITY_SCORE_CLEAN,
    BLOCKER_SCORE_CRITICAL,
    BLOCKER_SCORE_MODERATE,
    BLOCKER_SCORE_NONE,
    PRIORITY_THRESHOLD_CRITICAL,
    PRIORITY_THRESHOLD_HIGH,
    PRIORITY_THRESHOLD_MEDIUM,
    PRIORITY_THRESHOLD_LOW,
    PRIORITY_LEVEL_CRITICAL,
    PRIORITY_LEVEL_HIGH,
    PRIORITY_LEVEL_MEDIUM,
    PRIORITY_LEVEL_LOW,
    PRIORITY_LEVEL_INFORMATIONAL,
    PROJECT_STATUS_IN_PROGRESS_ADJUSTMENT,
    PROJECT_STATUS_COMPLETED_ADJUSTMENT,
)
from backend.app.schemas.reduction_intelligence import (
    ReductionPriorityResponse,
    ReductionPriorityDetail,
    ReductionPriorityList,
    ReductionIntelligenceSummary,
    RecalculateResponse,
)

logger = logging.getLogger("senseible-reduction-intelligence")


class ReductionIntelligenceService:
    """
    Deterministic Intelligence Service for Carbon Reduction Priorities (Step 22A).
    """

    def __init__(self):
        self.version = REDUCTION_INTELLIGENCE_VERSION

    # --------------------------------------------------------------------------
    # 1. CORE EVALUATION ENGINE
    # --------------------------------------------------------------------------
    def evaluate_priorities(
        self,
        db: Session,
        document_id: Optional[int] = None,
        save_to_db: bool = True,
    ) -> List[ReductionPriority]:
        """
        Deterministically evaluates posted accounting entries, opportunities, trends,
        forecasts, and data-quality indicators to generate ranked reduction priorities.
        """
        # 1. Fetch strictly POSTED CarbonLedgerEntry records
        ledger_query = db.query(CarbonLedgerEntry).filter(
            CarbonLedgerEntry.accounting_status == "POSTED"
        )
        if document_id is not None:
            ledger_query = ledger_query.filter(CarbonLedgerEntry.document_id == document_id)
        
        posted_entries = ledger_query.all()

        # Calculate total posted emissions (kgCO2e and tCO2e)
        total_posted_kg = Decimal("0.0")
        for e in posted_entries:
            co2e_kg = Decimal(str(e.calculated_co2e or 0))
            total_posted_kg += co2e_kg

        total_posted_t = total_posted_kg / Decimal("1000.0") if total_posted_kg > 0 else Decimal("0.0")

        # 2. Group posted entries by activity / emission source
        # Key: (scope, category, activity_type)
        grouped_entries: Dict[Tuple[str, str, str], List[CarbonLedgerEntry]] = {}
        for e in posted_entries:
            key = (e.scope or "UNKNOWN", e.category or "OTHER", e.activity_type or "UNKNOWN")
            if key not in grouped_entries:
                grouped_entries[key] = []
            grouped_entries[key].append(e)

        # 3. Fetch existing ReductionOpportunity records
        opp_query = db.query(ReductionOpportunity)
        if document_id is not None:
            opp_query = opp_query.filter(ReductionOpportunity.evidence_document_id == document_id)
        all_opportunities = opp_query.all()

        # Index opportunities by key and by opportunity_code
        opp_by_key: Dict[Tuple[str, str, str], List[ReductionOpportunity]] = {}
        opp_by_scope_act: Dict[Tuple[str, str], List[ReductionOpportunity]] = {}
        opp_by_ledger_id: Dict[int, ReductionOpportunity] = {}
        opp_by_id: Dict[int, ReductionOpportunity] = {}
        for opp in all_opportunities:
            opp_by_id[opp.id] = opp
            k = (opp.scope or "UNKNOWN", opp.category or "OTHER", opp.activity_type or "UNKNOWN")
            if k not in opp_by_key:
                opp_by_key[k] = []
            opp_by_key[k].append(opp)

            sk = (opp.scope or "UNKNOWN", opp.activity_type or "UNKNOWN")
            if sk not in opp_by_scope_act:
                opp_by_scope_act[sk] = []
            opp_by_scope_act[sk].append(opp)

            if opp.evidence_ledger_entry_id:
                opp_by_ledger_id[opp.evidence_ledger_entry_id] = opp

        # 4. Fetch existing ReductionProject records
        all_projects = db.query(ReductionProject).all()
        proj_by_opp_id: Dict[int, List[ReductionProject]] = {}
        proj_by_key: Dict[Tuple[str, str, str], List[ReductionProject]] = {}
        for proj in all_projects:
            if proj.opportunity_id:
                if proj.opportunity_id not in proj_by_opp_id:
                    proj_by_opp_id[proj.opportunity_id] = []
                proj_by_opp_id[proj.opportunity_id].append(proj)
            pk = (proj.scope or "UNKNOWN", proj.category or "OTHER", proj.activity_type or "UNKNOWN")
            if pk not in proj_by_key:
                proj_by_key[pk] = []
            proj_by_key[pk].append(proj)

        # 5. Build candidate priorities from posted sources and standalone opportunities
        candidate_items: List[Dict[str, Any]] = []
        processed_activity_types = set()

        # A. Process POSTED ledger groups
        processed_opp_ids = set()
        for (scope, category, activity_type), entries in grouped_entries.items():
            processed_activity_types.add(activity_type)
            # Calculate source emissions
            source_kg = sum(Decimal(str(e.calculated_co2e or 0)) for e in entries)
            source_t = source_kg / Decimal("1000.0")

            # Match matching reduction opportunity if any (actionable opportunities preferred)
            all_matched_opps = list(opp_by_key.get((scope, category, activity_type), []))
            # Also check scope + activity_type
            for o in opp_by_scope_act.get((scope, activity_type), []):
                if o not in all_matched_opps:
                    all_matched_opps.append(o)
            # Also check ledger entry ID match
            for e in entries:
                if e.id in opp_by_ledger_id:
                    o = opp_by_ledger_id[e.id]
                    if o not in all_matched_opps:
                        all_matched_opps.append(o)

            # Filter for actionable reduction opportunities (exclude pure data quality / factor gaps from consuming this group)
            actionable_opps = [o for o in all_matched_opps if o.category != "DATA_QUALITY" and o.trigger_type not in ("DATA_QUALITY", "UNRESOLVED_FACTOR")]
            primary_opp = actionable_opps[0] if actionable_opps else (all_matched_opps[0] if all_matched_opps else None)
            
            for o in actionable_opps:
                processed_opp_ids.add(o.id)

            # Match project if any
            matched_projects = []
            if primary_opp and primary_opp.id in proj_by_opp_id:
                matched_projects.extend(proj_by_opp_id[primary_opp.id])
            if (scope, category, activity_type) in proj_by_key:
                matched_projects.extend(proj_by_key[(scope, category, activity_type)])

            primary_proj = matched_projects[0] if matched_projects else None

            # Historical periods & trends for this source
            period_data = self._aggregate_period_series(entries)
            persistence_periods = len(period_data)

            # Trend calculation
            trend_pct, is_repeated_increase = self._calculate_trend_metrics(period_data)
            prev_kg = period_data[-2][1] if len(period_data) >= 2 else None

            # Forecast signal
            forecast_dto, forecast_score, forecast_kg = self._evaluate_forecast_signal(
                db=db,
                scope=scope,
                category=category,
                activity_type=activity_type,
                last_actual_kg=period_data[-1][1] if period_data else source_kg
            )

            # Signals
            impact_score = self._calculate_impact_score(source_kg, total_posted_kg)
            trend_score = self._calculate_trend_score(trend_pct, is_repeated_increase)
            persistence_score = self._calculate_persistence_score(persistence_periods)
            actionability_score, action_type = self._calculate_actionability_score(primary_opp)
            dq_score, blocker_score, is_dq_issue = self._calculate_data_quality_score(
                entries=entries,
                opportunity=primary_opp
            )

            # Project status modifier
            project_modifier = self._calculate_project_status_modifier(primary_proj)

            # Total score
            raw_score = (
                impact_score
                + trend_score
                + forecast_score
                + persistence_score
                + actionability_score
                + dq_score
                + blocker_score
                + project_modifier
            )
            final_score = min(Decimal("100.0"), max(Decimal("0.0"), raw_score)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            priority_level = self._map_priority_level(final_score, is_dq_issue)

            # Title & Reason
            title = self._generate_title(activity_type, category, scope, primary_opp, is_dq_issue)
            reason = self._generate_reason(
                title=title,
                source_kg=source_kg,
                total_kg=total_posted_kg,
                trend_pct=trend_pct,
                forecast_dto=forecast_dto,
                persistence_periods=persistence_periods,
                opportunity=primary_opp,
                project=primary_proj,
                is_dq_issue=is_dq_issue
            )

            # Evidence & provenance
            doc_id = document_id or (entries[0].document_id if entries else None)
            led_ids = [str(e.id) for e in entries[:5]]
            source_ref = f"Ledger entries [{', '.join(led_ids)}]" + (f", Document #{doc_id}" if doc_id else "")
            evidence_ref = entries[0].source_text if (entries and entries[0].source_text) else (primary_opp.rationale if primary_opp else None)

            # Deterministic code
            doc_suffix = f"DOC_{doc_id}" if doc_id else "GLOBAL"
            norm_act = (activity_type or "SRC").upper().replace(" ", "_").replace("-", "_")
            norm_cat = (category or "CAT").upper().replace(" ", "_").replace("-", "_")
            priority_code = f"PRIORITY_{scope}_{norm_cat}_{norm_act}_{doc_suffix}"

            candidate_items.append({
                "priority_code": priority_code,
                "document_id": doc_id,
                "opportunity_id": primary_opp.id if primary_opp else None,
                "project_id": primary_proj.id if primary_proj else None,
                "scope": scope,
                "category": category,
                "activity_type": activity_type,
                "priority_score": final_score,
                "priority_level": priority_level,
                "impact_score": impact_score.quantize(Decimal("0.01")),
                "trend_score": trend_score.quantize(Decimal("0.01")),
                "forecast_score": forecast_score.quantize(Decimal("0.01")),
                "persistence_score": persistence_score.quantize(Decimal("0.01")),
                "actionability_score": actionability_score.quantize(Decimal("0.01")),
                "data_quality_score": dq_score.quantize(Decimal("0.01")),
                "blocker_score": blocker_score.quantize(Decimal("0.01")),
                "title": title,
                "reason": reason,
                "current_emissions_kgco2e": source_kg.quantize(Decimal("0.000001")),
                "current_emissions_tco2e": source_t.quantize(Decimal("0.000001")),
                "previous_emissions_kgco2e": prev_kg.quantize(Decimal("0.000001")) if prev_kg is not None else None,
                "change_percent": trend_pct.quantize(Decimal("0.01")) if trend_pct is not None else None,
                "forecast_emissions_kgco2e": forecast_kg.quantize(Decimal("0.000001")) if forecast_kg is not None else None,
                "source_reference": source_ref,
                "evidence_reference": evidence_ref,
                "calculation_version": self.version,
                "is_data_quality_issue": is_dq_issue,
            })

        # B. Process standalone opportunities (e.g. DATA_QUALITY / UNRESOLVED_FACTOR with no posted ledger entries)
        seen_standalone_signatures = set()
        for opp in all_opportunities:
            if opp.id in processed_opp_ids:
                continue
            if opp.activity_type in processed_activity_types and not (opp.category == "DATA_QUALITY" or opp.trigger_type in ("DATA_QUALITY", "UNRESOLVED_FACTOR")):
                continue

            # Deduplicate multiple standalone entries representing the same gap
            sig = (opp.evidence_document_id or document_id, opp.scope, opp.activity_type, opp.trigger_type)
            if sig in seen_standalone_signatures:
                continue
            seen_standalone_signatures.add(sig)

            # This is a standalone opportunity (e.g., solar factor data gap or uncalculated metric)
            is_dq_issue = (opp.category == "DATA_QUALITY" or opp.trigger_type in ("DATA_QUALITY", "UNRESOLVED_FACTOR"))
            doc_id = document_id or opp.evidence_document_id

            impact_score = IMPACT_SCORE_ZERO
            trend_score = TREND_SCORE_STABLE_OR_DECREASING
            forecast_score = FORECAST_SCORE_UNAVAILABLE
            persistence_score = PERSISTENCE_SCORE_LOW if is_dq_issue else PERSISTENCE_SCORE_ZERO
            actionability_score = ACTIONABILITY_SCORE_DATA_GAP if is_dq_issue else ACTIONABILITY_SCORE_ANALYSIS
            dq_score = DATA_QUALITY_SCORE_UNRESOLVED_FACTOR if is_dq_issue else DATA_QUALITY_SCORE_REVIEW_REQUIRED
            blocker_score = BLOCKER_SCORE_CRITICAL if is_dq_issue else BLOCKER_SCORE_MODERATE

            raw_score = (
                impact_score
                + trend_score
                + forecast_score
                + persistence_score
                + actionability_score
                + dq_score
                + blocker_score
            )
            # Standalone data-quality items get high visibility
            if is_dq_issue:
                final_score = Decimal("65.0")  # Marked as HIGH data quality priority
            else:
                final_score = min(Decimal("100.0"), max(Decimal("0.0"), raw_score)).quantize(Decimal("0.01"))

            priority_level = PRIORITY_LEVEL_HIGH if is_dq_issue else self._map_priority_level(final_score, is_dq_issue)
            title = f"Data Gap: {opp.title}" if (is_dq_issue and not opp.title.startswith("Data Gap")) else opp.title
            
            reason = (
                f"{opp.description} "
                f"This data-quality blocker prevents verified emissions calculation until resolved. "
                f"Identified from document #{doc_id} with limitation: {opp.limitations or 'Verified emission factor required'}."
            )

            doc_suffix = f"DOC_{doc_id}" if doc_id else "GLOBAL"
            priority_code = f"PRIORITY_OPP_{opp.id}_{doc_suffix}"

            candidate_items.append({
                "priority_code": priority_code,
                "document_id": doc_id,
                "opportunity_id": opp.id,
                "project_id": None,
                "scope": opp.scope,
                "category": opp.category,
                "activity_type": opp.activity_type,
                "priority_score": final_score,
                "priority_level": priority_level,
                "impact_score": impact_score.quantize(Decimal("0.01")),
                "trend_score": trend_score.quantize(Decimal("0.01")),
                "forecast_score": forecast_score.quantize(Decimal("0.01")),
                "persistence_score": persistence_score.quantize(Decimal("0.01")),
                "actionability_score": actionability_score.quantize(Decimal("0.01")),
                "data_quality_score": dq_score.quantize(Decimal("0.01")),
                "blocker_score": blocker_score.quantize(Decimal("0.01")),
                "title": title,
                "reason": reason,
                "current_emissions_kgco2e": Decimal("0.0"),
                "current_emissions_tco2e": Decimal("0.0"),
                "previous_emissions_kgco2e": None,
                "change_percent": None,
                "forecast_emissions_kgco2e": None,
                "source_reference": f"ReductionOpportunity #{opp.id}, Document #{doc_id}",
                "evidence_reference": opp.rationale or opp.description,
                "calculation_version": self.version,
                "is_data_quality_issue": is_dq_issue,
            })

        # 6. Deterministic Sorting & Ranking
        # Sort key: priority_score DESC, current_emissions_kgco2e DESC, priority_code ASC
        candidate_items.sort(
            key=lambda x: (
                -x["priority_score"],
                -x["current_emissions_kgco2e"],
                x["priority_code"]
            )
        )

        for rank_idx, item in enumerate(candidate_items, start=1):
            item["priority_rank"] = rank_idx

        # 7. Persist to Database if requested (Idempotent update/upsert)
        persisted_entities: List[ReductionPriority] = []
        if save_to_db:
            # Delete existing priorities for the specific scope (or all if document_id is None)
            existing_query = db.query(ReductionPriority)
            if document_id is not None:
                existing_query = existing_query.filter(ReductionPriority.document_id == document_id)
            existing_query.delete(synchronize_session=False)
            db.flush()

            for item in candidate_items:
                entity = ReductionPriority(
                    priority_code=item["priority_code"],
                    document_id=item["document_id"],
                    opportunity_id=item["opportunity_id"],
                    project_id=item["project_id"],
                    scope=item["scope"],
                    category=item["category"],
                    activity_type=item["activity_type"],
                    priority_rank=item["priority_rank"],
                    priority_score=item["priority_score"],
                    priority_level=item["priority_level"],
                    impact_score=item["impact_score"],
                    trend_score=item["trend_score"],
                    forecast_score=item["forecast_score"],
                    persistence_score=item["persistence_score"],
                    actionability_score=item["actionability_score"],
                    data_quality_score=item["data_quality_score"],
                    blocker_score=item["blocker_score"],
                    title=item["title"],
                    reason=item["reason"],
                    current_emissions_kgco2e=item["current_emissions_kgco2e"],
                    current_emissions_tco2e=item["current_emissions_tco2e"],
                    previous_emissions_kgco2e=item["previous_emissions_kgco2e"],
                    change_percent=item["change_percent"],
                    forecast_emissions_kgco2e=item["forecast_emissions_kgco2e"],
                    source_reference=item["source_reference"],
                    evidence_reference=item["evidence_reference"],
                    calculation_version=item["calculation_version"],
                )
                db.add(entity)
                persisted_entities.append(entity)

            db.commit()
            for entity in persisted_entities:
                db.refresh(entity)
            return persisted_entities

        else:
            # Create transient model instances without saving
            for item in candidate_items:
                entity = ReductionPriority(
                    priority_code=item["priority_code"],
                    document_id=item["document_id"],
                    opportunity_id=item["opportunity_id"],
                    project_id=item["project_id"],
                    scope=item["scope"],
                    category=item["category"],
                    activity_type=item["activity_type"],
                    priority_rank=item["priority_rank"],
                    priority_score=item["priority_score"],
                    priority_level=item["priority_level"],
                    impact_score=item["impact_score"],
                    trend_score=item["trend_score"],
                    forecast_score=item["forecast_score"],
                    persistence_score=item["persistence_score"],
                    actionability_score=item["actionability_score"],
                    data_quality_score=item["data_quality_score"],
                    blocker_score=item["blocker_score"],
                    title=item["title"],
                    reason=item["reason"],
                    current_emissions_kgco2e=item["current_emissions_kgco2e"],
                    current_emissions_tco2e=item["current_emissions_tco2e"],
                    previous_emissions_kgco2e=item["previous_emissions_kgco2e"],
                    change_percent=item["change_percent"],
                    forecast_emissions_kgco2e=item["forecast_emissions_kgco2e"],
                    source_reference=item["source_reference"],
                    evidence_reference=item["evidence_reference"],
                    calculation_version=item["calculation_version"],
                )
                persisted_entities.append(entity)
            return persisted_entities

    # --------------------------------------------------------------------------
    # 2. DETERMINISTIC SIGNAL CALCULATIONS
    # --------------------------------------------------------------------------
    def _calculate_impact_score(self, source_kg: Decimal, total_kg: Decimal) -> Decimal:
        """Calculate materiality score relative to total posted emissions."""
        if total_kg <= Decimal("0.0") or source_kg <= Decimal("0.0"):
            return IMPACT_SCORE_ZERO

        ratio_pct = (source_kg / total_kg) * Decimal("100.0")

        if ratio_pct >= IMPACT_TIER_VERY_HIGH_PCT:
            return IMPACT_SCORE_VERY_HIGH
        elif ratio_pct >= IMPACT_TIER_HIGH_PCT:
            return IMPACT_SCORE_HIGH
        elif ratio_pct >= IMPACT_TIER_MEDIUM_PCT:
            return IMPACT_SCORE_MEDIUM
        else:
            return IMPACT_SCORE_LOW

    def _aggregate_period_series(self, entries: List[CarbonLedgerEntry]) -> List[Tuple[str, Decimal]]:
        """Aggregate ledger entries by reporting period chronologically."""
        period_map: Dict[str, Decimal] = {}
        for e in entries:
            p = str(e.reporting_period or "UNKNOWN")
            val = Decimal(str(e.calculated_co2e or 0))
            period_map[p] = period_map.get(p, Decimal("0.0")) + val

        # Chronological sort of reporting period strings
        sorted_periods = sorted(period_map.keys())
        return [(p, period_map[p]) for p in sorted_periods]

    def _calculate_trend_metrics(
        self,
        period_data: List[Tuple[str, Decimal]]
    ) -> Tuple[Optional[Decimal], bool]:
        """Calculate percentage change between latest 2 actual periods and multi-period escalation."""
        if len(period_data) < 2:
            return None, False

        prev_val = period_data[-2][1]
        curr_val = period_data[-1][1]

        if prev_val <= Decimal("0.0"):
            return None, False

        change_pct = ((curr_val - prev_val) / prev_val) * Decimal("100.0")

        # Check repeated increases across 3+ actual periods
        is_repeated = False
        if len(period_data) >= 3:
            is_repeated = True
            for i in range(len(period_data) - 1):
                if period_data[i + 1][1] <= period_data[i][1]:
                    is_repeated = False
                    break

        return change_pct, is_repeated

    def _calculate_trend_score(
        self,
        change_pct: Optional[Decimal],
        is_repeated_increase: bool
    ) -> Decimal:
        """Calculate trend score based on actual period-over-period change."""
        if change_pct is None:
            return TREND_SCORE_STABLE_OR_DECREASING

        if change_pct >= TREND_TIER_STRONG_INCREASE_PCT:
            score = TREND_SCORE_STRONG
        elif change_pct >= TREND_TIER_MODERATE_INCREASE_PCT:
            score = TREND_SCORE_MODERATE
        elif change_pct > TREND_TIER_WEAK_INCREASE_PCT:
            score = TREND_SCORE_WEAK
        else:
            score = TREND_SCORE_STABLE_OR_DECREASING

        if is_repeated_increase:
            score = min(TREND_WEIGHT, score + TREND_REPEATED_INCREASE_BONUS)

        return score

    def _evaluate_forecast_signal(
        self,
        db: Session,
        scope: Optional[str],
        category: Optional[str],
        activity_type: Optional[str],
        last_actual_kg: Decimal,
    ) -> Tuple[Optional[Any], Decimal, Optional[Decimal]]:
        """Evaluate Step 21 predictive emission trajectory without re-implementing."""
        try:
            req = ForecastRequest(
                scope=scope,
                category=category,
                activity_type=activity_type,
                horizon=1,
            )
            fcst_resp = emission_forecasting_service.generate_forecast(db=db, req=req, save_to_db=False)
            
            if not fcst_resp or fcst_resp.forecast_status == "INSUFFICIENT_DATA" or fcst_resp.historical_period_count < 3:
                return None, FORECAST_SCORE_UNAVAILABLE, None

            fcst_val_t = Decimal(str(fcst_resp.predicted_value))
            fcst_val_kg = fcst_val_t * Decimal("1000.0")

            if fcst_resp.proactive_signal == "FORECAST_INCREASE" or (last_actual_kg > 0 and fcst_val_kg > last_actual_kg * Decimal("1.02")):
                return fcst_resp, FORECAST_SCORE_INCREASE, fcst_val_kg
            elif fcst_resp.proactive_signal == "FORECAST_DECREASE" or (last_actual_kg > 0 and fcst_val_kg < last_actual_kg * Decimal("0.98")):
                return fcst_resp, FORECAST_SCORE_DECREASE, fcst_val_kg
            else:
                return fcst_resp, FORECAST_SCORE_UNCERTAIN, fcst_val_kg
        except Exception as err:
            logger.debug(f"Forecast evaluation skipped for {activity_type}: {err}")
            return None, FORECAST_SCORE_UNAVAILABLE, None

    def _calculate_persistence_score(self, period_count: int) -> Decimal:
        """Score persistence based on actual periods with posted data."""
        if period_count >= PERSISTENCE_PERIODS_STRONG:
            return PERSISTENCE_SCORE_STRONG
        elif period_count == PERSISTENCE_PERIODS_MODERATE:
            return PERSISTENCE_SCORE_MODERATE
        elif period_count == PERSISTENCE_PERIODS_LOW:
            return PERSISTENCE_SCORE_LOW
        else:
            return PERSISTENCE_SCORE_ZERO

    def _calculate_actionability_score(
        self,
        opportunity: Optional[ReductionOpportunity]
    ) -> Tuple[Decimal, str]:
        """Evaluate presence of concrete operational action."""
        if opportunity:
            if opportunity.category == "DATA_QUALITY" or opportunity.trigger_type in ("DATA_QUALITY", "UNRESOLVED_FACTOR"):
                return ACTIONABILITY_SCORE_DATA_GAP, "DATA_GAP"
            elif opportunity.recommended_action and len(opportunity.recommended_action) > 10:
                return ACTIONABILITY_SCORE_CONCRETE, "CONCRETE"
            else:
                return ACTIONABILITY_SCORE_ANALYSIS, "ANALYSIS_REQUIRED"
        return ACTIONABILITY_SCORE_ANALYSIS, "ANALYSIS_REQUIRED"

    def _calculate_data_quality_score(
        self,
        entries: List[CarbonLedgerEntry],
        opportunity: Optional[ReductionOpportunity]
    ) -> Tuple[Decimal, Decimal, bool]:
        """Detect unresolved emission factors, unverified metrics, or data gaps."""
        dq_score = DATA_QUALITY_SCORE_CLEAN
        blocker_score = BLOCKER_SCORE_NONE
        is_dq_issue = False

        # Check if opportunity is flagged as DATA_QUALITY
        if opportunity and (opportunity.category == "DATA_QUALITY" or opportunity.trigger_type in ("DATA_QUALITY", "UNRESOLVED_FACTOR")):
            dq_score = DATA_QUALITY_SCORE_UNRESOLVED_FACTOR
            blocker_score = BLOCKER_SCORE_CRITICAL
            is_dq_issue = True

        # Check if any ledger entry had missing factor or provisional factor
        for e in entries:
            if not e.emission_factor_id or not e.factor_value:
                dq_score = max(dq_score, DATA_QUALITY_SCORE_UNRESOLVED_FACTOR)
                blocker_score = max(blocker_score, BLOCKER_SCORE_CRITICAL)
                is_dq_issue = True

        return dq_score, blocker_score, is_dq_issue

    def _calculate_project_status_modifier(
        self,
        project: Optional[ReductionProject]
    ) -> Decimal:
        """Adjust score if an active project is already addressing this priority."""
        if not project:
            return Decimal("0.0")

        status_norm = (project.status or "").upper()
        if status_norm == "IN_PROGRESS":
            return PROJECT_STATUS_IN_PROGRESS_ADJUSTMENT
        elif status_norm == "COMPLETED":
            return PROJECT_STATUS_COMPLETED_ADJUSTMENT
        return Decimal("0.0")

    def _map_priority_level(self, score: Decimal, is_dq_issue: bool = False) -> str:
        """Map normalized priority score (0-100) to standard priority level."""
        if score >= PRIORITY_THRESHOLD_CRITICAL:
            return PRIORITY_LEVEL_CRITICAL
        elif score >= PRIORITY_THRESHOLD_HIGH:
            return PRIORITY_LEVEL_HIGH
        elif score >= PRIORITY_THRESHOLD_MEDIUM:
            return PRIORITY_LEVEL_MEDIUM
        elif score >= PRIORITY_THRESHOLD_LOW:
            return PRIORITY_LEVEL_LOW
        else:
            return PRIORITY_LEVEL_INFORMATIONAL

    # --------------------------------------------------------------------------
    # 3. EXPLANATION GENERATOR
    # --------------------------------------------------------------------------
    def _generate_title(
        self,
        activity_type: Optional[str],
        category: Optional[str],
        scope: Optional[str],
        opportunity: Optional[ReductionOpportunity],
        is_dq_issue: bool
    ) -> str:
        """Generate concise, factual title."""
        if opportunity and opportunity.title:
            return opportunity.title

        act_clean = (activity_type or "Emission Source").replace("_", " ").title()
        scope_clean = (scope or "").replace("_", " ").title()

        if is_dq_issue:
            return f"Data Gap: {act_clean} Factor Resolution"
        elif "Electricity" in act_clean:
            return f"Investigate {act_clean} Demand & Renewable Procurement"
        elif "Diesel" in act_clean:
            return f"Investigate {act_clean} Fuel Consumption & Generator Efficiency"
        else:
            return f"Investigate {act_clean} Reduction ({scope_clean})"

    def _generate_reason(
        self,
        title: str,
        source_kg: Decimal,
        total_kg: Decimal,
        trend_pct: Optional[Decimal],
        forecast_dto: Optional[Any],
        persistence_periods: int,
        opportunity: Optional[ReductionOpportunity],
        project: Optional[ReductionProject],
        is_dq_issue: bool
    ) -> str:
        """Build grounded, factual narrative explanation with source references."""
        source_t = source_kg / Decimal("1000.0")
        total_t = total_kg / Decimal("1000.0") if total_kg > 0 else Decimal("0.0")
        share_pct = (source_kg / total_kg * Decimal("100.0")) if total_kg > 0 else Decimal("0.0")

        lines = []

        if is_dq_issue:
            lines.append(
                f"Data quality gap: This area requires verified emission factor resolution or complete activity data. "
                f"Until resolved, emissions cannot be reliably verified."
            )
        elif total_t > 0:
            lines.append(
                f"{title} is a key reduction focus because it accounts for {source_t:.4f} tCO2e "
                f"({share_pct:.1f}% of total calculated posted footprint of {total_t:.4f} tCO2e)."
            )
        else:
            lines.append(f"{title} has recorded posted activity in the carbon ledger.")

        # Trend explanation
        if trend_pct is not None:
            if trend_pct > Decimal("0.0"):
                lines.append(f"Emissions increased by {trend_pct:.1f}% across recent actual reporting periods.")
            elif trend_pct < Decimal("0.0"):
                lines.append(f"Emissions decreased by {abs(trend_pct):.1f}% in the latest reported period.")
            else:
                lines.append("Emissions have remained stable across reported periods.")

        # Persistence explanation
        if persistence_periods >= 3:
            lines.append(f"This source shows sustained presence across {persistence_periods} consecutive reporting periods.")
        elif persistence_periods == 2:
            lines.append(f"Observed across {persistence_periods} reporting periods.")

        # Forecast explanation
        if forecast_dto:
            fcst_val = float(forecast_dto.predicted_value)
            if forecast_dto.proactive_signal == "FORECAST_INCREASE":
                lines.append(f"Step 21 predictive analytics indicates continuing upward trajectory (projected {fcst_val:.4f} tCO2e).")
            elif forecast_dto.proactive_signal == "FORECAST_DECREASE":
                lines.append(f"Step 21 predictive analytics projects downward trend to {fcst_val:.4f} tCO2e.")
            else:
                lines.append(f"Step 21 forecast projects steady emissions around {fcst_val:.4f} tCO2e.")
        else:
            lines.append("Forecast contribution is unavailable because sufficient historical periods (minimum 3) are not yet available.")

        # Project explanation
        if project:
            lines.append(f"Existing reduction project '{project.title}' is currently {project.status}.")

        return " ".join(lines)

    # --------------------------------------------------------------------------
    # 4. QUERY & SUMMARY HELPERS
    # --------------------------------------------------------------------------
    def get_priorities(
        self,
        db: Session,
        document_id: Optional[int] = None,
        scope: Optional[str] = None,
        priority_level: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[ReductionPriority]:
        """Fetch ranked reduction priorities with optional filters."""
        # Check if priorities exist in database, if not run evaluation
        query = db.query(ReductionPriority)
        if document_id is not None:
            query = query.filter(ReductionPriority.document_id == document_id)

        count = query.count()
        if count == 0:
            self.evaluate_priorities(db=db, document_id=document_id, save_to_db=True)
            query = db.query(ReductionPriority)
            if document_id is not None:
                query = query.filter(ReductionPriority.document_id == document_id)

        if scope and scope.upper() != "ALL":
            query = query.filter(ReductionPriority.scope == scope.upper().replace(" ", "_"))

        if priority_level:
            query = query.filter(ReductionPriority.priority_level == priority_level.upper())

        if category:
            query = query.filter(ReductionPriority.category == category.upper())

        return query.order_by(ReductionPriority.priority_rank.asc()).all()

    def get_priority_by_id(self, db: Session, priority_id: int) -> Optional[ReductionPriority]:
        """Get single reduction priority by ID."""
        return db.query(ReductionPriority).filter(ReductionPriority.id == priority_id).first()

    def get_summary(
        self,
        db: Session,
        document_id: Optional[int] = None,
    ) -> ReductionIntelligenceSummary:
        """Calculate executive summary KPI counters."""
        priorities = self.get_priorities(db=db, document_id=document_id)

        if not priorities:
            return ReductionIntelligenceSummary(
                total_priorities=0,
                critical=0,
                high=0,
                medium=0,
                low=0,
                informational=0,
                top_priority=None,
                top_priority_score=None,
                top_emitting_source=None,
                largest_increasing_source=None,
                forecast_available=False,
                forecast_concern=None,
                data_quality_blockers=None,
                existing_project_coverage=None,
            )

        critical_count = sum(1 for p in priorities if p.priority_level == PRIORITY_LEVEL_CRITICAL)
        high_count = sum(1 for p in priorities if p.priority_level == PRIORITY_LEVEL_HIGH)
        medium_count = sum(1 for p in priorities if p.priority_level == PRIORITY_LEVEL_MEDIUM)
        low_count = sum(1 for p in priorities if p.priority_level == PRIORITY_LEVEL_LOW)
        info_count = sum(1 for p in priorities if p.priority_level == PRIORITY_LEVEL_INFORMATIONAL)

        top_p = priorities[0] if priorities else None

        # Find top emitting source
        top_emitting = max(priorities, key=lambda p: p.current_emissions_kgco2e or Decimal("0.0"), default=None)
        top_emitting_name = top_emitting.title if (top_emitting and top_emitting.current_emissions_kgco2e > 0) else None

        # Find largest increasing source
        increasing = [p for p in priorities if p.change_percent is not None and p.change_percent > 0]
        largest_inc = max(increasing, key=lambda p: p.change_percent, default=None)
        largest_inc_name = largest_inc.title if largest_inc else None

        # Check forecast availability
        has_forecast = any(p.forecast_emissions_kgco2e is not None for p in priorities)
        forecast_concern = None
        if has_forecast:
            growing_fcst = [p for p in priorities if p.forecast_score >= FORECAST_SCORE_INCREASE]
            if growing_fcst:
                forecast_concern = f"{growing_fcst[0].title} projected to increase"

        # Check data quality blockers
        dq_items = [p for p in priorities if p.data_quality_score > Decimal("0.0") or p.blocker_score > Decimal("0.0")]
        dq_blocker_desc = f"{len(dq_items)} data quality area(s) require factor or evidence resolution" if dq_items else "No critical data quality blockers"

        # Check project coverage
        with_projects = sum(1 for p in priorities if p.project_id is not None)
        proj_coverage = f"{with_projects} of {len(priorities)} priorities linked to active reduction projects"

        return ReductionIntelligenceSummary(
            total_priorities=len(priorities),
            critical=critical_count,
            high=high_count,
            medium=medium_count,
            low=low_count,
            informational=info_count,
            top_priority=top_p.title if top_p else None,
            top_priority_score=float(top_p.priority_score) if (top_p and top_p.priority_score is not None) else None,
            top_emitting_source=top_emitting_name,
            largest_increasing_source=largest_inc_name,
            forecast_available=has_forecast,
            forecast_concern=forecast_concern,
            data_quality_blockers=dq_blocker_desc,
            existing_project_coverage=proj_coverage,
        )


reduction_intelligence_service = ReductionIntelligenceService()
