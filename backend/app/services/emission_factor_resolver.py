"""
services/emission_factor_resolver.py — Deterministic Emission Factor Resolution Engine (Step 12B).

Architecture:
  Activity Data
      ↓
  Activity Type & Unit Normalization
      ↓
  Geography, Year & Scope Normalization
      ↓
  Factor Filtering & Rejection Analysis
      ↓
  Deterministic Resolution Decision (MATCHED / NO_MATCH / MULTIPLE_MATCHES)
      ↓
  FactorResolutionResponse (with explicit match/rejection reasons)

Core Principles:
- The resolver NEVER guesses.
- The resolver NEVER uses an LLM.
- The resolver NEVER silently selects an approximate factor.
- Every candidate factor is tagged with transparent match or rejection reasons.
"""
import re
import logging
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.models.emission_factor import EmissionFactor
from backend.app.schemas.emission_factor import (
    FactorResolutionRequest,
    FactorResolutionCandidate,
    FactorResolutionResponse,
)
from backend.app.services.emission_factor_service import are_units_compatible

logger = logging.getLogger("senseible-emission-factor-resolver")


# ── NORMALIZATION HELPERS ──────────────────────────────────────────────────────

_ACTIVITY_TYPE_MAP: Dict[str, str] = {
    "purchased_electricity": "purchased_electricity",
    "purchased electricity": "purchased_electricity",
    "purchased-electricity": "purchased_electricity",
    "electricity": "purchased_electricity",
    "grid_electricity": "purchased_electricity",
    "grid electricity": "purchased_electricity",
    "diesel": "diesel",
    "diesel_fuel": "diesel",
    "diesel fuel": "diesel",
    "diesel-fuel": "diesel",
    "petrol": "petrol",
    "motor_petrol": "petrol",
    "motor petrol": "petrol",
    "gasoline": "petrol",
    "natural_gas": "natural_gas",
    "natural gas": "natural_gas",
    "png": "natural_gas",
    "cng": "natural_gas",
    "freight": "freight",
    "road_freight": "freight",
    "road freight": "freight",
    "freight transport": "freight",
    "water": "water",
    "water_consumption": "water",
    "water consumption": "water",
    "waste": "waste",
    "hazardous_waste": "waste",
    "hazardous waste": "waste",
    "non_hazardous_waste": "waste",
    "lpg": "lpg",
}

_UNIT_MAP: Dict[str, str] = {
    "kwh": "kWh",
    "kwh_active": "kWh",
    "kilowatt_hour": "kWh",
    "kilowatt-hour": "kWh",
    "l": "L",
    "liter": "L",
    "litre": "L",
    "liters": "L",
    "litres": "L",
    "scm": "scm",
    "m3": "scm",
    "standard_cubic_meter": "scm",
    "tonne_km": "tonne_km",
    "tonne-km": "tonne_km",
    "tkm": "tonne_km",
    "tonne_kilometer": "tonne_km",
    "kg": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    "km": "km",
    "kilometer": "km",
    "kilometers": "km",
}

_SCOPE_MAP: Dict[str, str] = {
    "scope 1": "SCOPE_1",
    "scope_1": "SCOPE_1",
    "scope-1": "SCOPE_1",
    "1": "SCOPE_1",
    "scope 2": "SCOPE_2",
    "scope_2": "SCOPE_2",
    "scope-2": "SCOPE_2",
    "2": "SCOPE_2",
    "scope 3": "SCOPE_3",
    "scope_3": "SCOPE_3",
    "scope-3": "SCOPE_3",
    "3": "SCOPE_3",
    "not applicable": "NOT_APPLICABLE",
    "not_applicable": "NOT_APPLICABLE",
    "n/a": "NOT_APPLICABLE",
    "na": "NOT_APPLICABLE",
}

_GEOGRAPHY_MAP: Dict[str, str] = {
    "india": "India",
    "in": "India",
    "ind": "India",
    "bharat": "India",
    "global": "GLOBAL",
    "world": "GLOBAL",
    "worldwide": "GLOBAL",
}


def normalize_activity_type(activity_str: Optional[str]) -> str:
    """Normalize activity type string to canonical snake_case."""
    if not activity_str:
        return ""
    cleaned = activity_str.strip().lower().replace("-", "_")
    cleaned_spaces = re.sub(r"\s+", " ", cleaned)
    return _ACTIVITY_TYPE_MAP.get(cleaned_spaces, _ACTIVITY_TYPE_MAP.get(cleaned, cleaned))


def normalize_unit(unit_str: Optional[str]) -> str:
    """Normalize activity unit string to canonical format."""
    if not unit_str:
        return ""
    cleaned = unit_str.strip().lower().replace(" ", "_").replace("-", "_")
    return _UNIT_MAP.get(cleaned, unit_str.strip())


def normalize_scope(scope_str: Optional[str]) -> Optional[str]:
    """Normalize scope string to SCOPE_1, SCOPE_2, SCOPE_3, or NOT_APPLICABLE."""
    if not scope_str:
        return None
    cleaned = scope_str.strip().lower()
    return _SCOPE_MAP.get(cleaned, scope_str.strip().upper())


def normalize_geography(geo_str: Optional[str]) -> Optional[str]:
    """Normalize geography to standard casing."""
    if not geo_str:
        return None
    cleaned = geo_str.strip().lower()
    return _GEOGRAPHY_MAP.get(cleaned, geo_str.strip())


def normalize_year(year_val: Any) -> Optional[int]:
    """Validate and convert year to integer."""
    if year_val is None or year_val == "":
        return None
    try:
        return int(year_val)
    except (ValueError, TypeError):
        return None


# ── EMISSION FACTOR RESOLVER ──────────────────────────────────────────────────

class EmissionFactorResolver:
    """
    Deterministic resolution engine for emission factor matching.
    Takes normalized activity details, evaluates candidate validity, and explains decisions.
    """

    def __init__(self):
        self.resolution_version = "1.0"

    def resolve(self, db: Session, request: FactorResolutionRequest) -> FactorResolutionResponse:
        """
        Execute deterministic factor resolution policy.

        Steps:
        1. Validate & normalize request inputs.
        2. Retrieve potential candidates for the activity type.
        3. Evaluate each factor against constraints (status, unit, geography, year, scope, preferred code).
        4. Classify candidates into valid candidates and rejected candidates with explicit reasons.
        5. Apply deterministic decision logic (MATCHED / NO_MATCH / MULTIPLE_MATCHES).
        """
        raw_act = request.activity_type
        raw_unit = request.activity_unit

        if not raw_act or not raw_act.strip():
            return FactorResolutionResponse(
                status="INVALID_REQUEST",
                message="activity_type is required and cannot be empty.",
                resolution_version=self.resolution_version,
            )

        if not raw_unit or not raw_unit.strip():
            return FactorResolutionResponse(
                status="INVALID_REQUEST",
                message="activity_unit is required and cannot be empty.",
                resolution_version=self.resolution_version,
            )

        # Step 1: Normalize inputs
        norm_act = normalize_activity_type(raw_act)
        norm_unit = normalize_unit(raw_unit)
        norm_geo = normalize_geography(request.geography)
        norm_year = normalize_year(request.year)
        norm_scope = normalize_scope(request.scope)
        pref_code = request.preferred_factor_code.strip() if request.preferred_factor_code else None

        # Step 2: Query candidate factors matching the normalized activity type
        factors = db.query(EmissionFactor).filter(
            EmissionFactor.activity_type == norm_act
        ).order_by(desc(EmissionFactor.applicable_year), EmissionFactor.factor_code).all()

        if not factors:
            return FactorResolutionResponse(
                status="NO_MATCH",
                message=f"No emission factors registered for activity type '{norm_act}'.",
                resolution_reasons=[
                    f"No factor exists in registry for activity '{norm_act}'.",
                    "Deterministic resolver does not guess or invent factors.",
                ],
                resolution_version=self.resolution_version,
            )

        valid_candidates: List[FactorResolutionCandidate] = []
        rejected_candidates: List[FactorResolutionCandidate] = []

        # Step 3: Evaluate each candidate factor
        for factor in factors:
            match_reasons: List[str] = [f"Exact activity type match ('{norm_act}')"]
            rejection_reasons: List[str] = []

            # Constraint 1: Status must be ACTIVE
            if factor.status != "ACTIVE":
                rejection_reasons.append(
                    f"Factor status is '{factor.status}'; only ACTIVE factors are eligible for resolution."
                )
            else:
                match_reasons.append("ACTIVE factor status verified")

            # Constraint 2: Activity Unit Compatibility
            if not are_units_compatible(norm_unit, factor.activity_unit):
                rejection_reasons.append(
                    f"Incompatible unit: activity provides '{norm_unit}', but factor expects '{factor.activity_unit}' ({factor.factor_unit})."
                )
            else:
                match_reasons.append(
                    f"Unit '{norm_unit}' is compatible with factor unit '{factor.activity_unit}'"
                )

            # Constraint 3: Geography Match (Strict mode)
            if norm_geo is not None:
                if factor.geography.strip().lower() != norm_geo.lower():
                    rejection_reasons.append(
                        f"Geography mismatch: requested '{norm_geo}', factor geography is '{factor.geography}'."
                    )
                else:
                    match_reasons.append(f"Exact geography match ('{norm_geo}')")

            # Constraint 4: Year Match (Strict mode, no silent fallback)
            if norm_year is not None:
                if factor.applicable_year != norm_year:
                    rejection_reasons.append(
                        f"Applicable year mismatch: requested {norm_year}, factor is {factor.applicable_year or 'Unspecified'}."
                    )
                else:
                    match_reasons.append(f"Exact applicable year match ({norm_year})")

            # Constraint 5: Scope Match (Strict mode, no scope swapping)
            if norm_scope is not None:
                if factor.scope.strip().upper() != norm_scope.upper():
                    rejection_reasons.append(
                        f"Scope mismatch: requested '{norm_scope}', factor scope is '{factor.scope}'."
                    )
                else:
                    match_reasons.append(f"Exact scope match ('{norm_scope}')")

            # Constraint 6: Preferred Factor Code (if supplied)
            if pref_code is not None:
                if factor.factor_code.strip() != pref_code:
                    rejection_reasons.append(
                        f"Factor code '{factor.factor_code}' does not match preferred code '{pref_code}'."
                    )
                else:
                    match_reasons.append(f"Matches preferred factor code '{pref_code}'")

            cand_obj = FactorResolutionCandidate(
                factor_id=factor.id,
                factor_code=factor.factor_code,
                factor_name=factor.factor_name,
                activity_type=factor.activity_type,
                activity_unit=factor.activity_unit,
                factor_unit=factor.factor_unit,
                geography=factor.geography,
                applicable_year=factor.applicable_year,
                scope=factor.scope,
                factor_value=factor.factor_value,
                version=factor.version,
                status=factor.status,
                source_name=factor.source_name,
                source_reference=factor.source_reference,
                match_reasons=match_reasons,
                rejection_reasons=rejection_reasons,
            )

            if len(rejection_reasons) == 0:
                valid_candidates.append(cand_obj)
            else:
                rejected_candidates.append(cand_obj)

        # Step 4: Final State Determination
        if len(valid_candidates) == 1:
            winner = valid_candidates[0]
            resolution_reasons = winner.match_reasons + [
                "Deterministic single factor match achieved without ambiguity."
            ]
            return FactorResolutionResponse(
                status="MATCHED",
                message=f"Deterministically matched factor '{winner.factor_code}' ({winner.factor_value} {winner.factor_unit}).",
                selected_factor=winner,
                candidates=valid_candidates,
                rejected_candidates=rejected_candidates,
                resolution_reasons=resolution_reasons,
                resolution_version=self.resolution_version,
            )

        elif len(valid_candidates) == 0:
            # Build clear explanation of why no candidate matched
            resolution_reasons = [
                f"No active emission factor satisfied all constraints for activity '{norm_act}' with unit '{norm_unit}'.",
            ]
            if norm_geo:
                resolution_reasons.append(f"Requested geography: {norm_geo}")
            if norm_year:
                resolution_reasons.append(f"Requested year: {norm_year}")
            if norm_scope:
                resolution_reasons.append(f"Requested scope: {norm_scope}")
            resolution_reasons.append(
                f"{len(rejected_candidates)} candidate factor(s) evaluated but rejected due to constraint mismatches."
            )

            return FactorResolutionResponse(
                status="NO_MATCH",
                message="No production-ready emission factor is available for this activity under the requested constraints.",
                selected_factor=None,
                candidates=[],
                rejected_candidates=rejected_candidates,
                resolution_reasons=resolution_reasons,
                resolution_version=self.resolution_version,
            )

        else:
            # Multiple candidates satisfy all constraints
            codes = ", ".join(c.factor_code for c in valid_candidates)
            resolution_reasons = [
                f"Ambiguous match: {len(valid_candidates)} active factors satisfy all constraints ({codes}).",
                "Resolver strictly forbids arbitrary selection among valid factors.",
                "Additional constraints (e.g. reporting year, geography, or specific factor code) are required to disambiguate.",
            ]
            return FactorResolutionResponse(
                status="MULTIPLE_MATCHES",
                message=f"Found {len(valid_candidates)} candidate factors satisfying the requested criteria. Manual disambiguation required.",
                selected_factor=None,
                candidates=valid_candidates,
                rejected_candidates=rejected_candidates,
                resolution_reasons=resolution_reasons,
                resolution_version=self.resolution_version,
            )


emission_factor_resolver = EmissionFactorResolver()
