import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.models.document import Document
from backend.app.models.sustainability_metric import SustainabilityMetric

logger = logging.getLogger("senseible-document-ai")

METRIC_MAPPINGS: List[Dict[str, Any]] = [
    # Energy
    {
        "section": "energy",
        "key": "electricity_kwh",
        "metric_type": "electricity_consumption",
        "category": "energy",
        "default_unit": "kWh",
    },
    {
        "section": "energy",
        "key": "renewable_energy_kwh",
        "metric_type": "renewable_energy",
        "category": "energy",
        "default_unit": "kWh",
    },
    {
        "section": "energy",
        "key": "fuel_diesel_liters",
        "metric_type": "fuel_consumption",
        "category": "energy",
        "default_unit": "Liters",
    },
    {
        "section": "energy",
        "key": "peak_demand_kva_kw",
        "metric_type": "peak_demand",
        "category": "energy",
        "default_unit": "kVA",
    },
    # Carbon
    {
        "section": "carbon_emissions",
        "key": "scope_1_direct_tco2e",
        "metric_type": "scope_1_emissions",
        "category": "carbon",
        "default_unit": "tCO2e",
    },
    {
        "section": "carbon_emissions",
        "key": "scope_2_indirect_tco2e",
        "metric_type": "scope_2_emissions",
        "category": "carbon",
        "default_unit": "tCO2e",
    },
    {
        "section": "carbon_emissions",
        "key": "total_ghg_emissions_tco2e",
        "metric_type": "total_ghg_emissions",
        "category": "carbon",
        "default_unit": "tCO2e",
    },
    # Water
    {
        "section": "water_and_waste",
        "key": "water_consumption_kl",
        "metric_type": "water_consumption",
        "category": "water",
        "default_unit": "kL",
    },
    {
        "section": "water_and_waste",
        "key": "recycled_water_kl",
        "metric_type": "recycled_water",
        "category": "water",
        "default_unit": "kL",
    },
    # Waste
    {
        "section": "water_and_waste",
        "key": "hazardous_waste_kg",
        "metric_type": "hazardous_waste",
        "category": "waste",
        "default_unit": "kg",
    },
    {
        "section": "water_and_waste",
        "key": "non_hazardous_waste_kg",
        "metric_type": "non_hazardous_waste",
        "category": "waste",
        "default_unit": "kg",
    },
    {
        "section": "water_and_waste",
        "key": "waste_recycled_percentage",
        "metric_type": "recycled_waste",
        "category": "waste",
        "default_unit": "%",
    },
    # Financial
    {
        "section": "energy",
        "key": "total_energy_cost_inr",
        "metric_type": "energy_cost",
        "category": "financial",
        "default_unit": "INR",
    },
]

class NormalizationService:
    """
    Standardizes structured document extractions into normalized, format-independent
    SustainabilityMetric records. Handles human verification overrides, evidence linkage,
    and unit verification.
    """

    def normalize_extraction(self, db: Session, document: Document) -> List[SustainabilityMetric]:
        """
        Convert structured extraction of a document into standardized SustainabilityMetric records.
        Applies any human field corrections and records verification status.
        Never calculates or invents missing data.
        """
        if not document.structured_data:
            logger.warning(f"Document {document.id} has no structured data to normalize.")
            return []

        data = document.structured_data
        corrections = document.field_corrections or {}
        evidence_list = data.get("evidence", [])
        evidence_map = {e["field"]: e for e in evidence_list if isinstance(e, dict) and "field" in e}

        company_name = (
            data.get("company", {}).get("name") 
            or document.company_name 
            or document.original_filename
        )

        period = data.get("period", {})
        period_start = period.get("start_date") or period.get("billing_month") or document.reporting_period
        period_end = period.get("end_date") or period.get("billing_month") or document.reporting_period

        # Clean existing normalized metrics for this document to prevent duplicates
        db.query(SustainabilityMetric).filter(SustainabilityMetric.document_id == document.id).delete()

        created_metrics: List[SustainabilityMetric] = []

        for mapping in METRIC_MAPPINGS:
            sec_name = mapping["section"]
            key = mapping["key"]
            source_field_name = f"{sec_name}.{key}"
            
            # Extract raw AI value
            raw_val = data.get(sec_name, {}).get(key)
            
            # Check for human correction
            # Correction key might be "electricity_kwh" or "energy.electricity_kwh"
            correction = corrections.get(key) or corrections.get(source_field_name)
            
            is_human_verified = False
            effective_val = raw_val
            unit = mapping["default_unit"]

            if correction and isinstance(correction, dict):
                corr_val = correction.get("corrected_value")
                if corr_val is not None and str(corr_val).strip() != "":
                    effective_val = corr_val
                    is_human_verified = True
                if correction.get("unit"):
                    unit = correction.get("unit")
            
            # Also check if marked verified in evidence map
            ev = evidence_map.get(key) or evidence_map.get(source_field_name)
            if ev and ev.get("is_verified"):
                is_human_verified = True
            if ev and ev.get("unit") and not (correction and correction.get("unit")):
                unit = ev.get("unit")

            # Document-wide verification status
            if document.review_status == "VERIFIED":
                is_human_verified = True

            # If the value is strictly null / None / non-numeric string, NEVER invent or store it!
            if effective_val is None or effective_val == "" or effective_val == "—":
                continue

            try:
                numeric_val = float(effective_val)
            except (ValueError, TypeError):
                logger.warning(f"Skipping non-numeric value for {source_field_name}: {effective_val}")
                continue

            # Traceability & evidence
            source_text = ev.get("source_text") if ev else None
            confidence = ev.get("confidence") if ev else (0.95 if document.extraction_method == "pymupdf" else 0.75)
            verification_status = "HUMAN_VERIFIED" if is_human_verified else "AI_EXTRACTED"

            metric_record = SustainabilityMetric(
                document_id=document.id,
                company_name=company_name,
                metric_type=mapping["metric_type"],
                category=mapping["category"],
                value=numeric_val,
                unit=unit,
                period_start=str(period_start) if period_start else None,
                period_end=str(period_end) if period_end else None,
                source_field=source_field_name,
                source_text=source_text,
                confidence=confidence,
                verification_status=verification_status,
            )

            db.add(metric_record)
            created_metrics.append(metric_record)

        try:
            db.commit()
            for m in created_metrics:
                db.refresh(m)
        except Exception as norm_commit_err:
            db.rollback()
            logger.exception(f"Failed to commit normalized metrics for Document ID {document.id}: {norm_commit_err}")
            raise

        logger.info(f"Normalized {len(created_metrics)} metrics for Document ID {document.id} ({company_name})")
        return created_metrics
