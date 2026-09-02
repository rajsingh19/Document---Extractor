"""
services/activity_data_normalizer.py — Canonical Activity Data Normalization Engine (Step 12C).

Architecture:
  Document / Raw Metric
      ↓
  Activity Type & Category Classification
      ↓
  Activity Role (TOTAL, COMPONENT, SUPPORTING) & Calculation Eligibility Derivation
      ↓
  Activity Grouping (doc_{id}_electricity_{period}) to prevent double-counting
      ↓
  Quantity Parsing & Strict Negative/NaN Validation
      ↓
  Unit Normalization & Activity/Unit Compatibility Verification
      ↓
  Strict Nullable Geography (never fabricated) & Reporting Period Normalization
      ↓
  Provenance Preservation (source field, exact source text, page)
      ↓
  Canonical ActivityData (ready for Step 13 without CO2e calculation)
"""
import re
import math
import logging
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session

from backend.app.models.activity_data import ActivityData
from backend.app.models.sustainability_metric import SustainabilityMetric
from backend.app.models.document import Document
from backend.app.schemas.activity_data import (
    ActivityDataNormalizeRequest,
    NormalizationPreviewResponse,
)
from backend.app.utils.number_parser import parse_indian_number

logger = logging.getLogger("senseible-activity-data-normalizer")

# Canonical activity categories
ACTIVITY_CATEGORIES: Dict[str, str] = {
    "purchased_electricity": "ENERGY",
    "diesel": "FUEL",
    "petrol": "FUEL",
    "natural_gas": "FUEL",
    "lpg": "FUEL",
    "freight": "TRANSPORT",
    "water": "WATER",
    "waste": "WASTE",
    "other": "OTHER",
}

# Strict activity unit compatibility definitions
COMPATIBLE_UNITS: Dict[str, List[str]] = {
    "purchased_electricity": ["kWh", "MWh"],
    "diesel": ["L"],
    "petrol": ["L"],
    "natural_gas": ["scm"],
    "lpg": ["kg", "L"],
    "freight": ["tonne_km"],
    "water": ["kL"],
    "waste": ["kg", "tonne"],
    "other": ["kVA", "ratio", "unitless", "other", ""],
}

# Raw activity type alias mapping
ACTIVITY_TYPE_ALIASES: Dict[str, str] = {
    "electricity": "purchased_electricity",
    "electricity consumption": "purchased_electricity",
    "electricity_consumption": "purchased_electricity",
    "electricity usage": "purchased_electricity",
    "purchased electricity": "purchased_electricity",
    "purchased_electricity": "purchased_electricity",
    "purchased power": "purchased_electricity",
    "grid electricity": "purchased_electricity",
    "grid_electricity": "purchased_electricity",
    "solar electricity": "purchased_electricity",
    "solar_electricity": "purchased_electricity",
    "renewable energy": "purchased_electricity",
    "renewable_energy": "purchased_electricity",
    "solar": "purchased_electricity",
    "diesel": "diesel",
    "diesel fuel": "diesel",
    "diesel_fuel": "diesel",
    "diesel consumption": "diesel",
    "diesel used": "diesel",
    "fuel_consumption": "diesel",
    "fuel consumption": "diesel",
    "petrol": "petrol",
    "petrol fuel": "petrol",
    "gasoline": "petrol",
    "natural gas": "natural_gas",
    "natural_gas": "natural_gas",
    "natural gas consumption": "natural_gas",
    "cng": "natural_gas",
    "png": "natural_gas",
    "freight": "freight",
    "freight transport": "freight",
    "goods transport": "freight",
    "transportation": "freight",
    "water": "water",
    "water consumption": "water",
    "water_consumption": "water",
    "waste": "waste",
    "waste generated": "waste",
    "hazardous_waste": "waste",
    "non_hazardous_waste": "waste",
    "peak_demand": "other",
    "peak demand": "other",
    "power_factor": "other",
    "power factor": "other",
}

# Unit alias mapping
UNIT_ALIASES: Dict[str, str] = {
    "kwh": "kWh",
    "kwh_active": "kWh",
    "kilowatt hour": "kWh",
    "kilowatt-hour": "kWh",
    "mwh": "MWh",
    "megawatt hour": "MWh",
    "megawatt-hour": "MWh",
    "l": "L",
    "liter": "L",
    "litre": "L",
    "liters": "L",
    "litres": "L",
    "scm": "scm",
    "m3": "scm",
    "m³": "scm",
    "standard_cubic_meter": "scm",
    "kg": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    "tonne": "tonne",
    "tonnes": "tonne",
    "metric ton": "tonne",
    "metric tonne": "tonne",
    "mt": "tonne",
    "tonne_km": "tonne_km",
    "tonne-km": "tonne_km",
    "tkm": "tonne_km",
    "tonne_kilometer": "tonne_km",
    "kl": "kL",
    "kilolitre": "kL",
    "kiloliter": "kL",
    "kva": "kVA",
    "pf": "ratio",
}

# Output emission metric types that MUST NEVER be mapped into ActivityData
EMISSION_METRICS_EXCLUSION: set = {
    "scope_1_emissions",
    "scope_2_emissions",
    "scope_3_emissions",
    "total_ghg_emissions",
    "ghg_emissions",
    "total_emissions",
    "carbon_emissions",
}


def normalize_activity_type(raw_str: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Return (activity_type, category) or (None, None) if unmappable."""
    if not raw_str:
        return None, None
    cleaned = raw_str.strip().lower().replace("-", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    act_type = ACTIVITY_TYPE_ALIASES.get(cleaned)
    if not act_type:
        # Check direct match against canonical keys
        if cleaned.replace(" ", "_") in ACTIVITY_CATEGORIES:
            act_type = cleaned.replace(" ", "_")
    if act_type:
        return act_type, ACTIVITY_CATEGORIES.get(act_type, "OTHER")
    return None, None


def normalize_unit(unit_str: Optional[str]) -> Optional[str]:
    """Normalize unit string to canonical representation."""
    if not unit_str:
        return None
    cleaned = unit_str.strip().lower().replace("-", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return UNIT_ALIASES.get(cleaned, unit_str.strip())


def normalize_geography(geo_str: Optional[str]) -> Optional[str]:
    """
    Strictly normalize geography ONLY if explicitly established.
    Never defaults to India.
    """
    if not geo_str or not str(geo_str).strip():
        return None
    cleaned = str(geo_str).strip().lower()
    if cleaned in ["india", "in", "ind", "bharat"]:
        return "India"
    if cleaned in ["global", "world", "worldwide"]:
        return "GLOBAL"
    return str(geo_str).strip()


def normalize_reporting_period(period_str: Optional[str]) -> Tuple[Optional[str], Optional[int]]:
    """
    Normalize reporting period into (period_YYYY_MM, reporting_year).
    Never fabricates missing dates.
    """
    if not period_str or not str(period_str).strip():
        return None, None
    s = str(period_str).strip()

    # Match YYYY-MM
    match_iso = re.search(r'(\d{4})-(\d{2})', s)
    if match_iso:
        year = int(match_iso.group(1))
        return match_iso.group(0), year

    # Match Month Year (e.g. "October 2024", "Oct 2024")
    months = {
        "jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
        "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12"
    }
    match_month = re.search(r'([A-Za-z]{3,9})\s+(\d{4})', s)
    if match_month:
        m_name = match_month.group(1).lower()[:3]
        year = int(match_month.group(2))
        if m_name in months:
            return f"{year}-{months[m_name]}", year

    # Match Year only (e.g. "2024")
    match_year = re.search(r'\b(19\d\d|20\d\d)\b', s)
    if match_year:
        year = int(match_year.group(1))
        return None, year

    return None, None


class ActivityDataNormalizer:
    """
    Deterministic Activity Data Normalization Service.
    Converts extracted metrics into canonical physical activity records for Step 13.
    """

    def __init__(self):
        self.normalization_version = "1.0"

    def preview_normalization(self, request: ActivityDataNormalizeRequest) -> NormalizationPreviewResponse:
        """
        Preview activity data normalization without persisting to database.
        """
        reasons: List[str] = []
        status = "VALID"

        # 1. Activity Type & Category
        raw_act = request.activity_type or request.source_field or ""
        act_type, category = normalize_activity_type(raw_act)
        if not act_type:
            status = "NEEDS_REVIEW"
            act_type = "other"
            category = "OTHER"
            reasons.append(f"Unrecognized activity type '{raw_act}'; classified as 'other' for review.")
        else:
            reasons.append(f"Normalized activity type to '{act_type}' ({category}).")

        # 2. Activity Role & Calculation Eligibility
        # Derived deterministically from activity type or suggested role
        role_raw = (request.activity_role or "").upper().strip()
        raw_act_clean = raw_act.lower().replace(" ", "_").replace("-", "_")

        if "peak_demand" in raw_act_clean or "power_factor" in raw_act_clean or role_raw == "SUPPORTING":
            activity_role = "SUPPORTING"
            calculation_eligible = False
            reasons.append("Activity role is SUPPORTING; strictly excluded from carbon calculations.")
        elif "grid" in raw_act_clean or "solar" in raw_act_clean or "renewable" in raw_act_clean or role_raw == "COMPONENT":
            activity_role = "COMPONENT"
            calculation_eligible = True
            reasons.append("Activity role is COMPONENT; constituent part of an aggregated total.")
        else:
            activity_role = "TOTAL"
            calculation_eligible = True
            reasons.append("Activity role is TOTAL; primary aggregate activity quantity.")

        # 3. Quantity Parsing & Safety
        raw_qty = request.quantity
        if raw_qty is None and request.source_text:
            raw_qty = request.source_text

        parsed_qty = parse_indian_number(raw_qty)
        if parsed_qty is None:
            status = "INVALID"
            reasons.append("Failed to parse a valid numeric activity quantity.")
        elif math.isnan(parsed_qty) or math.isinf(parsed_qty):
            status = "INVALID"
            parsed_qty = None
            reasons.append("Invalid numeric quantity: NaN or infinity rejected.")
        elif parsed_qty < 0:
            status = "INVALID"
            reasons.append(f"Negative activity quantity ({parsed_qty}) is invalid; activity amounts must be non-negative.")
        else:
            reasons.append(f"Parsed non-negative activity quantity: {parsed_qty}")

        # 4. Unit Normalization & Compatibility Check
        norm_unit = normalize_unit(request.unit)
        if not norm_unit and isinstance(request.quantity, str):
            unit_match = re.search(r'[a-zA-Z_³]+', request.quantity)
            if unit_match:
                norm_unit = normalize_unit(unit_match.group(0))

        if not norm_unit:
            if status != "INVALID":
                status = "NEEDS_REVIEW"
            reasons.append(f"Missing or unrecognized unit '{request.unit}'.")
        else:
            reasons.append(f"Normalized unit to '{norm_unit}'.")

        # Check compatibility with activity_type
        if act_type in COMPATIBLE_UNITS and norm_unit:
            valid_units = COMPATIBLE_UNITS[act_type]
            if valid_units and norm_unit not in valid_units and "other" not in valid_units:
                status = "INVALID"
                reasons.append(
                    f"Incompatible activity/unit combination: activity '{act_type}' cannot be measured in unit '{norm_unit}'. Allowed: {valid_units}"
                )

        # 5. Geography (Strictly Nullable, No Fabrication)
        norm_geo = normalize_geography(request.geography)
        if norm_geo:
            reasons.append(f"Explicit geography established: '{norm_geo}'.")
        else:
            reasons.append("No explicit geography provided; geography is None (not fabricated).")

        # 6. Reporting Period & Year
        period, year = normalize_reporting_period(request.reporting_period)
        if request.reporting_year and not year:
            year = request.reporting_year

        if period:
            reasons.append(f"Normalized reporting period: '{period}' (year {year}).")
        elif year:
            reasons.append(f"Normalized reporting year: {year} (period unspecified).")
        else:
            reasons.append("Reporting period is unspecified (no date fabricated).")

        # 7. Activity Grouping ID (Deterministic preview)
        group_id = None
        if act_type == "purchased_electricity":
            p_suffix = (period or str(year) or "general").replace("-", "_")
            group_id = f"electricity_{p_suffix}"
            reasons.append(f"Assigned activity group ID: '{group_id}' to link electricity components.")

        return NormalizationPreviewResponse(
            status=status,
            activity_type=act_type,
            category=category,
            activity_role=activity_role,
            calculation_eligible=calculation_eligible,
            activity_group_id=group_id,
            quantity=parsed_qty,
            unit=norm_unit,
            geography=norm_geo,
            reporting_period=period,
            reporting_year=year,
            scope=request.scope,
            reasons=reasons,
            normalization_version=self.normalization_version,
        )

    def normalize_metric(
        self,
        db: Session,
        metric: SustainabilityMetric,
        document: Optional[Document] = None,
        save: bool = True
    ) -> Optional[ActivityData]:
        """
        Normalize an existing SustainabilityMetric row into a canonical ActivityData record.
        Strictly excludes calculated emission metrics (scope 1/2/total).
        Guarantees idempotent deduplication.
        """
        m_type = (metric.metric_type or "").strip().lower()

        # Step 1: Strict exclusion of emission outputs
        if m_type in EMISSION_METRICS_EXCLUSION or "emission" in m_type or metric.category == "carbon":
            return None

        # Step 2: Activity Type & Category
        act_type, category = normalize_activity_type(m_type)
        if not act_type:
            act_type = "other"
            category = "OTHER"

        # Step 3: Determine Activity Role and Calculation Eligibility
        if m_type in ["peak_demand", "power_factor"] or metric.category == "financial" or m_type == "cost":
            activity_role = "SUPPORTING"
            calculation_eligible = False
        elif m_type in ["grid_electricity", "solar_electricity", "renewable_energy"]:
            activity_role = "COMPONENT"
            calculation_eligible = True
        else:
            activity_role = "TOTAL"
            calculation_eligible = True

        # Step 4: Activity Grouping (e.g. link total, grid, and solar electricity for a document)
        doc_id = metric.document_id or (document.id if document else None)
        period_str = getattr(metric, "reporting_period", None) or (document.reporting_period if document else None) or getattr(metric, "period_start", None)
        period, year = normalize_reporting_period(period_str)
        if not year and getattr(metric, "period_start", None):
            _, year = normalize_reporting_period(metric.period_start)

        activity_group_id = None
        if act_type == "purchased_electricity" and doc_id:
            p_clean = (period or str(year) or "general").replace("-", "_")
            activity_group_id = f"doc_{doc_id}_electricity_{p_clean}"

        # Step 5: Quantity & Unit Validation
        raw_val = metric.value
        parsed_qty = parse_indian_number(raw_val)
        norm_unit = normalize_unit(metric.unit)

        status = "VALID"
        reasons = []

        if parsed_qty is None or math.isnan(parsed_qty) or math.isinf(parsed_qty):
            status = "INVALID"
            reasons.append("Invalid numeric quantity.")
        elif parsed_qty < 0:
            status = "INVALID"
            reasons.append("Negative activity quantity.")

        if not norm_unit:
            status = "NEEDS_REVIEW"
            reasons.append("Unrecognized unit.")
        elif act_type in COMPATIBLE_UNITS and norm_unit not in COMPATIBLE_UNITS[act_type]:
            if "other" not in COMPATIBLE_UNITS[act_type]:
                status = "INVALID"
                reasons.append(f"Incompatible unit '{norm_unit}' for activity '{act_type}'.")

        # Step 6: Geography (Strictly Nullable)
        # Only set if explicitly provided on document/business metadata
        geography = None
        if document and getattr(document, "geography", None):
            geography = normalize_geography(document.geography)
        elif getattr(metric, "geography", None):
            geography = normalize_geography(metric.geography)

        # Step 7: Scope assignment if applicable
        scope = None
        if act_type == "purchased_electricity":
            scope = "SCOPE_2"
        elif act_type in ["diesel", "petrol", "natural_gas", "lpg"]:
            scope = "SCOPE_1"
        elif act_type == "freight":
            scope = "SCOPE_3"

        # Step 8: Deduplication Check (Idempotency)
        existing = db.query(ActivityData).filter(
            ActivityData.document_id == doc_id,
            ActivityData.metric_id == metric.id,
            ActivityData.activity_type == act_type,
            ActivityData.quantity == parsed_qty,
            ActivityData.unit == (norm_unit or ""),
            ActivityData.activity_role == activity_role,
        ).first()

        if existing:
            return existing

        activity = ActivityData(
            document_id=doc_id,
            metric_id=metric.id,
            activity_type=act_type,
            category=category,
            activity_role=activity_role,
            calculation_eligible=calculation_eligible,
            activity_group_id=activity_group_id,
            quantity=parsed_qty if parsed_qty is not None else 0.0,
            unit=norm_unit or metric.unit or "unknown",
            geography=geography,
            reporting_period=period,
            reporting_year=year,
            scope=scope,
            source_field=metric.source_field,
            source_text=metric.source_text,
            page=getattr(metric, "page", None),
            verification_status=metric.verification_status or "UNVERIFIED",
            normalization_status=status,
            normalization_reasons="; ".join(reasons) if reasons else "Normalized successfully",
            normalization_version=self.normalization_version,
        )

        if save:
            db.add(activity)
            db.commit()
            db.refresh(activity)

        return activity

    def sync_document_activities(self, db: Session, document_id: int) -> List[ActivityData]:
        """
        Idempotently normalize and synchronize all eligible sustainability metrics
        for a document into canonical ActivityData records.
        """
        doc = db.query(Document).filter(Document.id == document_id).first()
        metrics = db.query(SustainabilityMetric).filter(
            SustainabilityMetric.document_id == document_id
        ).all()

        synced: List[ActivityData] = []
        for m in metrics:
            item = self.normalize_metric(db, m, doc, save=True)
            if item:
                synced.append(item)

        return synced


activity_data_normalizer = ActivityDataNormalizer()
