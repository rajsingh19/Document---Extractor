import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.models.document import Document
from backend.app.models.sustainability_metric import SustainabilityMetric
from backend.app.services.insights_service import insights_service
from backend.app.schemas.copilot import RecommendationItem

logger = logging.getLogger("senseible-copilot-recommendations")

class CopilotRecommendationService:
    """
    Senseible AI Copilot Actionable Recommendations Service (Step 11E).
    Deterministically identifies, ranks, and structures operational sustainability focus areas
    from normalized metrics, historical trends, and data quality signals.
    """

    def generate_recommendations(self, db: Session, query: Optional[str] = None, document_id: Optional[int] = None) -> List[RecommendationItem]:
        """
        Produce ranked, grounded recommendation items with transparent assumptions and exact source lineage.
        """
        recommendations: List[RecommendationItem] = []
        seen_keys = set()

        metrics_q = db.query(SustainabilityMetric)
        docs_q = db.query(Document)
        if document_id is not None:
            metrics_q = metrics_q.filter(SustainabilityMetric.document_id == document_id)
            docs_q = docs_q.filter(Document.id == document_id)

        metrics = metrics_q.order_by(desc(SustainabilityMetric.created_at)).all()
        docs = docs_q.order_by(desc(Document.created_at)).all()
        insights = insights_service.generate_metric_insights(db)
        if document_id is not None:
            insights = [i for i in insights if i.source_document_id == document_id]

        # 1. EMISSIONS Opportunities (Scope 1, Scope 2, Largest Contributor)
        scope1_m = next((m for m in metrics if m.metric_type in ("scope_1_emissions", "scope1_emissions")), None)
        scope2_m = next((m for m in metrics if m.metric_type in ("scope_2_emissions", "scope2_emissions")), None)

        if scope1_m or scope2_m:

            s1_val = scope1_m.value if scope1_m else 0.0
            s2_val = scope2_m.value if scope2_m else 0.0
            
            if s2_val > s1_val and s2_val > 0:
                item_id = "rec-emissions-scope2-dominant"
                if item_id not in seen_keys:
                    seen_keys.add(item_id)
                    recommendations.append(RecommendationItem(
                        id=item_id,
                        category="EMISSIONS",
                        priority="HIGH",
                        title="Focus on Scope 2 Electricity-Related Emissions",
                        reason=f"Scope 2 emissions ({s2_val:.2f} tCO2e) represent the largest documented emissions contributor in your records.",
                        metric_type="scope_2_emissions",
                        current_value=s2_val,
                        unit="tCO2e",
                        source_document_id=scope2_m.document_id if scope2_m else None,
                        evidence=scope2_m.source_text if scope2_m else "Verified Scope 2 carbon metric",
                        suggested_actions=[
                            "Review high-consumption billing periods and peak-demand patterns.",
                            "Evaluate renewable electricity procurement or rooftop solar options.",
                            "Inspect major motor and compressor load efficiencies."
                        ],
                        limitations="Based on recorded Scope 1 and Scope 2 figures; does not predict exact capital costs or guaranteed reductions."
                    ))
            elif s1_val > s2_val and s1_val > 0:
                item_id = "rec-emissions-scope1-dominant"
                if item_id not in seen_keys:
                    seen_keys.add(item_id)
                    recommendations.append(RecommendationItem(
                        id=item_id,
                        category="EMISSIONS",
                        priority="HIGH",
                        title="Focus on Scope 1 Fuel and Direct Emissions",
                        reason=f"Scope 1 direct emissions ({s1_val:.2f} tCO2e) represent the largest documented emissions contributor in your records.",
                        metric_type="scope_1_emissions",
                        current_value=s1_val,
                        unit="tCO2e",
                        source_document_id=scope1_m.document_id if scope1_m else None,
                        evidence=scope1_m.source_text if scope1_m else "Verified Scope 1 carbon metric",
                        suggested_actions=[
                            "Inspect backup generator running logs against grid outage schedules.",
                            "Review boiler or burner fuel-to-air combustion tuning.",
                            "Evaluate electrification or cleaner alternative fuel opportunities."
                        ],
                        limitations="Operational guidance based on fuel/direct emissions data; does not predict exact capital costs."
                    ))

        # 2. ENERGY Opportunities (Electricity Consumption increases & trends)
        for ins in insights:
            if ins.metric_type == "electricity_consumption" or ins.category in ("energy", "INCREASE"):
                pct = ins.percentage_change
                if ins.category == "TREND" or (pct is not None and pct > 0):
                    item_id = f"rec-energy-{ins.period}"
                    if item_id not in seen_keys:
                        seen_keys.add(item_id)
                        p_val = "HIGH" if (pct and pct >= 10.0) or ins.category == "TREND" else "MEDIUM"
                        pct_text = f" ({pct:+.1f}%)" if pct is not None else ""
                        
                        recommendations.append(RecommendationItem(
                            id=item_id,
                            category="ENERGY",
                            priority=p_val,
                            title="Optimize High-Consumption Electricity Windows",
                            reason=f"Electricity consumption increased{pct_text} compared with the previous available reporting period.",
                            metric_type="electricity_consumption",
                            current_value=ins.current_value,
                            previous_value=ins.previous_value,
                            unit=ins.unit or "kWh",
                            percentage_change=ins.percentage_change,
                            source_document_id=ins.source_document_id,
                            evidence="Directly extracted from utility billing records",
                            suggested_actions=[
                                "Review peak-demand time intervals to minimize maximum demand tariff penalties.",
                                "Inspect operating schedules of heavy electrical loads (pumps, HVAC, induction furnaces).",
                                "Evaluate renewable energy integration or power factor correction."
                            ],
                            limitations="Operational guidance based on billing data; requires on-site electrical audit for equipment-level breakdown."
                        ))

        # 3. FUEL Opportunities (Diesel / Generator fuel shifts)
        fuel_m = next((m for m in metrics if m.metric_type in ("fuel_consumption", "diesel_liters")), None)
        fuel_ins = next((i for i in insights if i.metric_type == "fuel_consumption" and (i.percentage_change or 0) > 0), None)
        if fuel_ins or fuel_m:
            item_id = "rec-fuel-optimization"
            if item_id not in seen_keys:
                seen_keys.add(item_id)
                pct_val = fuel_ins.percentage_change if fuel_ins else None
                cur_v = fuel_ins.current_value if fuel_ins else fuel_m.value
                prev_v = fuel_ins.previous_value if fuel_ins else None
                
                recommendations.append(RecommendationItem(
                    id=item_id,
                    category="FUEL",
                    priority="HIGH" if (pct_val and pct_val >= 10.0) else "MEDIUM",
                    title="Review Auxiliary Generator and Fuel Usage",
                    reason=f"Recorded fuel consumption is {cur_v} Liters" + (f" with a {pct_val:+.1f}% shift." if pct_val else "."),
                    metric_type="fuel_consumption",
                    current_value=cur_v,
                    previous_value=prev_v,
                    unit="Liters",
                    percentage_change=pct_val,
                    source_document_id=fuel_m.document_id if fuel_m else None,
                    evidence=fuel_m.source_text if fuel_m else "Extracted fuel receipt",
                    suggested_actions=[
                        "Inspect backup generator running logs against grid outage schedules.",
                        "Review boiler or burner fuel-to-air combustion tuning.",
                        "Track fuel consumption per unit of production to identify operational variances."
                    ],
                    limitations="Reflects recorded purchase volumes; operating equipment hours must be verified on-site."
                ))

        # 4. WATER Opportunities
        water_m = next((m for m in metrics if m.metric_type == "water_consumption"), None)
        water_ins = next((i for i in insights if i.metric_type == "water_consumption" and (i.percentage_change or 0) > 0), None)
        if water_ins or (water_m and water_m.value > 0):
            item_id = "rec-water-conservation"
            if item_id not in seen_keys:
                seen_keys.add(item_id)
                recommendations.append(RecommendationItem(
                    id=item_id,
                    category="WATER",
                    priority="MEDIUM",
                    title="Evaluate Process Water Usage & Recycling Opportunities",
                    reason=f"Water consumption is currently recorded at {water_m.value if water_m else water_ins.current_value} kL.",
                    metric_type="water_consumption",
                    current_value=water_m.value if water_m else water_ins.current_value,
                    unit="kL",
                    source_document_id=water_m.document_id if water_m else None,
                    evidence=water_m.source_text if water_m else "Utility water bill record",
                    suggested_actions=[
                        "Inspect water metering across primary production vs utility/cooling loops.",
                        "Review water-loss and leakage indicators across storage and distribution lines.",
                        "Investigate wastewater recycling and closed-loop cooling possibilities."
                    ],
                    limitations="Provides aggregate site water metrics; does not establish specific sub-process water intensity."
                ))

        # 5. WASTE Opportunities
        waste_m = next((m for m in metrics if "waste" in m.metric_type), None)
        if waste_m and waste_m.value > 0:
            item_id = "rec-waste-circularity"
            if item_id not in seen_keys:
                seen_keys.add(item_id)
                recommendations.append(RecommendationItem(
                    id=item_id,
                    category="WASTE",
                    priority="MEDIUM",
                    title="Strengthen Waste Segregation and Material Recovery",
                    reason=f"Documented waste generation is {waste_m.value} {waste_m.unit}.",
                    metric_type=waste_m.metric_type,
                    current_value=waste_m.value,
                    unit=waste_m.unit,
                    source_document_id=waste_m.document_id,
                    evidence=waste_m.source_text or "Waste manifest record",
                    suggested_actions=[
                        "Review waste stream segregation at source between recyclable and hazardous fractions.",
                        "Identify scrap minimization opportunities in primary cutting and molding operations.",
                        "Engage certified recyclers to explore byproduct co-processing."
                    ],
                    limitations="Based on manifested disposal weights; raw material yield metrics require production linkage."
                ))

        # 6. DATA_QUALITY Opportunities
        review_docs = [d for d in docs if d.review_status == "NEEDS_REVIEW"]
        if review_docs:
            item_id = "rec-data-quality-verification"
            if item_id not in seen_keys:
                seen_keys.add(item_id)
                recommendations.append(RecommendationItem(
                    id=item_id,
                    category="DATA_QUALITY",
                    priority="HIGH",
                    title="Complete Human Review for Flagged Documents",
                    reason=f"{len(review_docs)} uploaded document(s) have extraction warnings or missing expected fields.",
                    source_document_id=review_docs[0].id,
                    suggested_actions=[
                        "Review and verify unconfirmed fields in flagged documents.",
                        "Confirm billing periods and utility meter numbers for accurate historical tracking.",
                        "Upload missing monthly bills to eliminate reporting timeline gaps."
                    ],
                    limitations="Improves data confidence; is a data-governance prerequisite rather than direct operational reduction."
                ))

        # Prioritize deterministically: HIGH -> MEDIUM -> LOW
        # If query specifically asks about emissions, ensure EMISSIONS recommendations are prioritized
        q_clean = (query or "").lower()
        is_emissions_query = any(k in q_clean for k in ["emission", "carbon", "ghg", "footprint", "scope 1", "scope 2", "scope1", "scope2"])
        
        priority_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        def sort_key(r):
            cat_bonus = 1 if (is_emissions_query and r.category in ("EMISSIONS", "ENERGY")) else 0
            return (-priority_order.get(r.priority, 0), -cat_bonus)

        sorted_recs = sorted(recommendations, key=sort_key)

        return sorted_recs

copilot_recommendation_service = CopilotRecommendationService()
