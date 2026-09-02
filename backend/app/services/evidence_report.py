"""
services/evidence_report.py — Grounded Evidence Report Service (Step 11F).

Architecture:
  SQL (SustainabilityMetric)   → numerical truth
  SQL (Document)               → provenance / metadata truth
  InsightsService              → deterministic interpretation
  CopilotRecommendationService → deterministic recommendations
  CopilotAttentionService      → data-quality / attention signals
  EvidenceReportService        → assembles ReportData
  ReportData                   → single canonical object
  API route                    → returns ReportData as JSON
  PDF renderer                 → renders ReportData as PDF (same object)

SAFETY RULES enforced by this service:
- Every ReportMetric.document_id == requested document_id (verified)
- Every ReportEvidence.document_id == requested document_id (verified)
- Missing data is represented as ReportMissingField, never as zero
- NOT_APPLICABLE fields are never shown as missing
- No LLM is invoked during report generation
- Source texts are verbatim from DB or "Source text unavailable."
- Emissions are only shown when present in DB; missing → emissions_available=False
"""
import hashlib
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Set

from sqlalchemy.orm import Session

from backend.app.models.document import Document
from backend.app.models.sustainability_metric import SustainabilityMetric
from backend.app.services.insights_service import insights_service, format_metric_label
from backend.app.services.copilot_recommendations import CopilotRecommendationService
from backend.app.services.copilot_attention import CopilotAttentionService
from backend.app.schemas.report import (
    ReportData,
    ReportMetadata,
    ReportMetric,
    ReportEvidence,
    ReportEmissions,
    ReportInsight,
    ReportRecommendation,
    ReportMissingField,
    ReportDataQuality,
)

logger = logging.getLogger("senseible-evidence-report")

# All metric types that the system tracks. Used to determine "missing" fields.
TRACKED_METRIC_TYPES: Dict[str, str] = {
    "electricity_consumption": "Electricity Consumption",
    "grid_electricity":         "Grid Electricity Purchased",
    "renewable_energy":         "Renewable Energy (Solar/Wind)",
    "peak_demand":              "Peak Demand",
    "power_factor":             "Power Factor",
    "fuel_consumption":         "Diesel / Fuel Consumption",
    "natural_gas":              "Natural Gas Consumption",
    "water_consumption":        "Water Consumption",
    "recycled_water":           "Recycled Water",
    "hazardous_waste":          "Hazardous Waste",
    "non_hazardous_waste":      "Non-Hazardous Waste",
    "scope_1_emissions":        "Scope 1 Emissions",
    "scope_2_emissions":        "Scope 2 Emissions",
    "total_ghg_emissions":      "Total GHG Emissions",
    "energy_cost":              "Energy / Invoice Cost",
}

# Fields that are electricity-bill-specific (not applicable to all doc types)
ELECTRICITY_BILL_METRICS: Set[str] = {
    "electricity_consumption", "grid_electricity", "renewable_energy",
    "peak_demand", "power_factor", "energy_cost",
}

CARBON_METRIC_TYPES: Set[str] = {
    "scope_1_emissions", "scope_2_emissions", "total_ghg_emissions"
}

_recommendation_service = CopilotRecommendationService()
_attention_service = CopilotAttentionService()


class EvidenceReportService:
    """
    Builds a fully grounded ReportData for a single document.
    Read-only: never writes to the database.
    """

    def generate_report(self, db: Session, document_id: int) -> ReportData:
        """
        Build a ReportData from the database for the given document_id.
        Raises ValueError if the document does not exist.
        """
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc is None:
            raise ValueError(f"Document {document_id} not found")

        # Retrieve only metrics belonging to this document
        raw_metrics = (
            db.query(SustainabilityMetric)
            .filter(SustainabilityMetric.document_id == document_id)
            .order_by(SustainabilityMetric.id.asc())
            .all()
        )

        # Safety: verify document scoping
        for m in raw_metrics:
            assert m.document_id == document_id, (
                f"Metric {m.id} belongs to doc {m.document_id}, not {document_id}"
            )

        generated_at = datetime.now(timezone.utc).isoformat()
        report_id = hashlib.sha256(
            f"{document_id}:{generated_at}".encode()
        ).hexdigest()[:16]

        metadata = self._build_metadata(doc, report_id, generated_at)
        report_metrics = self._build_metrics(raw_metrics, doc)
        emissions = self._build_emissions(raw_metrics)
        evidence = self._build_evidence(raw_metrics, doc)
        insights = self._build_insights(db, document_id)
        recommendations = self._build_recommendations(db, document_id)
        missing_data = self._build_missing_data(raw_metrics, doc)
        data_quality = self._build_data_quality(doc, raw_metrics)
        executive_summary = self._build_executive_summary(
            doc, report_metrics, emissions
        )
        attention_flags = self._build_attention_flags(doc, raw_metrics)

        return ReportData(
            metadata=metadata,
            metrics=report_metrics,
            emissions=emissions,
            evidence=evidence,
            insights=insights,
            recommendations=recommendations,
            missing_data=missing_data,
            data_quality=data_quality,
            executive_summary=executive_summary,
            attention_flags=attention_flags,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Internal builders
    # ──────────────────────────────────────────────────────────────────────────

    def _build_metadata(
        self, doc: Document, report_id: str, generated_at: str
    ) -> ReportMetadata:
        return ReportMetadata(
            report_id=report_id,
            document_id=doc.id,
            document_name=doc.original_filename or doc.filename,
            company_name=doc.company_name or None,
            document_type=doc.document_type or None,
            reporting_period=doc.reporting_period or None,
            generated_at=generated_at,
            verification_status=doc.review_status or None,
            quality_score=float(doc.quality_score or 0.0),
            review_status=doc.review_status or None,
            extraction_method=doc.extraction_method or None,
            page_count=doc.page_count or None,
        )

    def _build_metrics(
        self, raw_metrics: list, doc: Document
    ) -> List[ReportMetric]:
        """
        Build ReportMetric list. Deduplicates by metric_type, taking the most
        recently inserted row per type. Preserves exact SQL values.
        """
        # Dedup: last-wins per metric_type (highest id = most recent)
        seen: Dict[str, SustainabilityMetric] = {}
        for m in raw_metrics:
            if m.metric_type not in seen or m.id > seen[m.metric_type].id:
                seen[m.metric_type] = m

        result: List[ReportMetric] = []
        for metric_type, m in seen.items():
            result.append(ReportMetric(
                metric_name=format_metric_label(m.metric_type),
                metric_type=m.metric_type,
                category=m.category,
                value=m.value,
                unit=m.unit,
                reporting_period=doc.reporting_period or m.period_end or m.period_start,
                period_start=m.period_start,
                period_end=m.period_end,
                verification_status=m.verification_status,
                confidence=m.confidence,
                document_id=m.document_id,
                document_name=doc.original_filename or doc.filename,
                source_field=m.source_field,
                source_text=m.source_text or None,
            ))

        # Sort: energy first, carbon second, financial last
        category_order = {"energy": 0, "carbon": 1, "water": 2, "waste": 3, "financial": 4}
        result.sort(key=lambda r: (category_order.get(r.category, 9), r.metric_name))
        return result

    def _build_emissions(self, raw_metrics: list) -> ReportEmissions:
        """Build emissions summary from carbon-category metrics only."""
        carbon = {m.metric_type: m for m in raw_metrics if m.metric_type in CARBON_METRIC_TYPES}

        s1 = carbon.get("scope_1_emissions")
        s2 = carbon.get("scope_2_emissions")
        total = carbon.get("total_ghg_emissions")

        if not s1 and not s2 and not total:
            return ReportEmissions(emissions_available=False)

        dominant = None
        if s1 and s2:
            dominant = "scope_1" if s1.value > s2.value else "scope_2"

        return ReportEmissions(
            scope_1=s1.value if s1 else None,
            scope_1_unit=s1.unit if s1 else "tCO2e",
            scope_1_source=s1.source_text or None if s1 else None,
            scope_2=s2.value if s2 else None,
            scope_2_unit=s2.unit if s2 else "tCO2e",
            scope_2_source=s2.source_text or None if s2 else None,
            total_ghg=total.value if total else None,
            total_ghg_unit=total.unit if total else "tCO2e",
            total_ghg_source=total.source_text or None if total else None,
            dominant_scope=dominant,
            emissions_available=True,
        )

    def _build_evidence(
        self, raw_metrics: list, doc: Document
    ) -> List[ReportEvidence]:
        """Build evidence rows from metric source lineage. Verbatim source_text only."""
        seen_keys: Set[str] = set()
        result: List[ReportEvidence] = []

        for m in raw_metrics:
            key = f"{m.document_id}:{m.source_field}:{m.metric_type}"
            if key in seen_keys:
                continue
            seen_keys.add(key)

            result.append(ReportEvidence(
                evidence_id=key,
                document_id=m.document_id,
                document_name=doc.original_filename or doc.filename,
                field=m.source_field,
                metric_name=format_metric_label(m.metric_type),
                value=m.value,
                unit=m.unit,
                source_text=m.source_text if m.source_text else "Source text unavailable.",
                page=1 if (doc.page_count and doc.page_count >= 1) else None,
                verification_status=m.verification_status,
            ))

        return result

    def _build_insights(self, db: Session, document_id: int) -> List[ReportInsight]:
        """Retrieve deterministic insights from InsightsService, filtered to this document."""
        all_insights = insights_service.generate_metric_insights(db)
        doc_insights = [i for i in all_insights if i.source_document_id == document_id]

        result: List[ReportInsight] = []
        for ins in doc_insights:
            # Derive a title from category + metric_type
            cat = (ins.category or "").replace("_", " ").title()
            m_label = format_metric_label(ins.metric_type) if ins.metric_type else ""
            title = f"{cat}: {m_label}" if m_label else cat

            result.append(ReportInsight(
                category=ins.category,
                severity=ins.severity,
                metric_type=ins.metric_type,
                metric=ins.metric_type,
                title=title,
                message=ins.message,
                explanation=ins.message,
                current_value=ins.current_value,
                previous_value=ins.previous_value,
                unit=ins.unit,
                reporting_period=ins.period,
                source_document_id=ins.source_document_id,
            ))

        return result

    def _build_recommendations(
        self, db: Session, document_id: int
    ) -> List[ReportRecommendation]:
        """Retrieve deterministic recommendations from CopilotRecommendationService."""
        recs = _recommendation_service.generate_recommendations(
            db, document_id=document_id
        )
        result: List[ReportRecommendation] = []
        for r in recs:
            result.append(ReportRecommendation(
                id=r.id,
                category=r.category,
                priority=r.priority,
                title=r.title,
                reason=r.reason,
                metric_type=r.metric_type,
                current_value=r.current_value,
                unit=r.unit,
                suggested_actions=list(r.suggested_actions),
                limitations=r.limitations,
                source_document_id=r.source_document_id,
            ))
        return result

    def _build_missing_data(
        self, raw_metrics: list, doc: Document
    ) -> List[ReportMissingField]:
        """
        Determine which tracked metric types are absent from this document.
        Only flags as "missing" types that are expected for this document type.
        NOT_APPLICABLE types (e.g. water in an electricity bill) are marked accordingly.
        Never treats zero or empty as "missing" — only truly absent metrics.
        """
        present_types: Set[str] = {m.metric_type for m in raw_metrics}
        doc_type = (doc.document_type or "").lower()

        # Determine which metrics are expected for this document type
        is_electricity = any(k in doc_type for k in ["electricity", "energy", "power", "bill"])
        is_esg = any(k in doc_type for k in ["esg", "audit", "sustainability", "report"])
        is_water = "water" in doc_type
        is_waste = "waste" in doc_type

        result: List[ReportMissingField] = []

        for metric_type, display_name in TRACKED_METRIC_TYPES.items():
            if metric_type in present_types:
                continue  # present — not missing

            if metric_type in CARBON_METRIC_TYPES:
                # Carbon metrics: expected for electricity bills and ESG reports
                if not (is_electricity or is_esg):
                    continue  # not applicable for this doc type

            if metric_type in ("water_consumption", "recycled_water"):
                if not (is_water or is_esg):
                    result.append(ReportMissingField(
                        field_name=metric_type,
                        display_name=display_name,
                        reason="Not reported in this document",
                        is_not_applicable=True,
                    ))
                    continue

            if metric_type in ("hazardous_waste", "non_hazardous_waste"):
                if not (is_waste or is_esg):
                    result.append(ReportMissingField(
                        field_name=metric_type,
                        display_name=display_name,
                        reason="Not reported in this document",
                        is_not_applicable=True,
                    ))
                    continue

            if metric_type == "natural_gas":
                # Natural gas is optional in all document types
                result.append(ReportMissingField(
                    field_name=metric_type,
                    display_name=display_name,
                    reason="Not reported in this document",
                    is_not_applicable=False,
                ))
                continue

            if metric_type in ELECTRICITY_BILL_METRICS and not is_electricity:
                continue  # Not expected

            # Genuinely missing for this document type
            result.append(ReportMissingField(
                field_name=metric_type,
                display_name=display_name,
                reason="Not reported in this document",
                is_not_applicable=False,
            ))

        return result

    def _build_data_quality(
        self, doc: Document, raw_metrics: list
    ) -> ReportDataQuality:
        """Read data quality information from the Document model."""
        q_summary = doc.quality_summary or {}
        review_reasons = q_summary.get("review_reasons") or []
        low_conf = q_summary.get("low_confidence_fields") or []

        verified_count = sum(
            1 for m in raw_metrics if m.verification_status == "HUMAN_VERIFIED"
        )
        ai_count = sum(
            1 for m in raw_metrics if m.verification_status == "AI_EXTRACTED"
        )

        return ReportDataQuality(
            verification_status=doc.review_status,
            review_status=doc.review_status,
            quality_score=float(doc.quality_score or 0.0),
            extraction_method=doc.extraction_method,
            confidence_score=float(doc.confidence_score or 0.0),
            needs_review=(doc.review_status == "NEEDS_REVIEW"),
            review_reasons=list(review_reasons),
            low_confidence_fields=list(low_conf),
            metric_count=len(raw_metrics),
            verified_metric_count=verified_count,
            ai_extracted_metric_count=ai_count,
        )

    def _build_executive_summary(
        self,
        doc: Document,
        metrics: List[ReportMetric],
        emissions: ReportEmissions,
    ) -> str:
        """
        Build a deterministic executive summary from structured data.
        No LLM. Each sentence is constructed from exact DB values.
        """
        lines: List[str] = []

        company = doc.company_name or "The company"
        period = doc.reporting_period or "the reported period"
        doc_type = doc.document_type or "document"

        lines.append(
            f"This report presents the sustainability data extracted from the "
            f"{doc_type} for {company} covering {period}."
        )

        # Energy summary
        elec = next((m for m in metrics if m.metric_type == "electricity_consumption"), None)
        if elec:
            lines.append(
                f"Total electricity consumption recorded is "
                f"{elec.value:,.0f} {elec.unit}."
            )

        # Emissions summary
        if emissions.emissions_available:
            parts = []
            if emissions.scope_1 is not None:
                parts.append(f"Scope 1: {emissions.scope_1:.2f} {emissions.scope_1_unit}")
            if emissions.scope_2 is not None:
                parts.append(f"Scope 2: {emissions.scope_2:.2f} {emissions.scope_2_unit}")
            if emissions.total_ghg is not None:
                parts.append(f"Total: {emissions.total_ghg:.2f} {emissions.total_ghg_unit}")
            if parts:
                lines.append("Greenhouse gas emissions — " + ", ".join(parts) + ".")
            if emissions.dominant_scope == "scope_2":
                lines.append(
                    "Scope 2 (grid electricity) is the larger documented emissions category."
                )
            elif emissions.dominant_scope == "scope_1":
                lines.append(
                    "Scope 1 (direct fuel combustion) is the larger documented emissions category."
                )
        else:
            lines.append("Emissions data was not available in this document.")

        # Quality
        qs = float(doc.quality_score or 0.0)
        vs = doc.review_status or "UNKNOWN"
        lines.append(
            f"Extraction quality score: {qs:.0f}/100. Verification status: {vs}."
        )

        return " ".join(lines)

    def _build_attention_flags(
        self, doc: Document, raw_metrics: list
    ) -> List[str]:
        """Generate human-readable attention flags from document state."""
        flags: List[str] = []
        if doc.review_status == "NEEDS_REVIEW":
            flags.append("Document requires human review before final reporting.")
        if float(doc.quality_score or 0) < 70:
            flags.append(
                f"Extraction quality score ({doc.quality_score:.0f}/100) is below 70. "
                "Consider reprocessing or manual verification."
            )
        low_conf_metrics = [
            m for m in raw_metrics
            if m.confidence is not None and m.confidence < 0.70
        ]
        if low_conf_metrics:
            names = ", ".join(
                format_metric_label(m.metric_type) for m in low_conf_metrics[:3]
            )
            flags.append(
                f"Low confidence extraction on: {names}. Human verification recommended."
            )
        return flags


evidence_report_service = EvidenceReportService()
