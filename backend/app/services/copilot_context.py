import re
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_

from backend.app.models.document import Document
from backend.app.models.sustainability_metric import SustainabilityMetric
from backend.app.services.insights_service import insights_service
from backend.app.schemas.copilot import (
    CopilotContext,
    CopilotSummary,
    DocumentContext,
    MetricContext,
    InsightContext,
    ReviewContext,
    SourceContext,
)

logger = logging.getLogger("senseible-copilot-context")

# Limits to prevent context bloat
MAX_DOCUMENTS = 10
MAX_INSIGHTS = 10
MAX_REVIEW_ITEMS = 10
MAX_SOURCES = 20
MAX_METRICS = 15

def classify_intent(query: str) -> str:
    """
    Deterministic intent router based on normalized pattern matching.
    Priority-ordered with GENERAL_HELP fallback.
    """
    q = (query or "").strip().lower()

    if not q:
        return "GENERAL_HELP"

    # 1. DOCUMENT_REVIEW: Items needing attention or verification
    if any(k in q for k in [
        "need review", "needs review", "attention", "pending review", 
        "unverified", "require review", "requires review", "flagged", "quality issue"
    ]):
        return "DOCUMENT_REVIEW"

    # 2. MISSING_DATA: Gaps in reporting or missing fields
    if any(k in q for k in [
        "missing", "not applicable", "unfilled", "data gap", "gaps in data"
    ]):
        return "MISSING_DATA"

    # 3. ACTION_RECOMMENDATION: Steps to reduce emissions or improve sustainability
    if any(k in q for k in [
        "how can we reduce", "how can i reduce", "reduce emission", "reduce emissions", 
        "how to reduce", "recommendation", "recommendations", "how to improve", 
        "what actions", "action recommendation", "next steps"
    ]):
        return "ACTION_RECOMMENDATION"

    # 4. EMISSIONS_ANALYSIS: Scope 1/2 GHG, carbon footprint changes
    if any(k in q for k in [
        "emission change", "emissions change", "why did emission", "why did emissions",
        "carbon footprint", "scope 1", "scope 2", "ghg emission", "ghg emissions", 
        "tco2e", "carbon emission", "carbon emissions"
    ]):
        return "EMISSIONS_ANALYSIS"

    # 5. TREND_ANALYSIS: Period-over-period comparisons and trajectory
    if any(k in q for k in [
        "trend", "trends", "historical", "how has", "how have", "change over time", 
        "increased", "decreased", "period over period", "month over month", "vs last month"
    ]):
        return "TREND_ANALYSIS"

    # 6. METRIC_QUERY: Specific sustainability parameters and latest values
    if any(k in q for k in [
        "consumption", "electricity", "energy", "water", "fuel", "diesel", 
        "kwh", "kl", "waste", "hazardous", "metric", "metrics", "latest value", 
        "total cost", "payable amount", "peak demand"
    ]):
        return "METRIC_QUERY"

    # 7. DOCUMENT_SEARCH: Finding, listing, or checking documents
    if any(k in q for k in [
        "what document", "what documents", "list document", "list documents", 
        "show document", "show documents", "find document", "invoice", "invoices", 
        "bill", "bills", "files", "docket", "manifest", "audit report", "uploaded"
    ]):
        return "DOCUMENT_SEARCH"

    # 8. Fallback
    return "GENERAL_HELP"


class CopilotContextService:
    """
    Senseible AI Copilot Grounded Context Layer (Step 11B).
    Gathers, validates, and compacts factual data from documents, metrics, evidence,
    and deterministic insights without hallucination or LLM generation.
    """

    def build_summary(self, db: Session) -> CopilotSummary:
        """Calculate deterministic summary counters directly from the database."""
        doc_count = db.query(func.count(Document.id)).scalar() or 0
        needs_review = db.query(func.count(Document.id)).filter(Document.review_status == "NEEDS_REVIEW").scalar() or 0
        verified = db.query(func.count(Document.id)).filter(Document.review_status == "VERIFIED").scalar() or 0
        metric_count = db.query(func.count(SustainabilityMetric.id)).scalar() or 0

        # Active attention items = review docs + actionable insights
        insights = insights_service.generate_metric_insights(db)
        action_insights = [i for i in insights if i.severity in ("ACTION_REQUIRED", "REVIEW", "WARNING")]
        active_attention = needs_review + len(action_insights)

        return CopilotSummary(
            document_count=doc_count,
            documents_needing_review=needs_review,
            verified_documents=verified,
            metric_count=metric_count,
            active_attention_items=active_attention
        )

    def extract_sources_from_documents(self, documents: List[Document], limit: int = MAX_SOURCES) -> List[SourceContext]:
        """Extract verbatim source evidence anchors preserved during document extraction."""
        sources: List[SourceContext] = []
        for doc in documents:
            if not doc.structured_data:
                continue
            evidence_list = doc.structured_data.get("evidence", [])
            for ev in evidence_list:
                if len(sources) >= limit:
                    return sources
                field_name = ev.get("field", "unknown_field")
                val = ev.get("human_corrected_value") if ev.get("human_corrected_value") is not None else ev.get("value")
                unit = ev.get("unit")
                src_text = ev.get("source_text")

                sources.append(SourceContext(
                    document_id=doc.id,
                    document_name=doc.original_filename or doc.filename,
                    field=field_name,
                    value=val,
                    unit=unit,
                    source_text=src_text
                ))
        return sources

    def build_context(self, db: Session, query: str) -> CopilotContext:
        """
        Build compact, intent-aware grounded context object from real Senseible data.
        """
        intent = classify_intent(query)
        summary = self.build_summary(db)

        docs_ctx: List[DocumentContext] = []
        metrics_ctx: List[MetricContext] = []
        insights_ctx: List[InsightContext] = []
        review_ctx: List[ReviewContext] = []
        sources_ctx: List[SourceContext] = []
        historical_comparisons: List[Dict[str, Any]] = []

        all_docs = db.query(Document).order_by(desc(Document.created_at)).all()
        all_metrics = db.query(SustainabilityMetric).order_by(desc(SustainabilityMetric.created_at)).all()
        all_insights = insights_service.generate_metric_insights(db)

        # 1. Intent: DOCUMENT_REVIEW / What needs attention
        if intent == "DOCUMENT_REVIEW":
            review_docs = [d for d in all_docs if d.review_status == "NEEDS_REVIEW"][:MAX_REVIEW_ITEMS]
            for doc in review_docs:
                q_summary = doc.quality_summary or {}
                missing = q_summary.get("expected_missing_list") or q_summary.get("missing_fields") or []
                reasons = q_summary.get("review_reasons") or []
                reason_str = reasons[0] if reasons else ("Missing fields: " + ", ".join(missing) if missing else "Requires review")

                review_ctx.append(ReviewContext(
                    document_id=doc.id,
                    filename=doc.original_filename or doc.filename,
                    reason=reason_str,
                    quality_score=float(doc.quality_score or 0.0),
                    affected_fields=missing
                ))

                docs_ctx.append(DocumentContext(
                    document_id=doc.id,
                    filename=doc.original_filename or doc.filename,
                    document_type=doc.document_type,
                    company_name=doc.company_name,
                    reporting_period=doc.reporting_period,
                    status=doc.status,
                    quality_score=float(doc.quality_score or 0.0),
                    verification_status=doc.review_status or "NEEDS_REVIEW"
                ))

            # Include high severity insights
            for ins in [i for i in all_insights if i.severity in ("ACTION_REQUIRED", "REVIEW")][:MAX_INSIGHTS]:
                insights_ctx.append(InsightContext(
                    category=ins.category,
                    severity=ins.severity,
                    metric_type=ins.metric_type,
                    message=ins.message,
                    current_value=ins.current_value,
                    previous_value=ins.previous_value,
                    percentage_change=ins.percentage_change,
                    source_document_id=ins.source_document_id
                ))

            sources_ctx = self.extract_sources_from_documents(review_docs, limit=MAX_SOURCES)

        # 2. Intent: MISSING_DATA
        elif intent == "MISSING_DATA":
            for doc in all_docs[:MAX_DOCUMENTS]:
                q_summary = doc.quality_summary or {}
                missing = q_summary.get("expected_missing_list") or q_summary.get("missing_fields") or []
                na_list = q_summary.get("not_applicable_list") or []

                if missing:
                    review_ctx.append(ReviewContext(
                        document_id=doc.id,
                        filename=doc.original_filename or doc.filename,
                        reason=f"Missing expected: {', '.join(missing)} (N/A: {len(na_list)})",
                        quality_score=float(doc.quality_score or 0.0),
                        affected_fields=missing
                    ))

                docs_ctx.append(DocumentContext(
                    document_id=doc.id,
                    filename=doc.original_filename or doc.filename,
                    document_type=doc.document_type,
                    company_name=doc.company_name,
                    reporting_period=doc.reporting_period,
                    status=doc.status,
                    quality_score=float(doc.quality_score or 0.0),
                    verification_status=doc.review_status or "NEEDS_REVIEW"
                ))

        # 3. Intent: EMISSIONS_ANALYSIS / Carbon footprint
        elif intent == "EMISSIONS_ANALYSIS":
            emission_metrics = [m for m in all_metrics if m.category == "carbon" or "emission" in m.metric_type][:MAX_METRICS]
            for m in emission_metrics:
                metrics_ctx.append(MetricContext(
                    metric_type=m.metric_type,
                    category=m.category,
                    value=m.value,
                    unit=m.unit,
                    period=m.period_end or m.period_start,
                    confidence=m.confidence,
                    verification_status=m.verification_status,
                    source_document_id=m.document_id
                ))

            # Emission-related insights
            for ins in [i for i in all_insights if i.category == "carbon" or "emission" in (i.metric_type or "")][:MAX_INSIGHTS]:
                insights_ctx.append(InsightContext(
                    category=ins.category,
                    severity=ins.severity,
                    metric_type=ins.metric_type,
                    message=ins.message,
                    current_value=ins.current_value,
                    previous_value=ins.previous_value,
                    percentage_change=ins.percentage_change,
                    source_document_id=ins.source_document_id
                ))

            rel_doc_ids = {m.document_id for m in emission_metrics}
            rel_docs = [d for d in all_docs if d.id in rel_doc_ids][:MAX_DOCUMENTS]
            for d in rel_docs:
                docs_ctx.append(DocumentContext(
                    document_id=d.id,
                    filename=d.original_filename or d.filename,
                    document_type=d.document_type,
                    company_name=d.company_name,
                    reporting_period=d.reporting_period,
                    status=d.status,
                    quality_score=float(d.quality_score or 0.0),
                    verification_status=d.review_status or "READY"
                ))
            sources_ctx = self.extract_sources_from_documents(rel_docs, limit=MAX_SOURCES)

        # 4. Intent: TREND_ANALYSIS
        elif intent == "TREND_ANALYSIS":
            # Group metrics by type to compute period comparison
            for m in all_metrics[:MAX_METRICS]:
                metrics_ctx.append(MetricContext(
                    metric_type=m.metric_type,
                    category=m.category,
                    value=m.value,
                    unit=m.unit,
                    period=m.period_end or m.period_start,
                    confidence=m.confidence,
                    verification_status=m.verification_status,
                    source_document_id=m.document_id
                ))

            for ins in [i for i in all_insights if i.percentage_change is not None][:MAX_INSIGHTS]:
                insights_ctx.append(InsightContext(
                    category=ins.category,
                    severity=ins.severity,
                    metric_type=ins.metric_type,
                    message=ins.message,
                    current_value=ins.current_value,
                    previous_value=ins.previous_value,
                    percentage_change=ins.percentage_change,
                    source_document_id=ins.source_document_id
                ))

                historical_comparisons.append({
                    "metric_type": ins.metric_type,
                    "period": ins.period,
                    "current_value": ins.current_value,
                    "previous_value": ins.previous_value,
                    "percentage_change": ins.percentage_change,
                    "unit": ins.unit
                })

        # 5. Intent: ACTION_RECOMMENDATION
        elif intent == "ACTION_RECOMMENDATION":
            for ins in all_insights[:MAX_INSIGHTS]:
                insights_ctx.append(InsightContext(
                    category=ins.category,
                    severity=ins.severity,
                    metric_type=ins.metric_type,
                    message=ins.message,
                    current_value=ins.current_value,
                    previous_value=ins.previous_value,
                    percentage_change=ins.percentage_change,
                    source_document_id=ins.source_document_id
                ))

            for m in all_metrics[:MAX_METRICS]:
                metrics_ctx.append(MetricContext(
                    metric_type=m.metric_type,
                    category=m.category,
                    value=m.value,
                    unit=m.unit,
                    period=m.period_end or m.period_start,
                    confidence=m.confidence,
                    verification_status=m.verification_status,
                    source_document_id=m.document_id
                ))

        # 6. Intent: METRIC_QUERY
        elif intent == "METRIC_QUERY":
            matched_metrics = []
            for m in all_metrics:
                if any(w in query.lower() for w in m.metric_type.split("_")) or any(w in query.lower() for w in [m.category, m.unit.lower()]):
                    matched_metrics.append(m)
            
            selected_metrics = (matched_metrics if matched_metrics else all_metrics)[:MAX_METRICS]
            for m in selected_metrics:
                metrics_ctx.append(MetricContext(
                    metric_type=m.metric_type,
                    category=m.category,
                    value=m.value,
                    unit=m.unit,
                    period=m.period_end or m.period_start,
                    confidence=m.confidence,
                    verification_status=m.verification_status,
                    source_document_id=m.document_id
                ))

            rel_doc_ids = {m.document_id for m in selected_metrics}
            rel_docs = [d for d in all_docs if d.id in rel_doc_ids][:MAX_DOCUMENTS]
            for d in rel_docs:
                docs_ctx.append(DocumentContext(
                    document_id=d.id,
                    filename=d.original_filename or d.filename,
                    document_type=d.document_type,
                    company_name=d.company_name,
                    reporting_period=d.reporting_period,
                    status=d.status,
                    quality_score=float(d.quality_score or 0.0),
                    verification_status=d.review_status or "READY"
                ))
            sources_ctx = self.extract_sources_from_documents(rel_docs, limit=MAX_SOURCES)

        # 7. Intent: DOCUMENT_SEARCH
        elif intent == "DOCUMENT_SEARCH":
            for d in all_docs[:MAX_DOCUMENTS]:
                docs_ctx.append(DocumentContext(
                    document_id=d.id,
                    filename=d.original_filename or d.filename,
                    document_type=d.document_type,
                    company_name=d.company_name,
                    reporting_period=d.reporting_period,
                    status=d.status,
                    quality_score=float(d.quality_score or 0.0),
                    verification_status=d.review_status or "READY"
                ))
            sources_ctx = self.extract_sources_from_documents(all_docs[:MAX_DOCUMENTS], limit=MAX_SOURCES)

        # 8. GENERAL_HELP fallback: compact overview
        else:
            for d in all_docs[:5]:
                docs_ctx.append(DocumentContext(
                    document_id=d.id,
                    filename=d.original_filename or d.filename,
                    document_type=d.document_type,
                    company_name=d.company_name,
                    reporting_period=d.reporting_period,
                    status=d.status,
                    quality_score=float(d.quality_score or 0.0),
                    verification_status=d.review_status or "READY"
                ))

        return CopilotContext(
            intent=intent,
            query=query,
            summary=summary,
            documents=docs_ctx,
            metrics=metrics_ctx,
            insights=insights_ctx,
            review_items=review_ctx,
            sources=sources_ctx,
            historical_comparisons=historical_comparisons
        )

copilot_context_service = CopilotContextService()
