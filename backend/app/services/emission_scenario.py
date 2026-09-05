"""
services/emission_scenario.py — Deterministic Service for Emissions Scenario Engine (Step 22C).

Calculates hypothetical decarbonization what-if scenarios using:
- Verified POSTED CarbonLedgerEntry actuals for baseline
- Existing ActivityData and activity metadata
- Deterministic EmissionFactorResolver for baseline and replacement factors
- Pure Python Decimal arithmetic (no floating point precision loss)
- Strict missing-factor protection (no zero substitution, emits SCENARIO_NOT_QUANTIFIABLE)
- Target gap evaluation against active ReductionRoadmaps
- Audit preservation via ARCHIVED status
"""
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.models.carbon_ledger import CarbonLedgerEntry
from backend.app.models.activity_data import ActivityData
from backend.app.models.reduction_roadmap import ReductionRoadmap
from backend.app.models.emission_scenario import (
    EmissionScenario,
    ScenarioInput,
    ScenarioResult,
)
from backend.app.schemas.emission_scenario import (
    ScenarioCreateRequest,
    ScenarioInputCreate,
    ScenarioUpdateRequest,
)
from backend.app.schemas.emission_factor import FactorResolutionRequest
from backend.app.services.emission_factor_resolver import EmissionFactorResolver
from backend.app.config.emission_scenario import (
    SCENARIO_CALCULATION_VERSION,
    SCENARIO_STATUS_DRAFT,
    SCENARIO_STATUS_CALCULATED,
    SCENARIO_STATUS_ARCHIVED,
    SCENARIO_TYPE_REDUCE_ACTIVITY,
    SCENARIO_TYPE_INCREASE_ACTIVITY,
    SCENARIO_TYPE_REPLACE_SOURCE,
    SCENARIO_TYPE_SHIFT_SOURCE,
    SCENARIO_TYPE_ADD_SOURCE,
    SCENARIO_TYPE_REMOVE_SOURCE,
    QUANTIFICATION_STATUS_QUANTIFIED,
    QUANTIFICATION_STATUS_PARTIALLY_QUANTIFIED,
    QUANTIFICATION_STATUS_NOT_QUANTIFIABLE,
    TARGET_STATUS_MET,
    TARGET_STATUS_NOT_MET,
    TARGET_STATUS_NOT_DEFINED,
    TARGET_STATUS_SCENARIO_NOT_QUANTIFIABLE,
    RESULT_STATUS_QUANTIFIED,
    RESULT_STATUS_UNRESOLVED_FACTOR,
    RESULT_STATUS_MISSING_ACTIVITY,
    DEFAULT_UNRESOLVED_FACTOR_NOTE,
    DEFAULT_SCENARIO_CAUTION,
)


def _d(val: Any) -> Decimal:
    if val is None:
        return Decimal("0.0")
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


class EmissionScenarioService:
    """
    Deterministic scenario calculation engine.
    """

    def __init__(self):
        self.version = SCENARIO_CALCULATION_VERSION
        self.factor_resolver = EmissionFactorResolver()

    # ==========================================================================
    # 1. BASELINE EXTRACTION
    # ==========================================================================

    def get_baseline_entries(
        self,
        db: Session,
        document_id: Optional[int] = None,
        baseline_period: Optional[str] = None
    ) -> List[CarbonLedgerEntry]:
        """
        Retrieves baseline ledger entries strictly from POSTED CarbonLedgerEntry records.
        """
        query = db.query(CarbonLedgerEntry).filter(
            CarbonLedgerEntry.accounting_status == "POSTED"
        )
        if document_id is not None:
            query = query.filter(CarbonLedgerEntry.document_id == document_id)
        if baseline_period:
            query = query.filter(CarbonLedgerEntry.reporting_period == baseline_period)

        return query.order_by(CarbonLedgerEntry.id.asc()).all()

    # ==========================================================================
    # 2. SCENARIO CREATION & CALCULATION
    # ==========================================================================

    def create_and_calculate_scenario(
        self,
        db: Session,
        payload: ScenarioCreateRequest
    ) -> EmissionScenario:
        """
        Initializes, saves inputs, and deterministically calculates an EmissionScenario.
        """
        # 1. Load baseline ledger records
        baseline_entries = self.get_baseline_entries(
            db=db,
            document_id=payload.document_id,
            baseline_period=payload.baseline_period
        )

        total_baseline_kg = sum((_d(e.calculated_co2e) for e in baseline_entries), Decimal("0.0"))
        total_baseline_t = (total_baseline_kg / Decimal("1000.0")).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

        # Baseline period identification
        period_str = payload.baseline_period
        if not period_str and baseline_entries:
            period_str = baseline_entries[0].reporting_period or f"FY{baseline_entries[0].reporting_year or 'ACTUAL'}"
        if not period_str:
            period_str = "ACTUAL"

        # Unique code generation
        import uuid
        doc_suffix = f"DOC_{payload.document_id}" if payload.document_id else "PORTFOLIO"
        timestamp_str = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        rand_suffix = uuid.uuid4().hex[:6].upper()
        scenario_code = f"SCEN-{doc_suffix}-{payload.scenario_type[:6]}-{timestamp_str}-{rand_suffix}"

        # 2. Create scenario root entity
        scenario = EmissionScenario(
            scenario_code=scenario_code,
            document_id=payload.document_id,
            roadmap_id=payload.roadmap_id,
            name=payload.name,
            description=payload.description,
            scenario_type=payload.scenario_type,
            status=SCENARIO_STATUS_DRAFT,
            baseline_period=period_str,
            baseline_emissions_kgco2e=total_baseline_kg,
            baseline_emissions_tco2e=total_baseline_t,
            calculation_version=self.version,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(scenario)
        db.flush()

        # 3. Normalize structured inputs
        normalized_inputs = self._normalize_inputs(db, payload, baseline_entries)

        # 4. Save inputs and calculate source-level results
        self._execute_scenario_calculation(db, scenario, baseline_entries, normalized_inputs)

        db.commit()
        db.refresh(scenario)
        return scenario

    def recalculate_scenario(self, db: Session, scenario_id: int) -> EmissionScenario:
        """
        Recalculates an existing scenario deterministically against current baseline ledger actuals.
        """
        scenario = db.query(EmissionScenario).filter(EmissionScenario.id == scenario_id).first()
        if not scenario:
            raise ValueError(f"EmissionScenario with id {scenario_id} not found")

        # Clear existing results
        db.query(ScenarioResult).filter(ScenarioResult.scenario_id == scenario.id).delete()

        baseline_entries = self.get_baseline_entries(
            db=db,
            document_id=scenario.document_id,
            baseline_period=scenario.baseline_period
        )

        total_baseline_kg = sum((_d(e.calculated_co2e) for e in baseline_entries), Decimal("0.0"))
        total_baseline_t = (total_baseline_kg / Decimal("1000.0")).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        scenario.baseline_emissions_kgco2e = total_baseline_kg
        scenario.baseline_emissions_tco2e = total_baseline_t

        # Re-execute calculation with existing inputs
        self._execute_scenario_calculation(db, scenario, baseline_entries, scenario.inputs)

        scenario.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(scenario)
        return scenario

    # ==========================================================================
    # 3. INTERNAL CALCULATION ENGINE
    # ==========================================================================

    def _normalize_inputs(
        self,
        db: Session,
        payload: ScenarioCreateRequest,
        baseline_entries: List[CarbonLedgerEntry]
    ) -> List[ScenarioInputCreate]:
        """
        Converts shortcut fields or raw inputs into a unified list of ScenarioInputCreate.
        """
        if payload.inputs and len(payload.inputs) > 0:
            return payload.inputs

        # Process shortcut single-action scenario
        inputs_list: List[ScenarioInputCreate] = []

        if payload.scenario_type in (SCENARIO_TYPE_REDUCE_ACTIVITY, SCENARIO_TYPE_INCREASE_ACTIVITY, SCENARIO_TYPE_REMOVE_SOURCE):
            target_act_id = payload.target_activity_data_id or payload.source_activity_data_id
            target_pct = payload.change_percent or (Decimal("100.0") if payload.scenario_type == SCENARIO_TYPE_REMOVE_SOURCE else Decimal("0.0"))

            # Find matching baseline ledger entry or ActivityData
            matched_entry = None
            if target_act_id:
                matched_entry = next((e for e in baseline_entries if e.activity_data_id == target_act_id), None)
            elif baseline_entries:
                matched_entry = baseline_entries[0]

            act_type = matched_entry.activity_type if matched_entry else "activity"
            inputs_list.append(
                ScenarioInputCreate(
                    activity_data_id=matched_entry.activity_data_id if matched_entry else target_act_id,
                    source_ledger_entry_id=matched_entry.id if matched_entry else None,
                    activity_type=act_type,
                    change_type=payload.scenario_type,
                    change_percent=target_pct,
                    assumption=payload.description or f"{payload.scenario_type} by {target_pct}%",
                )
            )

        elif payload.scenario_type in (SCENARIO_TYPE_REPLACE_SOURCE, SCENARIO_TYPE_SHIFT_SOURCE):
            source_act_id = payload.source_activity_data_id or payload.target_activity_data_id
            rep_pct = payload.replacement_percent or payload.change_percent or Decimal("0.0")
            rep_source = payload.replacement_activity_type or "solar_electricity"

            matched_entry = None
            if source_act_id:
                matched_entry = next((e for e in baseline_entries if e.activity_data_id == source_act_id), None)
            elif baseline_entries:
                matched_entry = baseline_entries[0]

            act_type = matched_entry.activity_type if matched_entry else "purchased_electricity"
            inputs_list.append(
                ScenarioInputCreate(
                    activity_data_id=matched_entry.activity_data_id if matched_entry else source_act_id,
                    source_ledger_entry_id=matched_entry.id if matched_entry else None,
                    activity_type=act_type,
                    change_type=payload.scenario_type,
                    change_percent=rep_pct,
                    replacement_source=rep_source,
                    assumption=payload.description or f"Replace {rep_pct}% of {act_type} with {rep_source}",
                )
            )

        return inputs_list

    def _execute_scenario_calculation(
        self,
        db: Session,
        scenario: EmissionScenario,
        baseline_entries: List[CarbonLedgerEntry],
        inputs: List[Any]
    ):
        """
        Evaluates assumptions line-by-line, performs factor resolution, and computes modeled results.
        """
        assumptions_list = []
        limitations_list = []
        has_unresolved_factor = False

        # Map baseline entries by activity_data_id and entry.id
        entry_map: Dict[int, CarbonLedgerEntry] = {e.id: e for e in baseline_entries}
        act_id_map: Dict[int, CarbonLedgerEntry] = {e.activity_data_id: e for e in baseline_entries if e.activity_data_id}

        # Track which baseline entries have been altered by scenario inputs
        modified_entry_ids = set()

        # Iterate over each input assumption
        for inp in inputs:
            # Match baseline entry
            matched_entry: Optional[CarbonLedgerEntry] = None
            if getattr(inp, "source_ledger_entry_id", None) and inp.source_ledger_entry_id in entry_map:
                matched_entry = entry_map[inp.source_ledger_entry_id]
            elif getattr(inp, "activity_data_id", None) and inp.activity_data_id in act_id_map:
                matched_entry = act_id_map[inp.activity_data_id]
            elif baseline_entries:
                # Fallback to match by activity_type if possible
                matched_entry = next((e for e in baseline_entries if e.activity_type == getattr(inp, "activity_type", None)), None)

            base_qty = _d(matched_entry.quantity) if matched_entry else Decimal("0.0")
            base_unit = matched_entry.activity_unit if matched_entry else "unit"
            base_factor = _d(matched_entry.factor_value) if (matched_entry and matched_entry.factor_value is not None) else None
            base_scope = matched_entry.scope if matched_entry else "Scope 1"
            base_cat = matched_entry.category if matched_entry else "OTHER"
            base_act_type = matched_entry.activity_type if matched_entry else (getattr(inp, "activity_type", "activity") or "activity")
            base_co2e_kg = _d(matched_entry.calculated_co2e) if matched_entry else Decimal("0.0")

            change_pct = _d(getattr(inp, "change_percent", None))
            chg_type = getattr(inp, "change_type", SCENARIO_TYPE_REDUCE_ACTIVITY)

            # Persist ScenarioInput if not already persisted
            scenario_input = inp
            if not isinstance(inp, ScenarioInput):
                scenario_input = ScenarioInput(
                    scenario_id=scenario.id,
                    activity_data_id=matched_entry.activity_data_id if matched_entry else getattr(inp, "activity_data_id", None),
                    source_ledger_entry_id=matched_entry.id if matched_entry else None,
                    activity_type=base_act_type,
                    category=base_cat,
                    scope=base_scope,
                    baseline_quantity=base_qty,
                    baseline_unit=base_unit,
                    scenario_quantity=base_qty,  # updated below
                    scenario_unit=base_unit,
                    change_type=chg_type,
                    change_percent=change_pct,
                    replacement_source=getattr(inp, "replacement_source", None),
                    replacement_activity_data_id=getattr(inp, "replacement_activity_data_id", None),
                    assumption=getattr(inp, "assumption", None),
                    evidence_reference=getattr(inp, "evidence_reference", None),
                    created_at=datetime.utcnow(),
                )
                db.add(scenario_input)

            if matched_entry:
                modified_entry_ids.add(matched_entry.id)

            # ── CALCULATE ACCORDING TO CHANGE TYPE ─────────────────────────────
            if chg_type in (SCENARIO_TYPE_REDUCE_ACTIVITY, SCENARIO_TYPE_REMOVE_SOURCE):
                reduction_ratio = change_pct / Decimal("100.0")
                if chg_type == SCENARIO_TYPE_REMOVE_SOURCE:
                    reduction_ratio = Decimal("1.0")

                scenario_qty = (base_qty * (Decimal("1.0") - reduction_ratio)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
                scenario_input.scenario_quantity = scenario_qty

                scenario_emissions_kg = None
                reduction_kg = None
                result_status = RESULT_STATUS_QUANTIFIED

                if base_factor is not None:
                    scenario_emissions_kg = (scenario_qty * base_factor).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
                    reduction_kg = (base_co2e_kg - scenario_emissions_kg).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
                else:
                    has_unresolved_factor = True
                    result_status = RESULT_STATUS_UNRESOLVED_FACTOR
                    limitations_list.append(f"Baseline emission factor for {base_act_type} is not resolved.")

                formula_text = f"{scenario_qty} {base_unit} × {base_factor} = {scenario_emissions_kg} kgCO2e" if base_factor is not None else "Factor unresolved"
                result = ScenarioResult(
                    scenario_id=scenario.id,
                    source_name=matched_entry.factor_name or base_act_type if matched_entry else base_act_type,
                    scope=base_scope,
                    category=base_cat,
                    activity_type=base_act_type,
                    baseline_quantity=base_qty,
                    scenario_quantity=scenario_qty,
                    unit=base_unit,
                    baseline_emissions_kgco2e=base_co2e_kg,
                    scenario_emissions_kgco2e=scenario_emissions_kg,
                    reduction_kgco2e=reduction_kg,
                    baseline_factor=base_factor,
                    scenario_factor=base_factor,
                    factor_unit=matched_entry.factor_unit if matched_entry else None,
                    factor_source=matched_entry.factor_source if matched_entry else None,
                    factor_version=matched_entry.factor_version if matched_entry else None,
                    factor_code=matched_entry.factor_code if matched_entry else None,
                    calculation_formula=formula_text,
                    status=result_status,
                    notes=f"Reduced {base_act_type} activity by {change_pct}%.",
                    created_at=datetime.utcnow(),
                )
                db.add(result)
                assumptions_list.append(f"Reduced {base_act_type} from {base_qty} {base_unit} to {scenario_qty} {base_unit} (-{change_pct}%).")

            elif chg_type == SCENARIO_TYPE_INCREASE_ACTIVITY:
                increase_ratio = change_pct / Decimal("100.0")
                scenario_qty = (base_qty * (Decimal("1.0") + increase_ratio)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
                scenario_input.scenario_quantity = scenario_qty

                scenario_emissions_kg = None
                reduction_kg = None
                result_status = RESULT_STATUS_QUANTIFIED

                if base_factor is not None:
                    scenario_emissions_kg = (scenario_qty * base_factor).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
                    reduction_kg = (base_co2e_kg - scenario_emissions_kg).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
                else:
                    has_unresolved_factor = True
                    result_status = RESULT_STATUS_UNRESOLVED_FACTOR
                    limitations_list.append(f"Baseline emission factor for {base_act_type} is not resolved.")

                formula_text = f"{scenario_qty} {base_unit} × {base_factor} = {scenario_emissions_kg} kgCO2e" if base_factor is not None else "Factor unresolved"
                result = ScenarioResult(
                    scenario_id=scenario.id,
                    source_name=matched_entry.factor_name or base_act_type if matched_entry else base_act_type,
                    scope=base_scope,
                    category=base_cat,
                    activity_type=base_act_type,
                    baseline_quantity=base_qty,
                    scenario_quantity=scenario_qty,
                    unit=base_unit,
                    baseline_emissions_kgco2e=base_co2e_kg,
                    scenario_emissions_kgco2e=scenario_emissions_kg,
                    reduction_kgco2e=reduction_kg,
                    baseline_factor=base_factor,
                    scenario_factor=base_factor,
                    factor_unit=matched_entry.factor_unit if matched_entry else None,
                    factor_source=matched_entry.factor_source if matched_entry else None,
                    factor_version=matched_entry.factor_version if matched_entry else None,
                    factor_code=matched_entry.factor_code if matched_entry else None,
                    calculation_formula=formula_text,
                    status=result_status,
                    notes=f"Increased {base_act_type} activity by {change_pct}%.",
                    created_at=datetime.utcnow(),
                )
                db.add(result)
                assumptions_list.append(f"Increased {base_act_type} from {base_qty} {base_unit} to {scenario_qty} {base_unit} (+{change_pct}%).")

            elif chg_type in (SCENARIO_TYPE_REPLACE_SOURCE, SCENARIO_TYPE_SHIFT_SOURCE):
                replace_ratio = change_pct / Decimal("100.0")
                replaced_qty = (base_qty * replace_ratio).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
                remaining_qty = (base_qty - replaced_qty).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

                scenario_input.scenario_quantity = remaining_qty
                rep_source_name = getattr(inp, "replacement_source", "solar_electricity") or "solar_electricity"

                # 1. Remaining original source line item
                rem_emissions_kg = None
                if base_factor is not None:
                    rem_emissions_kg = (remaining_qty * base_factor).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

                rem_result = ScenarioResult(
                    scenario_id=scenario.id,
                    source_name=f"Remaining {matched_entry.factor_name or base_act_type if matched_entry else base_act_type}",
                    scope=base_scope,
                    category=base_cat,
                    activity_type=base_act_type,
                    baseline_quantity=base_qty,
                    scenario_quantity=remaining_qty,
                    unit=base_unit,
                    baseline_emissions_kgco2e=base_co2e_kg,
                    scenario_emissions_kgco2e=rem_emissions_kg,
                    reduction_kgco2e=(base_co2e_kg - rem_emissions_kg).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP) if rem_emissions_kg is not None else None,
                    baseline_factor=base_factor,
                    scenario_factor=base_factor,
                    factor_unit=matched_entry.factor_unit if matched_entry else None,
                    factor_source=matched_entry.factor_source if matched_entry else None,
                    factor_version=matched_entry.factor_version if matched_entry else None,
                    factor_code=matched_entry.factor_code if matched_entry else None,
                    calculation_formula=f"{remaining_qty} {base_unit} × {base_factor} = {rem_emissions_kg} kgCO2e" if base_factor is not None else "Factor unresolved",
                    status=RESULT_STATUS_QUANTIFIED if base_factor is not None else RESULT_STATUS_UNRESOLVED_FACTOR,
                    notes=f"Remaining {100 - change_pct}% of original {base_act_type}.",
                    created_at=datetime.utcnow(),
                )
                db.add(rem_result)

                # 2. Replacement source factor resolution
                rep_factor_res = self.factor_resolver.resolve(
                    db=db,
                    request=FactorResolutionRequest(
                        activity_type=rep_source_name,
                        activity_unit=base_unit,
                        scope="SCOPE_2" if "electric" in rep_source_name.lower() or "solar" in rep_source_name.lower() else "SCOPE_1",
                        geography=matched_entry.geography if matched_entry else None,
                        year=matched_entry.reporting_year if matched_entry else None,
                    )
                )

                rep_factor = None
                rep_factor_unit = None
                rep_factor_source = None
                rep_factor_version = None
                rep_factor_code = None
                rep_status = RESULT_STATUS_QUANTIFIED
                rep_emissions_kg = None

                if rep_factor_res and rep_factor_res.status == "MATCHED" and rep_factor_res.selected_factor:
                    sel = rep_factor_res.selected_factor
                    rep_factor = _d(sel.factor_value)
                    rep_factor_unit = sel.factor_unit
                    rep_factor_source = sel.source_name
                    rep_factor_version = sel.version
                    rep_factor_code = sel.factor_code
                    rep_emissions_kg = (replaced_qty * rep_factor).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
                    scenario_input.replacement_emission_factor_id = sel.factor_id
                else:
                    has_unresolved_factor = True
                    rep_status = RESULT_STATUS_UNRESOLVED_FACTOR
                    limitations_list.append(f"Solar/replacement factor for '{rep_source_name}' is not currently resolved in the factor registry.")

                rep_result = ScenarioResult(
                    scenario_id=scenario.id,
                    source_name=f"Replacement: {rep_source_name}",
                    scope="SCOPE_2" if "electric" in rep_source_name.lower() or "solar" in rep_source_name.lower() else "SCOPE_1",
                    category="ENERGY" if "electric" in rep_source_name.lower() or "solar" in rep_source_name.lower() else "OTHER",
                    activity_type=rep_source_name,
                    baseline_quantity=Decimal("0.0"),
                    scenario_quantity=replaced_qty,
                    unit=base_unit,
                    baseline_emissions_kgco2e=Decimal("0.0"),
                    scenario_emissions_kgco2e=rep_emissions_kg,
                    reduction_kgco2e=(Decimal("0.0") - rep_emissions_kg).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP) if rep_emissions_kg is not None else None,
                    baseline_factor=None,
                    scenario_factor=rep_factor,
                    factor_unit=rep_factor_unit,
                    factor_source=rep_factor_source,
                    factor_version=rep_factor_version,
                    factor_code=rep_factor_code,
                    calculation_formula=f"{replaced_qty} {base_unit} × {rep_factor} = {rep_emissions_kg} kgCO2e" if rep_factor is not None else "Factor unresolved",
                    status=rep_status,
                    notes=f"Modeled {change_pct}% replacement of {base_act_type} with {rep_source_name}.",
                    created_at=datetime.utcnow(),
                )
                db.add(rep_result)

                assumptions_list.append(f"Replaced {change_pct}% ({replaced_qty} {base_unit}) of {base_act_type} with {rep_source_name}. Remaining original: {remaining_qty} {base_unit}.")

            elif chg_type == SCENARIO_TYPE_ADD_SOURCE:
                # Refinement 1: ADD_SOURCE requiring existing ActivityData + resolved factor
                add_qty = change_pct if change_pct is not None else base_qty
                scenario_input.scenario_quantity = add_qty

                rep_factor_res = self.factor_resolver.resolve(
                    db=db,
                    request=FactorResolutionRequest(
                        activity_type=base_act_type,
                        activity_unit=base_unit,
                        scope=base_scope,
                    )
                )
                add_factor = _d(rep_factor_res.selected_factor.factor_value) if (rep_factor_res and rep_factor_res.status == "MATCHED" and rep_factor_res.selected_factor) else base_factor

                add_emissions_kg = None
                add_status = RESULT_STATUS_QUANTIFIED
                if add_factor is not None:
                    add_emissions_kg = (add_qty * add_factor).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
                else:
                    has_unresolved_factor = True
                    add_status = RESULT_STATUS_UNRESOLVED_FACTOR
                    limitations_list.append(f"Emission factor for added source {base_act_type} is not resolved.")

                add_result = ScenarioResult(
                    scenario_id=scenario.id,
                    source_name=f"Added Source: {base_act_type}",
                    scope=base_scope,
                    category=base_cat,
                    activity_type=base_act_type,
                    baseline_quantity=Decimal("0.0"),
                    scenario_quantity=add_qty,
                    unit=base_unit,
                    baseline_emissions_kgco2e=Decimal("0.0"),
                    scenario_emissions_kgco2e=add_emissions_kg,
                    reduction_kgco2e=(Decimal("0.0") - add_emissions_kg).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP) if add_emissions_kg is not None else None,
                    baseline_factor=None,
                    scenario_factor=add_factor,
                    factor_unit=base_unit,
                    factor_source="Resolver",
                    factor_version="1.0",
                    factor_code="ADD-SRC",
                    calculation_formula=f"{add_qty} {base_unit} × {add_factor} = {add_emissions_kg} kgCO2e" if add_factor is not None else "Factor unresolved",
                    status=add_status,
                    notes=f"Added new verified source {base_act_type}.",
                    created_at=datetime.utcnow(),
                )
                db.add(add_result)
                assumptions_list.append(f"Added {add_qty} {base_unit} of verified source {base_act_type}.")

        # ── PRESERVE UNTOUCHED BASELINE SOURCES ───────────────────────────────
        for entry in baseline_entries:
            if entry.id not in modified_entry_ids:
                entry_co2e_kg = _d(entry.calculated_co2e)
                entry_factor = _d(entry.factor_value) if entry.factor_value is not None else None
                entry_qty = _d(entry.quantity)

                untouched_result = ScenarioResult(
                    scenario_id=scenario.id,
                    source_name=entry.factor_name or entry.activity_type,
                    scope=entry.scope,
                    category=entry.category,
                    activity_type=entry.activity_type,
                    baseline_quantity=entry_qty,
                    scenario_quantity=entry_qty,
                    unit=entry.activity_unit,
                    baseline_emissions_kgco2e=entry_co2e_kg,
                    scenario_emissions_kgco2e=entry_co2e_kg,
                    reduction_kgco2e=Decimal("0.0"),
                    baseline_factor=entry_factor,
                    scenario_factor=entry_factor,
                    factor_unit=entry.factor_unit,
                    factor_source=entry.factor_source,
                    factor_version=entry.factor_version,
                    factor_code=entry.factor_code,
                    calculation_formula=f"{entry_qty} {entry.activity_unit} × {entry_factor} = {entry_co2e_kg} kgCO2e",
                    status=RESULT_STATUS_QUANTIFIED,
                    notes="Baseline activity unchanged in this scenario.",
                    created_at=datetime.utcnow(),
                )
                db.add(untouched_result)

        db.flush()

        # ── 4. AGGREGATE TOTAL SCENARIO FOOTPRINT ──────────────────────────────
        all_results = db.query(ScenarioResult).filter(ScenarioResult.scenario_id == scenario.id).all()

        if has_unresolved_factor or any(r.status == RESULT_STATUS_UNRESOLVED_FACTOR for r in all_results):
            # Refinement 3: When any factor is unresolved, overall total reduction is NULL
            scenario.quantification_status = QUANTIFICATION_STATUS_NOT_QUANTIFIABLE
            scenario.scenario_emissions_kgco2e = None
            scenario.scenario_emissions_tco2e = None
            scenario.reduction_kgco2e = None
            scenario.reduction_tco2e = None
            scenario.reduction_percent = None
            scenario.remaining_target_gap_kgco2e = None
            scenario.remaining_target_gap_tco2e = None
            scenario.target_status = TARGET_STATUS_SCENARIO_NOT_QUANTIFIABLE
            if not limitations_list:
                limitations_list.append(DEFAULT_UNRESOLVED_FACTOR_NOTE)
        else:
            scenario.quantification_status = QUANTIFICATION_STATUS_QUANTIFIED
            total_scenario_kg = sum((_d(r.scenario_emissions_kgco2e) for r in all_results), Decimal("0.0"))
            total_scenario_t = (total_scenario_kg / Decimal("1000.0")).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

            scenario.scenario_emissions_kgco2e = total_scenario_kg
            scenario.scenario_emissions_tco2e = total_scenario_t

            total_reduction_kg = (scenario.baseline_emissions_kgco2e - total_scenario_kg).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
            total_reduction_t = (total_reduction_kg / Decimal("1000.0")).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
            scenario.reduction_kgco2e = total_reduction_kg
            scenario.reduction_tco2e = total_reduction_t

            if scenario.baseline_emissions_kgco2e > Decimal("0.0"):
                red_pct = ((total_reduction_kg / scenario.baseline_emissions_kgco2e) * Decimal("100.0")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
                scenario.reduction_percent = red_pct
            else:
                scenario.reduction_percent = Decimal("0.0")

            # ── 5. TARGET COMPARISON (ROADMAP INTEGRATION) ─────────────────────
            roadmap: Optional[ReductionRoadmap] = None
            if scenario.roadmap_id:
                roadmap = db.query(ReductionRoadmap).filter(ReductionRoadmap.id == scenario.roadmap_id).first()
            elif scenario.document_id:
                roadmap = db.query(ReductionRoadmap).filter(
                    ReductionRoadmap.document_id == scenario.document_id
                ).order_by(ReductionRoadmap.id.desc()).first()

            if roadmap and roadmap.target_emissions_kgco2e is not None:
                target_kg = _d(roadmap.target_emissions_kgco2e)
                gap_kg = (total_scenario_kg - target_kg).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
                gap_t = (gap_kg / Decimal("1000.0")).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

                scenario.remaining_target_gap_kgco2e = gap_kg
                scenario.remaining_target_gap_tco2e = gap_t

                if total_scenario_kg <= target_kg:
                    scenario.target_status = TARGET_STATUS_MET
                else:
                    scenario.target_status = TARGET_STATUS_NOT_MET
            else:
                scenario.target_status = TARGET_STATUS_NOT_DEFINED

        scenario.status = SCENARIO_STATUS_CALCULATED
        scenario.assumption_summary = "; ".join(assumptions_list) if assumptions_list else "Standard scenario model."
        scenario.limitation_summary = "; ".join(limitations_list) if limitations_list else DEFAULT_SCENARIO_CAUTION

    # ==========================================================================
    # 4. CRUD & ARCHIVAL (Refinement 2: Soft Archive by Default)
    # ==========================================================================

    def get_scenario_by_id(self, db: Session, scenario_id: int) -> Optional[EmissionScenario]:
        return db.query(EmissionScenario).filter(EmissionScenario.id == scenario_id).first()

    def list_scenarios(
        self,
        db: Session,
        document_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[EmissionScenario]:
        query = db.query(EmissionScenario)
        if document_id is not None:
            query = query.filter(EmissionScenario.document_id == document_id)
        if status:
            query = query.filter(EmissionScenario.status == status)
        else:
            # By default exclude ARCHIVED unless explicitly requested
            query = query.filter(EmissionScenario.status != SCENARIO_STATUS_ARCHIVED)

        return query.order_by(desc(EmissionScenario.id)).all()

    def update_scenario(
        self,
        db: Session,
        scenario_id: int,
        payload: ScenarioUpdateRequest
    ) -> Optional[EmissionScenario]:
        scenario = self.get_scenario_by_id(db, scenario_id)
        if not scenario:
            return None

        if payload.name is not None:
            scenario.name = payload.name
        if payload.description is not None:
            scenario.description = payload.description
        if payload.status is not None:
            scenario.status = payload.status

        scenario.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(scenario)
        return scenario

    def archive_scenario(self, db: Session, scenario_id: int) -> bool:
        """
        Refinement 2: Archives a scenario rather than deleting to preserve audit lineage.
        """
        scenario = self.get_scenario_by_id(db, scenario_id)
        if not scenario:
            return False

        scenario.status = SCENARIO_STATUS_ARCHIVED
        scenario.updated_at = datetime.utcnow()
        db.commit()
        return True

    def delete_scenario(self, db: Session, scenario_id: int, hard_delete: bool = False) -> bool:
        """
        Deletes or archives a scenario. Defaults to soft archival.
        """
        if not hard_delete:
            return self.archive_scenario(db, scenario_id)

        scenario = self.get_scenario_by_id(db, scenario_id)
        if not scenario:
            return False

        db.delete(scenario)
        db.commit()
        return True
