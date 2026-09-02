"""
services/emission_factor_service.py — Emission Factor Registry & Matching Engine (Step 12A).

Deterministic registry for emission factors and unit-safe candidate resolution.
LLMs are NEVER used to invent, select, or modify emission factors.
"""
import logging
from typing import List, Optional, Dict, Set, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.models.emission_factor import EmissionFactor
from backend.app.schemas.emission_factor import (
    EmissionFactorCreate,
    EmissionFactorUpdate,
    EmissionFactorResponse,
    CandidateMatchResponse,
)

logger = logging.getLogger("senseible-emission-factors")

# ── UNIT COMPATIBILITY SPECIFICATIONS ──────────────────────────────────────────
# Maps normalized unit aliases to their canonical activity unit family.
_UNIT_ALIASES: Dict[str, str] = {
    "kwh": "kwh",
    "kwh_active": "kwh",
    "kilowatt_hour": "kwh",
    "kilowatt-hour": "kwh",
    "l": "l",
    "liter": "l",
    "liters": "l",
    "litre": "l",
    "litres": "l",
    "scm": "scm",
    "m3": "scm",
    "cubic_meter": "scm",
    "kg": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    "tonne_km": "tonne_km",
    "tkm": "tonne_km",
    "tonne-km": "tonne_km",
    "tonne_kilometer": "tonne_km",
    "km": "km",
    "kilometer": "km",
    "kilometers": "km",
}


def normalize_unit(unit_str: Optional[str]) -> str:
    """Normalize unit string to canonical key."""
    if not unit_str:
        return ""
    cleaned = unit_str.strip().lower().replace(" ", "_")
    return _UNIT_ALIASES.get(cleaned, cleaned)


def are_units_compatible(activity_unit: str, factor_activity_unit: str) -> bool:
    """
    Check if an activity unit is compatible with the factor's expected activity unit.
    Rejects incompatible unit combinations (e.g. diesel in kWh).
    """
    u1 = normalize_unit(activity_unit)
    u2 = normalize_unit(factor_activity_unit)
    if not u1 or not u2:
        return False
    return u1 == u2


# ── DEMO FACTORS SPECIFICATION ────────────────────────────────────────────────
# Clearly marked demo data for registry development and testing only.
DEMO_FACTORS_SEED: List[Dict] = [
    {
        "factor_code": "DEMO_INDIA_GRID_ELECTRICITY_2024",
        "factor_name": "India Central Electricity Grid Average Factor 2024 (DEMO)",
        "activity_type": "purchased_electricity",
        "category": "ENERGY",
        "scope": "SCOPE_2",
        "factor_value": 0.71,
        "factor_unit": "kgCO2e/kWh",
        "activity_unit": "kWh",
        "geography": "India",
        "applicable_year": 2024,
        "source_name": "DEMO DATA — NOT FOR PRODUCTION",
        "source_reference": "Illustrative CEA Baseline v2024 (Demo)",
        "methodology": "Average Grid Generation Mix (Demo Model)",
        "version": "1.0",
        "status": "ACTIVE",
        "notes": "Demonstration registry factor for Step 12A testing.",
    },
    {
        "factor_code": "DEMO_INDIA_GRID_ELECTRICITY_2025",
        "factor_name": "India Central Electricity Grid Average Factor 2025 (DEMO)",
        "activity_type": "purchased_electricity",
        "category": "ENERGY",
        "scope": "SCOPE_2",
        "factor_value": 0.69,
        "factor_unit": "kgCO2e/kWh",
        "activity_unit": "kWh",
        "geography": "India",
        "applicable_year": 2025,
        "source_name": "DEMO DATA — NOT FOR PRODUCTION",
        "source_reference": "Illustrative CEA Projected Baseline v2025 (Demo)",
        "methodology": "Average Grid Generation Mix (Demo Model)",
        "version": "1.1",
        "status": "ACTIVE",
        "notes": "Demonstration factor illustrating year-over-year coexisting versions.",
    },
    {
        "factor_code": "DEMO_DIESEL_STATIONARY_2024",
        "factor_name": "Diesel Fuel Stationary Combustion (DEMO)",
        "activity_type": "diesel",
        "category": "FUEL",
        "scope": "SCOPE_1",
        "factor_value": 2.68,
        "factor_unit": "kgCO2e/L",
        "activity_unit": "L",
        "geography": "India",
        "applicable_year": 2024,
        "source_name": "DEMO DATA — NOT FOR PRODUCTION",
        "source_reference": "Illustrative Diesel Combustion Factor (Demo)",
        "methodology": "Tier 1 Direct Combustion Factor",
        "version": "1.0",
        "status": "ACTIVE",
        "notes": "Demonstration factor for stationary generator diesel fuel.",
    },
    {
        "factor_code": "DEMO_PETROL_MOBILE_2024",
        "factor_name": "Motor Petrol / Gasoline Combustion (DEMO)",
        "activity_type": "petrol",
        "category": "FUEL",
        "scope": "SCOPE_1",
        "factor_value": 2.31,
        "factor_unit": "kgCO2e/L",
        "activity_unit": "L",
        "geography": "India",
        "applicable_year": 2024,
        "source_name": "DEMO DATA — NOT FOR PRODUCTION",
        "source_reference": "Illustrative Petrol Combustion Factor (Demo)",
        "methodology": "Tier 1 Mobile Combustion Factor",
        "version": "1.0",
        "status": "ACTIVE",
        "notes": "Demonstration factor for vehicle motor petrol.",
    },
    {
        "factor_code": "DEMO_NATURAL_GAS_2024",
        "factor_name": "Natural Gas Combustion (DEMO)",
        "activity_type": "natural_gas",
        "category": "FUEL",
        "scope": "SCOPE_1",
        "factor_value": 2.02,
        "factor_unit": "kgCO2e/scm",
        "activity_unit": "scm",
        "geography": "India",
        "applicable_year": 2024,
        "source_name": "DEMO DATA — NOT FOR PRODUCTION",
        "source_reference": "Illustrative PNG/CNG Factor (Demo)",
        "methodology": "Tier 1 Gas Combustion Factor",
        "version": "1.0",
        "status": "ACTIVE",
        "notes": "Demonstration factor for piped natural gas.",
    },
    {
        "factor_code": "DEMO_ROAD_FREIGHT_2024",
        "factor_name": "Heavy Road Freight Transport (DEMO)",
        "activity_type": "freight",
        "category": "TRANSPORT",
        "scope": "SCOPE_3",
        "factor_value": 0.18,
        "factor_unit": "kgCO2e/tonne_km",
        "activity_unit": "tonne_km",
        "geography": "India",
        "applicable_year": 2024,
        "source_name": "DEMO DATA — NOT FOR PRODUCTION",
        "source_reference": "Illustrative Freight Factor (Demo)",
        "methodology": "Distance-Weight Activity Model",
        "version": "1.0",
        "status": "ACTIVE",
        "notes": "Demonstration factor for logistics road freight transport.",
    },
    {
        "factor_code": "DEMO_INACTIVE_DIESEL_LEGACY",
        "factor_name": "Legacy Diesel Factor - Decommissioned (DEMO INACTIVE)",
        "activity_type": "diesel",
        "category": "FUEL",
        "scope": "SCOPE_1",
        "factor_value": 2.65,
        "factor_unit": "kgCO2e/L",
        "activity_unit": "L",
        "geography": "India",
        "applicable_year": 2020,
        "source_name": "DEMO DATA — NOT FOR PRODUCTION",
        "source_reference": "Historical Legacy Record",
        "methodology": "Decommissioned Method",
        "version": "0.9",
        "status": "INACTIVE",
        "notes": "Demonstration record: Must be excluded from candidate matching.",
    },
    {
        "factor_code": "DEMO_DRAFT_SOLAR_RECs",
        "factor_name": "Experimental Solar REC Factor (DEMO DRAFT)",
        "activity_type": "purchased_electricity",
        "category": "ENERGY",
        "scope": "SCOPE_2",
        "factor_value": 0.05,
        "factor_unit": "kgCO2e/kWh",
        "activity_unit": "kWh",
        "geography": "India",
        "applicable_year": 2024,
        "source_name": "DEMO DATA — NOT FOR PRODUCTION",
        "source_reference": "Draft Research Internal Note",
        "methodology": "Draft Unverified Model",
        "version": "0.1",
        "status": "DRAFT",
        "notes": "Demonstration record: Must be excluded from candidate matching.",
    },
]


class EmissionFactorService:
    """
    Core management and candidate matching service for emission factors.
    Guarantees deterministic matching and auditable provenance.
    """

    def create_factor(self, db: Session, factor_in: EmissionFactorCreate) -> EmissionFactor:
        """Create a new emission factor record."""
        existing = db.query(EmissionFactor).filter(
            EmissionFactor.factor_code == factor_in.factor_code
        ).first()
        if existing:
            raise ValueError(f"Emission factor code '{factor_in.factor_code}' already exists.")

        factor = EmissionFactor(
            factor_code=factor_in.factor_code.strip(),
            factor_name=factor_in.factor_name.strip(),
            activity_type=factor_in.activity_type.strip().lower(),
            category=factor_in.category.strip().upper(),
            scope=factor_in.scope.strip().upper(),
            factor_value=factor_in.factor_value,
            factor_unit=factor_in.factor_unit.strip(),
            activity_unit=factor_in.activity_unit.strip(),
            geography=factor_in.geography.strip(),
            applicable_year=factor_in.applicable_year,
            source_name=factor_in.source_name.strip(),
            source_reference=factor_in.source_reference.strip() if factor_in.source_reference else None,
            methodology=factor_in.methodology.strip() if factor_in.methodology else None,
            version=factor_in.version.strip(),
            effective_from=factor_in.effective_from,
            effective_to=factor_in.effective_to,
            status=factor_in.status.strip().upper(),
            notes=factor_in.notes,
        )
        db.add(factor)
        db.commit()
        db.refresh(factor)
        return factor

    def get_factor(self, db: Session, factor_id: int) -> Optional[EmissionFactor]:
        """Retrieve emission factor by primary key ID."""
        return db.query(EmissionFactor).filter(EmissionFactor.id == factor_id).first()

    def get_factor_by_code(self, db: Session, factor_code: str) -> Optional[EmissionFactor]:
        """Retrieve emission factor by unique factor code."""
        return db.query(EmissionFactor).filter(
            EmissionFactor.factor_code == factor_code.strip()
        ).first()

    def list_factors(
        self,
        db: Session,
        activity_type: Optional[str] = None,
        category: Optional[str] = None,
        scope: Optional[str] = None,
        geography: Optional[str] = None,
        year: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[EmissionFactor]:
        """Query factors with multi-parameter filtering."""
        query = db.query(EmissionFactor)

        if activity_type:
            query = query.filter(EmissionFactor.activity_type == activity_type.strip().lower())
        if category:
            query = query.filter(EmissionFactor.category == category.strip().upper())
        if scope:
            query = query.filter(EmissionFactor.scope == scope.strip().upper())
        if geography:
            query = query.filter(EmissionFactor.geography.ilike(f"%{geography.strip()}%"))
        if year is not None:
            query = query.filter(EmissionFactor.applicable_year == year)
        if status:
            query = query.filter(EmissionFactor.status == status.strip().upper())

        return query.order_by(desc(EmissionFactor.applicable_year), EmissionFactor.factor_code).all()

    def find_candidates(
        self,
        db: Session,
        activity_type: Optional[str],
        activity_unit: Optional[str],
        geography: Optional[str] = None,
        year: Optional[int] = None,
        scope: Optional[str] = None,
    ) -> CandidateMatchResponse:
        """
        Deterministic Candidate Matching Engine.

        Priority rules:
        1. Input validation (activity_type and activity_unit must be provided).
        2. Status constraint: Factor must be ACTIVE (INACTIVE and DRAFT are strictly excluded).
        3. Activity constraint: Exact activity_type match.
        4. Unit compatibility constraint: Activity unit must be strictly compatible with factor's activity_unit.
        5. Geography constraint: When provided, exact match on geography.
        6. Year constraint: When provided, exact match on applicable_year.
        7. Scope constraint: When provided, exact match on scope.

        Returns CandidateMatchResponse with status:
        - MATCHED (exactly 1 candidate)
        - NO_MATCH (0 candidates)
        - MULTIPLE_MATCHES (>1 candidates)
        - INVALID_REQUEST (missing required parameters)
        """
        if not activity_type or not activity_type.strip():
            return CandidateMatchResponse(
                status="INVALID_REQUEST",
                message="Missing required parameter: activity_type",
                matched_factor=None,
                candidate_factors=[],
                match_count=0,
            )

        if not activity_unit or not activity_unit.strip():
            return CandidateMatchResponse(
                status="INVALID_REQUEST",
                message="Missing required parameter: activity_unit",
                matched_factor=None,
                candidate_factors=[],
                match_count=0,
            )

        act_clean = activity_type.strip().lower()
        unit_clean = activity_unit.strip()

        # Step 1: Query ACTIVE factors for this activity type
        query = db.query(EmissionFactor).filter(
            EmissionFactor.status == "ACTIVE",
            EmissionFactor.activity_type == act_clean
        )

        # Step 2: Scope constraint (if provided)
        if scope and scope.strip():
            query = query.filter(EmissionFactor.scope == scope.strip().upper())

        factors = query.all()

        # Step 3: Unit compatibility filter (strict)
        compatible_factors = [
            f for f in factors
            if are_units_compatible(unit_clean, f.activity_unit)
        ]

        if not compatible_factors:
            return CandidateMatchResponse(
                status="NO_MATCH",
                message=f"No active emission factor found with compatible unit '{unit_clean}' for activity '{act_clean}'.",
                matched_factor=None,
                candidate_factors=[],
                match_count=0,
            )

        # Step 4: Geography filter (if provided)
        filtered = compatible_factors
        if geography and geography.strip():
            geo_clean = geography.strip().lower()
            geo_matched = [f for f in filtered if f.geography.strip().lower() == geo_clean]
            if geo_matched:
                filtered = geo_matched
            else:
                # Check for Global fallback only if exact regional match missing
                global_matched = [f for f in filtered if f.geography.strip().upper() == "GLOBAL"]
                if global_matched:
                    filtered = global_matched
                else:
                    return CandidateMatchResponse(
                        status="NO_MATCH",
                        message=f"No active emission factor matches geography '{geography}' for activity '{act_clean}'.",
                        matched_factor=None,
                        candidate_factors=[],
                        match_count=0,
                    )

        # Step 5: Year filter (if provided)
        if year is not None:
            year_matched = [f for f in filtered if f.applicable_year == year]
            if year_matched:
                filtered = year_matched
            else:
                return CandidateMatchResponse(
                    status="NO_MATCH",
                    message=f"No active emission factor matches year {year} for activity '{act_clean}'.",
                    matched_factor=None,
                    candidate_factors=[],
                    match_count=0,
                )

        # Step 6: Evaluate candidate count
        match_count = len(filtered)
        responses = [EmissionFactorResponse.model_validate(f) for f in filtered]

        if match_count == 0:
            return CandidateMatchResponse(
                status="NO_MATCH",
                message=f"No active emission factor found matching the supplied criteria for activity '{act_clean}'.",
                matched_factor=None,
                candidate_factors=[],
                match_count=0,
            )
        elif match_count == 1:
            return CandidateMatchResponse(
                status="MATCHED",
                message=f"Deterministically matched factor '{filtered[0].factor_code}'.",
                matched_factor=responses[0],
                candidate_factors=responses,
                match_count=1,
            )
        else:
            return CandidateMatchResponse(
                status="MULTIPLE_MATCHES",
                message=f"Found {match_count} candidate factors. Additional constraints (e.g. year, geography, scope) are required to disambiguate.",
                matched_factor=None,
                candidate_factors=responses,
                match_count=match_count,
            )

    def seed_demo_factors(self, db: Session) -> int:
        """
        Seed demo factors if not already present.
        Explicitly marked with demo source disclaimers.
        """
        count = 0
        for item in DEMO_FACTORS_SEED:
            existing = db.query(EmissionFactor).filter(
                EmissionFactor.factor_code == item["factor_code"]
            ).first()
            if not existing:
                factor = EmissionFactor(**item)
                db.add(factor)
                count += 1
        if count > 0:
            db.commit()
            logger.info(f"Seeded {count} demo emission factors.")
        return count


emission_factor_service = EmissionFactorService()
