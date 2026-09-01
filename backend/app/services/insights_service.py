import re
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.models.document import Document
from backend.app.models.sustainability_metric import SustainabilityMetric
from backend.app.schemas.insight import MetricInsight
from backend.app.utils.helpers import parse_period_key

logger = logging.getLogger("senseible-document-ai")

THRESHOLD_METRIC_TYPES = {
    "electricity_consumption",
    "water_consumption",
    "fuel_consumption",
    "hazardous_waste",
    "non_hazardous_waste",
    "scope_1_emissions",
    "scope_2_emissions",
    "total_ghg_emissions",
}

def format_metric_label(key: Optional[str]) -> str:
    """Format metric_type key into clean human-readable title."""
    if not key:
        return "Metric"
    name_map = {
        "electricity_consumption": "Electricity consumption",
        "renewable_energy": "Renewable energy",
        "fuel_consumption": "Fuel consumption",
        "peak_demand": "Peak demand",
        "scope_1_emissions": "Scope 1 emissions",
        "scope_2_emissions": "Scope 2 emissions",
        "total_ghg_emissions": "Total GHG emissions",
        "water_consumption": "Water consumption",
        "recycled_water": "Recycled water",
        "hazardous_waste": "Hazardous waste",
        "non_hazardous_waste": "Non-hazardous waste",
        "recycled_waste": "Waste recycled",
        "energy_cost": "Energy cost",
    }
    if key in name_map:
        return name_map[key]
    return key.replace("_", " ").capitalize()

def are_consecutive_months(p1_key: str, p2_key: str) -> bool:
    """
    Check if two period keys formatted as 'YYYY-MM' represent consecutive calendar months.
    """
    m1 = re.match(r'^(\d{4})-(\d{2})$', str(p1_key).strip())
    m2 = re.match(r'^(\d{4})-(\d{2})$', str(p2_key).strip())
    if not m1 or not m2:
        return False
    
    y1, mo1 = int(m1.group(1)), int(m1.group(2))
    y2, mo2 = int(m2.group(1)), int(m2.group(2))
    
    return (y2 * 12 + mo2) - (y1 * 12 + mo1) == 1

def format_percentage(val: float) -> str:
    """Format percentage value cleanly."""
    if abs(val - round(val)) < 0.001:
        return f"{int(round(val))}%"
    return f"{val:.1f}%"

class InsightsService:
    """
    Deterministic insights engine that inspects stored sustainability metrics and documents.
    Generates explainable, evidence-backed insights without LLMs.
    """

    def generate_metric_insights(
        self,
        db: Session,
        company: Optional[str] = None,
        severity: Optional[str] = None,
        metric_type: Optional[str] = None
    ) -> List[MetricInsight]:
        """
        Generate all deterministic insights across stored data, applying optional filters.
        """
        insights: List[MetricInsight] = []

        # Fetch metrics and documents
        metrics_query = db.query(SustainabilityMetric)
        docs_query = db.query(Document)

        all_metrics = metrics_query.all()
        all_docs = docs_query.all()

        # Group metrics by company and metric_type
        # Structure: company -> metric_type -> list of records
        company_metric_groups: Dict[str, Dict[str, List[SustainabilityMetric]]] = {}
        # Company -> all known period keys
        company_periods: Dict[str, set] = {}
        # Company -> period_key -> raw label mapping
        company_period_labels: Dict[str, Dict[str, str]] = {}

        for m in all_metrics:
            c_name = m.company_name or "Unknown Company"
            if c_name not in company_metric_groups:
                company_metric_groups[c_name] = {}
                company_periods[c_name] = set()
                company_period_labels[c_name] = {}

            if m.metric_type not in company_metric_groups[c_name]:
                company_metric_groups[c_name][m.metric_type] = []

            company_metric_groups[c_name][m.metric_type].append(m)

            p_raw = m.period_start or m.period_end or "Unknown"
            p_key = parse_period_key(p_raw)
            company_periods[c_name].add(p_key)
            if p_key not in company_period_labels[c_name] or len(str(p_raw)) > len(company_period_labels[c_name][p_key]):
                company_period_labels[c_name][p_key] = str(p_raw)

        # ---------------------------------------------------------
        # 1. PERIOD-OVER-PERIOD, NEW_DATA & TREND INSIGHTS
        # ---------------------------------------------------------
        for c_name, metric_dict in company_metric_groups.items():
            for m_type, records in metric_dict.items():
                # Sort records chronologically
                def get_sort_tuple(rec):
                    p = rec.period_start or rec.period_end or "9999-99"
                    return (parse_period_key(p), rec.created_at or rec.id or 0)

                sorted_records = sorted(records, key=get_sort_tuple)

                # Collapse records for the same period if duplicates exist (take latest)
                period_map: Dict[str, SustainabilityMetric] = {}
                for r in sorted_records:
                    p_key = parse_period_key(r.period_start or r.period_end)
                    period_map[p_key] = r

                unique_sorted_records = [period_map[k] for k in sorted(period_map.keys())]
                count = len(unique_sorted_records)

                # Check if single period exists -> NEW_DATA
                if count == 1:
                    latest = unique_sorted_records[0]
                    p_key = parse_period_key(latest.period_start or latest.period_end)
                    p_label = latest.period_start or latest.period_end or p_key
                    label_str = format_metric_label(m_type)
                    insights.append(MetricInsight(
                        metric_type=m_type,
                        category="NEW_DATA",
                        severity="INFO",
                        company_name=c_name,
                        period=p_key,
                        current_value=latest.value,
                        previous_value=None,
                        unit=latest.unit,
                        percentage_change=None,
                        message=f"{label_str} was reported for the first time in {p_label}.",
                        source_document_id=latest.document_id,
                        previous_source_document_id=None,
                        threshold_note=None,
                        quality_score=None
                    ))
                    continue

                # When >= 2 periods exist:
                curr = unique_sorted_records[-1]
                prev = unique_sorted_records[-2]

                curr_period_key = parse_period_key(curr.period_start or curr.period_end)
                prev_period_key = parse_period_key(prev.period_start or prev.period_end)
                curr_period_label = curr.period_start or curr.period_end or curr_period_key

                # Unit Safety Check: Do NOT compare incompatible units
                if curr.unit != prev.unit:
                    logger.warning(f"Incompatible units for {c_name} {m_type}: {curr.unit} vs {prev.unit}. Skipping PoP comparison.")
                else:
                    abs_change = round(curr.value - prev.value, 2)
                    label_str = format_metric_label(m_type)

                    if prev.value != 0:
                        pct_change = round(((curr.value - prev.value) / prev.value) * 100, 2)
                    else:
                        pct_change = None

                    if curr.value > prev.value:
                        # Category: INCREASE
                        is_attention = (
                            m_type in THRESHOLD_METRIC_TYPES
                            and pct_change is not None
                            and pct_change > 10.0
                        )
                        severity_val = "ATTENTION" if is_attention else "INFO"
                        threshold_note_val = "Internal monitoring threshold: increase greater than 10%." if is_attention else None
                        
                        if pct_change is not None:
                            pct_str = format_percentage(abs(pct_change))
                            msg = f"{label_str} increased by {pct_str} compared with the previous period."
                        else:
                            msg = f"{label_str} increased by {abs_change} {curr.unit} compared with the previous period."

                        insights.append(MetricInsight(
                            metric_type=m_type,
                            category="INCREASE",
                            severity=severity_val,
                            company_name=c_name,
                            period=curr_period_key,
                            current_value=curr.value,
                            previous_value=prev.value,
                            unit=curr.unit,
                            percentage_change=pct_change,
                            message=msg,
                            source_document_id=curr.document_id,
                            previous_source_document_id=prev.document_id,
                            threshold_note=threshold_note_val,
                            quality_score=None
                        ))

                    elif curr.value < prev.value:
                        # Category: DECREASE (strictly neutral language)
                        if pct_change is not None:
                            pct_str = format_percentage(abs(pct_change))
                            msg = f"{label_str} decreased by {pct_str} compared with the previous period."
                        else:
                            msg = f"{label_str} decreased by {abs(abs_change)} {curr.unit} compared with the previous period."

                        insights.append(MetricInsight(
                            metric_type=m_type,
                            category="DECREASE",
                            severity="INFO",
                            company_name=c_name,
                            period=curr_period_key,
                            current_value=curr.value,
                            previous_value=prev.value,
                            unit=curr.unit,
                            percentage_change=pct_change,
                            message=msg,
                            source_document_id=curr.document_id,
                            previous_source_document_id=prev.document_id,
                            threshold_note=None,
                            quality_score=None
                        ))

                # ---------------------------------------------------------
                # 3-PERIOD CONSECUTIVE TREND CHECK
                # ---------------------------------------------------------
                if count >= 3:
                    # Examine the latest three reporting periods
                    r1 = unique_sorted_records[-3]
                    r2 = unique_sorted_records[-2]
                    r3 = unique_sorted_records[-1]

                    p1_k = parse_period_key(r1.period_start or r1.period_end)
                    p2_k = parse_period_key(r2.period_start or r2.period_end)
                    p3_k = parse_period_key(r3.period_start or r3.period_end)

                    # Only valid if units match and calendar periods are strictly consecutive
                    if (r1.unit == r2.unit == r3.unit) and are_consecutive_months(p1_k, p2_k) and are_consecutive_months(p2_k, p3_k):
                        if r1.value < r2.value < r3.value:
                            label_str = format_metric_label(m_type)
                            insights.append(MetricInsight(
                                metric_type=m_type,
                                category="TREND",
                                severity="ATTENTION",
                                company_name=c_name,
                                period=p3_k,
                                current_value=r3.value,
                                previous_value=r2.value,
                                unit=r3.unit,
                                percentage_change=None,
                                message=f"{label_str} increased across three consecutive reporting periods.",
                                source_document_id=r3.document_id,
                                previous_source_document_id=r2.document_id,
                                threshold_note="Internal monitoring threshold: consistent upward trend over 3 consecutive periods.",
                                quality_score=None
                            ))

        # ---------------------------------------------------------
        # 2. MISSING DATA DETECTION (Conservative & History-Based)
        # ---------------------------------------------------------
        for c_name, p_set in company_periods.items():
            if not p_set:
                continue
            sorted_c_periods = sorted(list(p_set))
            if len(sorted_c_periods) < 2:
                # Need at least 2 periods for this company to determine historical expectations
                continue

            latest_p_key = sorted_c_periods[-1]
            latest_p_label = company_period_labels[c_name].get(latest_p_key, latest_p_key)

            # Find all metric types historically reported in prior periods for this same company
            prior_metric_types = set()
            for m_type, records in company_metric_groups[c_name].items():
                for r in records:
                    r_pkey = parse_period_key(r.period_start or r.period_end)
                    if r_pkey < latest_p_key:
                        prior_metric_types.add(m_type)

            # Check if any historically reported metric is missing in the latest period
            for m_type in prior_metric_types:
                records = company_metric_groups[c_name].get(m_type, [])
                present_in_latest = any(
                    parse_period_key(r.period_start or r.period_end) == latest_p_key
                    for r in records
                )
                if not present_in_latest:
                    label_str = format_metric_label(m_type)
                    insights.append(MetricInsight(
                        metric_type=m_type,
                        category="MISSING_DATA",
                        severity="INFO",
                        company_name=c_name,
                        period=latest_p_key,
                        current_value=None,
                        previous_value=None,
                        unit=None,
                        percentage_change=None,
                        message=f"{label_str} was not reported for {latest_p_label}.",
                        source_document_id=None,
                        previous_source_document_id=None,
                        threshold_note=None,
                        quality_score=None
                    ))

        # ---------------------------------------------------------
        # 3. DATA QUALITY & OCR REVIEW INSIGHTS
        # ---------------------------------------------------------
        for doc in all_docs:
            needs_rev = False
            reasons = []

            if doc.review_status == "NEEDS_REVIEW":
                needs_rev = True
                if doc.extraction_method == "ocr_fallback":
                    reasons.append("OCR extraction was used")
                if doc.quality_score is not None and doc.quality_score < 70:
                    reasons.append(f"quality score is {int(doc.quality_score)}/100")
                if not reasons:
                    reasons.append("human verification is pending")
            elif doc.extraction_method == "ocr_fallback" and doc.review_status != "VERIFIED":
                needs_rev = True
                reasons.append("OCR extraction was used")
                if doc.quality_score is not None and doc.quality_score < 70:
                    reasons.append(f"quality score is {int(doc.quality_score)}/100")
            elif doc.quality_score is not None and doc.quality_score < 70 and doc.review_status != "VERIFIED":
                needs_rev = True
                reasons.append(f"quality score is {int(doc.quality_score)}/100")

            if needs_rev:
                reason_text = " and ".join(reasons)
                doc_title = doc.original_filename or doc.document_type or f"Document #{doc.id}"
                msg = f"{doc_title} requires review because {reason_text}."

                insights.append(MetricInsight(
                    metric_type=None,
                    category="NEEDS_REVIEW",
                    severity="REVIEW",
                    company_name=doc.company_name,
                    period=doc.reporting_period,
                    current_value=None,
                    previous_value=None,
                    unit=None,
                    percentage_change=None,
                    message=msg,
                    source_document_id=doc.id,
                    previous_source_document_id=None,
                    threshold_note="Extraction confidence or OCR fallback requires human review.",
                    quality_score=doc.quality_score
                ))

        # ---------------------------------------------------------
        # 4. APPLY FILTERS
        # ---------------------------------------------------------
        filtered_insights: List[MetricInsight] = []

        for item in insights:
            if company:
                if not item.company_name or company.lower() not in item.company_name.lower():
                    continue
            if severity:
                if item.severity.upper() != severity.upper():
                    continue
            if metric_type:
                if item.metric_type != metric_type:
                    continue
            filtered_insights.append(item)

        return filtered_insights

insights_service = InsightsService()
