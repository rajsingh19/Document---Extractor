"""
services/carbon_calculation.py — Deterministic Carbon Calculation Engine (Step 13).

Calculates physical CO2e emissions from canonical ActivityData using the EmissionFactorResolver.
ZERO LLM calls. ZERO floating-point arithmetic in final persistence.
Strict Python Decimal arithmetic with ROUND_HALF_UP.
Prevents double counting across TOTAL and COMPONENT activity groups.
"""
import math
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.models.carbon_calculation import CarbonCalculation
from backend.app.models.activity_data import ActivityData
from backend.app.models.document import Document
from backend.app.models.emission_factor import EmissionFactor
from backend.app.schemas.emission_factor import FactorResolutionRequest
from backend.app.services.emission_factor_resolver import emission_factor_resolver
from backend.app.schemas.carbon_calculation import (
    CarbonCalculationRequest,
    CarbonCalculationResponse,
    DocumentCarbonCalculationSummary,
)

logger = logging.getLogger("senseible-carbon-calculation-engine")


class CarbonCalculationEngine:
    """
    Deterministic Carbon Calculation Engine.
    Implements auditable Quantity × Resolved Factor arithmetic without LLMs or arbitrary assumptions.
    """

    def __init__(self):
        self.calculation_version = "1.0"

    def calculate_activity(
        self,
        db: Session,
        request: CarbonCalculationRequest,
        save: bool = True
    ) -> CarbonCalculation:
        """
        Calculate CO2e emissions for a single ActivityData record.
        Strictly uses ActivityData.geography (no request-level override allowed).
        """
        # Step A: Load ActivityData
        activity = db.query(ActivityData).filter(
            ActivityData.id == request.activity_data_id
        ).first()

        if not activity:
            calc = CarbonCalculation(
                activity_data_id=request.activity_data_id,
                activity_type="unknown",
                activity_role="TOTAL",
                quantity=Decimal("0.0"),
                activity_unit="unknown",
                status="ERROR",
                calculation_reason=f"ActivityData record ID {request.activity_data_id} not found.",
                calculation_version=self.calculation_version,
            )
            if save:
                db.add(calc)
                db.commit()
                db.refresh(calc)
            return calc

        # Idempotency check: if already calculated and force_recalculate is False
        if not request.force_recalculate:
            existing = db.query(CarbonCalculation).filter(
                CarbonCalculation.activity_data_id == activity.id,
                CarbonCalculation.calculation_version == self.calculation_version
            ).order_by(desc(CarbonCalculation.id)).first()

            if existing and existing.status in ["CALCULATED", "INELIGIBLE", "NO_FACTOR", "MISSING_GEOGRAPHY"]:
                return existing

        # Step B: Validate normalization status & physical quantity
        if (
            activity.normalization_status == "INVALID"
            or activity.quantity is None
            or activity.quantity < 0
            or math.isnan(activity.quantity)
            or math.isinf(activity.quantity)
            or not activity.unit
        ):
            reason = "Invalid activity data: " + (activity.normalization_reasons or "Negative, NaN, or missing quantity/unit.")
            return self._record_failure(
                db, activity, status="INVALID_ACTIVITY", reason=reason, save=save
            )

        # Step C: Calculation Eligibility
        # Derived deterministically from activity_role
        if activity.activity_role == "SUPPORTING" or not activity.calculation_eligible:
            return self._record_failure(
                db,
                activity,
                status="INELIGIBLE",
                reason=f"Operational supporting metric ({activity.activity_type}) is strictly non-eligible for carbon calculation.",
                save=save
            )

        # Step D: Factor Resolution via existing EmissionFactorResolver (Single Source of Truth)
        # Distinguish solar/renewable electricity generation from purchased utility grid electricity
        req_activity_type = activity.activity_type
        if activity.activity_type == "purchased_electricity":
            is_solar = (
                "solar" in (activity.source_field or "").lower()
                or "renewable" in (activity.source_field or "").lower()
                or "solar" in (activity.source_text or "").lower()
            )
            if is_solar:
                req_activity_type = "solar_electricity"

        resolution_req = FactorResolutionRequest(
            activity_type=req_activity_type,
            activity_unit=activity.unit,
            geography=activity.geography,
            year=activity.reporting_year,
            scope=activity.scope,
            category=activity.category,
        )

        resolution = emission_factor_resolver.resolve(db, resolution_req)

        # Check if missing geography caused failure or if selected factor strictly requires explicit geography
        if activity.geography is None:
            if resolution.selected_factor:
                f_src = (resolution.selected_factor.source_name or "").lower()
                f_code = (resolution.selected_factor.factor_code or "").lower()
                if "requires_geography" in f_src or "regional_only" in f_code:
                    return self._record_failure(
                        db,
                        activity,
                        status="MISSING_GEOGRAPHY",
                        reason="Selected emission factor strictly requires explicit geographic specification.",
                        save=save
                    )

        # Check if missing year
        if activity.reporting_year is None:
            if resolution.status in ["NO_MATCH", "MULTIPLE_MATCHES"] or (resolution.selected_factor and resolution.selected_factor.applicable_year):
                # If year is required and activity year is None
                candidates = db.query(EmissionFactor).filter(
                    EmissionFactor.activity_type == activity.activity_type,
                    EmissionFactor.status == "ACTIVE"
                ).all()
                if any(c.applicable_year is not None for c in candidates):
                    return self._record_failure(
                        db,
                        activity,
                        status="MISSING_YEAR",
                        reason="Applicable reporting year is missing and required for emission factor resolution.",
                        save=save
                    )

        if resolution.status == "NO_MATCH":
            # Check if rejection was due to geography
            if any("geography" in r.lower() for r in (resolution.resolution_reasons or [])):
                return self._record_failure(
                    db, activity, status="MISSING_GEOGRAPHY", reason="Geography mismatch or unspecified geography prevents factor resolution.", save=save
                )
            reason = resolution.message or f"No matching active emission factor found for '{activity.activity_type}' in {activity.geography or 'Unspecified'}."
            return self._record_failure(
                db, activity, status="NO_FACTOR", reason=reason, save=save
            )

        if resolution.status == "MULTIPLE_MATCHES":
            reason = "Multiple active emission factors matched all constraints; automatic selection is prohibited to prevent guessing."
            return self._record_failure(
                db, activity, status="MULTIPLE_FACTORS", reason=reason, save=save
            )

        if resolution.status == "INVALID_REQUEST":
            reason = resolution.message or "Invalid resolution request constraints."
            return self._record_failure(
                db, activity, status="UNSUPPORTED_UNIT", reason=reason, save=save
            )

        if resolution.status != "MATCHED" or not resolution.selected_factor:
            return self._record_failure(
                db, activity, status="NO_FACTOR", reason="Factor resolution did not produce a valid candidate.", save=save
            )

        # Step G: Deterministic Decimal Arithmetic
        factor = resolution.selected_factor

        try:
            qty_dec = Decimal(str(activity.quantity))
            factor_val_dec = Decimal(str(factor.factor_value))
            # Multiply and quantize with ROUND_HALF_UP to 4 decimal places
            co2e_dec = (qty_dec * factor_val_dec).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        except Exception as err:
            logger.error(f"Decimal arithmetic error for activity {activity.id}: {err}")
            return self._record_failure(
                db, activity, status="ERROR", reason=f"Decimal arithmetic calculation error: {err}", save=save
            )

        # Build human-readable formula string
        # e.g. "420 L × 2.68 kgCO2e/L = 1125.6000 kgCO2e"
        formula = f"{activity.quantity:g} {activity.unit} × {factor.factor_value:g} {factor.factor_unit} = {co2e_dec} kgCO2e"

        # Step H: Idempotent Persistence
        calc = db.query(CarbonCalculation).filter(
            CarbonCalculation.activity_data_id == activity.id,
            CarbonCalculation.calculation_version == self.calculation_version
        ).first()

        if not calc:
            calc = CarbonCalculation(
                activity_data_id=activity.id,
                document_id=activity.document_id,
                metric_id=activity.metric_id,
                activity_type=activity.activity_type,
                activity_role=activity.activity_role,
                activity_group_id=activity.activity_group_id,
                quantity=qty_dec,
                activity_unit=activity.unit,
                emission_factor_id=factor.factor_id,
                factor_code=factor.factor_code,
                factor_name=factor.factor_name,
                factor_value=factor_val_dec,
                factor_unit=factor.factor_unit,
                factor_version=factor.version,
                factor_source=factor.source_name,
                geography=activity.geography,
                reporting_period=activity.reporting_period,
                reporting_year=activity.reporting_year,
                scope=factor.scope or activity.scope,
                calculated_co2e=co2e_dec,
                calculated_co2e_unit="kgCO2e",
                formula=formula,
                calculation_version=self.calculation_version,
                status="CALCULATED",
                calculation_reason="Calculated successfully via matched emission factor.",
                source_field=activity.source_field,
                source_text=activity.source_text,
                page=activity.page,
            )
            if save:
                db.add(calc)
                db.commit()
                db.refresh(calc)
        else:
            # Update existing record deterministically
            calc.quantity = qty_dec
            calc.activity_unit = activity.unit
            calc.emission_factor_id = factor.factor_id
            calc.factor_code = factor.factor_code
            calc.factor_name = factor.factor_name
            calc.factor_value = factor_val_dec
            calc.factor_unit = factor.factor_unit
            calc.factor_version = factor.version
            calc.factor_source = factor.source_name
            calc.geography = activity.geography
            calc.reporting_period = activity.reporting_period
            calc.reporting_year = activity.reporting_year
            calc.scope = factor.scope or activity.scope
            calc.calculated_co2e = co2e_dec
            calc.formula = formula
            calc.status = "CALCULATED"
            calc.calculation_reason = "Calculated successfully via matched emission factor."
            calc.source_field = activity.source_field
            calc.source_text = activity.source_text
            calc.page = activity.page
            if save:
                db.commit()
                db.refresh(calc)

        return calc

    def _record_failure(
        self,
        db: Session,
        activity: ActivityData,
        status: str,
        reason: str,
        save: bool = True
    ) -> CarbonCalculation:
        """Helper to idempotently record an ineligible, failed, or non-calculated activity."""
        calc = db.query(CarbonCalculation).filter(
            CarbonCalculation.activity_data_id == activity.id,
            CarbonCalculation.calculation_version == self.calculation_version
        ).first()

        qty_dec = Decimal(str(activity.quantity)) if activity.quantity is not None and not math.isnan(activity.quantity) and not math.isinf(activity.quantity) else Decimal("0.0")

        if not calc:
            calc = CarbonCalculation(
                activity_data_id=activity.id,
                document_id=activity.document_id,
                metric_id=activity.metric_id,
                activity_type=activity.activity_type,
                activity_role=activity.activity_role,
                activity_group_id=activity.activity_group_id,
                quantity=qty_dec,
                activity_unit=activity.unit or "unknown",
                geography=activity.geography,
                reporting_period=activity.reporting_period,
                reporting_year=activity.reporting_year,
                scope=activity.scope,
                calculated_co2e=None,
                formula=None,
                calculation_version=self.calculation_version,
                status=status,
                calculation_reason=reason,
                source_field=activity.source_field,
                source_text=activity.source_text,
                page=activity.page,
            )
            if save:
                db.add(calc)
                db.commit()
                db.refresh(calc)
        else:
            calc.status = status
            calc.calculation_reason = reason
            calc.calculated_co2e = None
            calc.formula = None
            if save:
                db.commit()
                db.refresh(calc)

        return calc

    def calculate_document_emissions(
        self,
        db: Session,
        document_id: int
    ) -> DocumentCarbonCalculationSummary:
        """
        Batch calculate carbon emissions for all ActivityData associated with a document.
        Applies deterministic double-counting protection across TOTAL and COMPONENT activity groups.
        """
        activities = db.query(ActivityData).filter(
            ActivityData.document_id == document_id
        ).order_by(ActivityData.id.asc()).all()

        calculations: List[CarbonCalculation] = []
        for act in activities:
            calc = self.calculate_activity(
                db,
                CarbonCalculationRequest(activity_data_id=act.id, force_recalculate=True),
                save=True
            )
            calculations.append(calc)

        # Aggregate counts
        total_count = len(calculations)
        calculated_count = sum(1 for c in calculations if c.status == "CALCULATED")
        ineligible_count = sum(1 for c in calculations if c.status == "INELIGIBLE")
        no_factor_count = sum(1 for c in calculations if c.status == "NO_FACTOR")
        multiple_factor_count = sum(1 for c in calculations if c.status == "MULTIPLE_FACTORS")
        invalid_count = sum(1 for c in calculations if c.status in ["INVALID_ACTIVITY", "UNSUPPORTED_UNIT", "MISSING_GEOGRAPHY", "MISSING_YEAR", "ERROR"])

        # Double-Counting Protection & Aggregation Algorithm:
        # Group calculations by activity_group_id
        groups: Dict[Optional[str], List[CarbonCalculation]] = {}
        for c in calculations:
            gid = c.activity_group_id
            if gid not in groups:
                groups[gid] = []
            groups[gid].append(c)

        aggregated_calcs: List[CarbonCalculation] = []

        for gid, group_calcs in groups.items():
            if not gid:
                # Standalone activities without group: include if CALCULATED
                for c in group_calcs:
                    if c.status == "CALCULATED":
                        aggregated_calcs.append(c)
                continue

            has_total = any(c.activity_role == "TOTAL" for c in group_calcs)
            has_components = any(c.activity_role == "COMPONENT" for c in group_calcs)

            if has_total and has_components:
                # CASE A: TOTAL + COMPONENTS (e.g. Document #1 electricity)
                # Constituent components are included; TOTAL is excluded to prevent double-counting.
                for c in group_calcs:
                    if c.activity_role == "COMPONENT" and c.status == "CALCULATED":
                        aggregated_calcs.append(c)
            elif has_total and not has_components:
                # CASE B: TOTAL ONLY (e.g. standalone diesel)
                for c in group_calcs:
                    if c.activity_role == "TOTAL" and c.status == "CALCULATED":
                        aggregated_calcs.append(c)
            elif has_components and not has_total:
                # CASE C: COMPONENTS ONLY
                for c in group_calcs:
                    if c.activity_role == "COMPONENT" and c.status == "CALCULATED":
                        aggregated_calcs.append(c)
            else:
                # Ambiguous: safely include any calculated non-total items
                for c in group_calcs:
                    if c.status == "CALCULATED" and c.activity_role != "TOTAL":
                        aggregated_calcs.append(c)

        # Sum calculated CO2e deterministically using Python Decimal
        scope_1_sum = Decimal("0.0")
        scope_2_sum = Decimal("0.0")
        scope_3_sum = Decimal("0.0")
        total_sum = Decimal("0.0")

        for c in aggregated_calcs:
            val = Decimal(str(c.calculated_co2e))
            total_sum += val
            if c.scope == "SCOPE_1":
                scope_1_sum += val
            elif c.scope == "SCOPE_2":
                scope_2_sum += val
            elif c.scope == "SCOPE_3":
                scope_3_sum += val

        return DocumentCarbonCalculationSummary(
            document_id=document_id,
            total_activity_records=total_count,
            calculated_records=calculated_count,
            ineligible_records=ineligible_count,
            no_factor_records=no_factor_count,
            multiple_factor_records=multiple_factor_count,
            invalid_records=invalid_count,
            total_calculated_co2e=float(total_sum) if calculated_count > 0 else None,
            total_calculated_co2e_unit="kgCO2e",
            scope_1_calculated_co2e=float(scope_1_sum) if scope_1_sum > 0 else None,
            scope_2_calculated_co2e=float(scope_2_sum) if scope_2_sum > 0 else None,
            scope_3_calculated_co2e=float(scope_3_sum) if scope_3_sum > 0 else None,
            calculations=[CarbonCalculationResponse.model_validate(c) for c in calculations],
        )


carbon_calculation_engine = CarbonCalculationEngine()
