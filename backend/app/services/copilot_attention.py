import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from backend.app.models.document import Document
from backend.app.models.sustainability_metric import SustainabilityMetric
from backend.app.services.insights_service import insights_service
from backend.app.schemas.copilot import (
    AttentionItem,
    AttentionSummary,
    AttentionResponse,
)

logger = logging.getLogger("senseible-copilot-attention")

class CopilotAttentionService:
    """
    Senseible AI Copilot Proactive Attention Engine (Step 11D).
    Deterministically identifies, categorizes, deduplicates, and prioritizes operational
    issues and metric shifts across documents, metrics, and insights without LLM hallucinations.
    """

    def get_attention_items(self, db: Session) -> AttentionResponse:
        """
        Generate prioritized, deduplicated attention items and summary directly from database.
        """
        items: List[AttentionItem] = []
        seen_keys = set()

        docs = db.query(Document).order_by(desc(Document.created_at)).all()
        metrics = db.query(SustainabilityMetric).order_by(desc(SustainabilityMetric.created_at)).all()
        insights = insights_service.generate_metric_insights(db)

        # 1. Document Review Items (NEEDS_REVIEW, low confidence, OCR fallback, classification conflict)
        for doc in docs:
            if doc.review_status == "NEEDS_REVIEW":
                q_summary = doc.quality_summary or {}
                reasons = q_summary.get("review_reasons") or []
                missing_exp = q_summary.get("expected_missing_list") or []
                score = float(doc.quality_score or 0.0)

                # Determine specific type and underlying reason
                item_type = "DOCUMENT_REVIEW"
                severity = "HIGH"
                reason_str = reasons[0] if reasons else "Extraction requires verification"

                if any("classification" in r.lower() for r in reasons):
                    item_type = "CLASSIFICATION_CONFLICT"
                    reason_str = "Document type conflict detected during classification"
                elif any("evidence" in r.lower() or "validation" in r.lower() for r in reasons):
                    item_type = "EVIDENCE_ISSUE"
                    reason_str = "Extracted value could not be fully validated against source evidence"
                elif any("confidence" in r.lower() or "ocr" in r.lower() for r in reasons) or score < 70.0:
                    item_type = "LOW_CONFIDENCE"
                    reason_str = reasons[0] if reasons else "Extraction confidence or OCR fallback requires human review"
                elif missing_exp:
                    item_type = "DOCUMENT_REVIEW"
                    reason_str = f"Expected field(s) missing: {', '.join(missing_exp)}"

                doc_label = doc.document_type or "Document"
                fname = doc.original_filename or doc.filename
                period_str = f" — {doc.reporting_period}" if doc.reporting_period else ""
                item_id = f"doc-rev-{doc.id}"

                if item_id not in seen_keys:
                    seen_keys.add(item_id)
                    items.append(AttentionItem(
                        id=item_id,
                        type=item_type,
                        severity=severity,
                        title=f"{doc_label}{period_str} needs review",
                        message=f"{fname} is flagged for verification. Quality score: {int(score)}/100.",
                        reason=reason_str,
                        company_name=doc.company_name,
                        document_id=doc.id,
                        source_document_id=doc.id,
                        action_type="VIEW_DOCUMENT",
                        action_label="Review Document",
                        action_target=f"/documents/{doc.id}"
                    ))

        # 2. Missing Expected Data (Excluding NOT_APPLICABLE)
        for doc in docs:
            if doc.review_status != "NEEDS_REVIEW": # Avoid duplicate alert if already in high review
                q_summary = doc.quality_summary or {}
                missing_exp = q_summary.get("expected_missing_list") or []
                # Never treat NOT_APPLICABLE as missing
                na_list = q_summary.get("not_applicable_list") or []
                actual_missing = [f for f in missing_exp if f not in na_list]

                if actual_missing:
                    item_id = f"missing-{doc.id}"
                    if item_id not in seen_keys:
                        seen_keys.add(item_id)
                        doc_label = doc.document_type or "Document"
                        fname = doc.original_filename or doc.filename
                        items.append(AttentionItem(
                            id=item_id,
                            type="MISSING_DATA",
                            severity="MEDIUM",
                            title=f"Missing expected data in {doc_label}",
                            message=f"Expected field(s) `{', '.join(actual_missing)}` not reported in {fname}.",
                            reason=f"Expected sustainability parameter missing from {doc_label}",
                            company_name=doc.company_name,
                            document_id=doc.id,
                            source_document_id=doc.id,
                            action_type="VIEW_DOCUMENT",
                            action_label="Review Document",
                            action_target=f"/documents/{doc.id}"
                        ))

        # 3. Metric Change & Significant Insight Attention
        for ins in insights:
            # Significant increases, decreases, or anomalies
            if ins.category in ("INCREASE", "DECREASE", "TREND") or ins.severity in ("ACTION_REQUIRED", "REVIEW", "WARNING"):
                if ins.percentage_change is not None and abs(ins.percentage_change) >= 5.0 or ins.severity in ("ACTION_REQUIRED", "REVIEW"):
                    item_id = f"ins-{ins.metric_type}-{ins.period}-{ins.category}"
                    if item_id not in seen_keys:
                        seen_keys.add(item_id)
                        m_title = (ins.metric_type or "Metric").replace("_", " ").title()
                        direction = "increased" if (ins.percentage_change or 0) > 0 else "decreased" if (ins.percentage_change or 0) < 0 else "changed"
                        pct_str = f" {ins.percentage_change:+.1f}%" if ins.percentage_change is not None else ""
                        
                        sev = "HIGH" if ins.severity in ("ACTION_REQUIRED", "REVIEW") and abs(ins.percentage_change or 0) >= 20.0 else "MEDIUM"

                        items.append(AttentionItem(
                            id=item_id,
                            type="METRIC_CHANGE",
                            severity=sev,
                            title=f"{m_title} {direction}{pct_str}",
                            message=ins.message,
                            reason=ins.threshold_note or f"Significant period-over-period shift in {m_title}",
                            company_name=ins.company_name,
                            metric_type=ins.metric_type,
                            current_value=ins.current_value,
                            previous_value=ins.previous_value,
                            unit=ins.unit,
                            percentage_change=ins.percentage_change,
                            source_document_id=ins.source_document_id,
                            action_type="VIEW_METRIC",
                            action_label="View Metric",
                            action_target="/metrics"
                        ))

        # 4. Unverified Critical Data (AI_EXTRACTED metrics not already in document review)
        for m in metrics:
            if m.verification_status == "AI_EXTRACTED" and (m.confidence or 1.0) < 0.7:
                doc_key = f"doc-rev-{m.document_id}"
                if doc_key not in seen_keys:
                    item_id = f"unver-m-{m.id}"
                    if item_id not in seen_keys:
                        seen_keys.add(item_id)
                        m_title = m.metric_type.replace("_", " ").title()
                        items.append(AttentionItem(
                            id=item_id,
                            type="UNVERIFIED_DATA",
                            severity="LOW",
                            title=f"Unverified {m_title} data",
                            message=f"Human verification recommended for {m_title} ({m.value} {m.unit}).",
                            reason=f"Low confidence ({int((m.confidence or 0)*100)}%) AI extraction",
                            company_name=m.company_name,
                            document_id=m.document_id,
                            metric_type=m.metric_type,
                            current_value=m.value,
                            unit=m.unit,
                            source_document_id=m.document_id,
                            action_type="VIEW_DOCUMENT",
                            action_label="Review Document",
                            action_target=f"/documents/{m.document_id}"
                        ))

        # Sort items deterministically: HIGH -> MEDIUM -> LOW, then ID
        severity_weight = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        sorted_items = sorted(
            items,
            key=lambda x: (
                -severity_weight.get(x.severity, 0),
                0 if x.type in ("CLASSIFICATION_CONFLICT", "EVIDENCE_ISSUE", "LOW_CONFIDENCE", "DOCUMENT_REVIEW") else 1,
                -(x.document_id or 0)
            )
        )

        # Build deterministic summary
        summary = AttentionSummary(
            total=len(sorted_items),
            high=sum(1 for i in sorted_items if i.severity == "HIGH"),
            medium=sum(1 for i in sorted_items if i.severity == "MEDIUM"),
            low=sum(1 for i in sorted_items if i.severity == "LOW"),
            documents_needing_review=sum(1 for i in sorted_items if i.type in ("DOCUMENT_REVIEW", "LOW_CONFIDENCE", "CLASSIFICATION_CONFLICT", "EVIDENCE_ISSUE")),
            missing_data_items=sum(1 for i in sorted_items if i.type == "MISSING_DATA"),
            metric_changes=sum(1 for i in sorted_items if i.type == "METRIC_CHANGE")
        )

        return AttentionResponse(
            items=sorted_items,
            summary=summary
        )

copilot_attention_service = CopilotAttentionService()
