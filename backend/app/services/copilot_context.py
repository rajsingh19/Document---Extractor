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

def classify_intent(query: str, history: Optional[List[Dict[str, str]]] = None) -> str:
    """
    Deterministic intent router based on normalized pattern matching.
    Priority-ordered with conversational follow-up resolution and GENERAL_HELP fallback.
    """
    q = (query or "").strip().lower()

    if not q:
        return "GENERAL_HELP"

    # Contextual follow-up resolution (e.g. "What about previous month?", "How did that change?")
    combined_context = q
    if history:
        for turn in history[-4:]:
            combined_context += " " + turn.get("content", "").lower()

    # Carbon Credit Intents (Step 20)
    if any(k in q for k in ["why is my carbon credit readiness score", "why is my score", "explain readiness score", "explain carbon credit score"]):
        return "CARBON_CREDIT_EXPLAIN_SCORE"

    if any(k in q for k in ["what is missing before certification", "what is missing before methodology", "what evidence do i still need", "missing for carbon credits", "missing before certification"]):
        return "CARBON_CREDIT_MISSING"

    if any(k in q for k in ["what should i do next", "carbon credit next step", "carbon credit next action", "next steps for carbon credits"]) and any(c in combined_context for c in ["carbon credit", "readiness", "project", "certification"]):
        return "CARBON_CREDIT_NEXT_ACTION"

    if any(k in q for k in ["is this project verified", "is project verified", "verification status", "verified for carbon credits", "externally verified"]):
        return "CARBON_CREDIT_VERIFICATION"

    if any(k in q for k in ["methodology readiness", "verra eligible", "gold standard", "methodology review", "generic carbon standard"]):
        return "CARBON_CREDIT_METHODOLOGY"

    if any(k in q for k in ["carbon credit", "carbon credits", "ready for carbon credits", "carbon credit readiness", "tradable credits"]):
        return "CARBON_CREDIT_READINESS"

    # Step 22C: EMISSION_SCENARIO_ANALYSIS (What-if scenario modeling)
    if any(k in q for k in [
        "what if i replace", "what if we replace", "what if i reduce", "what if we reduce",
        "what if i switch", "what if we switch", "what if diesel", "what if electricity",
        "what if grid", "what if solar", "what if consumption", "what if fuel",
        "scenario analysis", "emission scenario", "emissions scenario", "what-if", "what if",
        "how would this scenario affect", "how does this scenario affect",
        "model a scenario", "scenario calculation", "what assumptions did you use",
        "how much will solar save", "how much co2 will solar save", "how much co2 would solar save",
        "can i replace grid electricity with solar", "switch to solar"
    ]):
        return "EMISSION_SCENARIO_ANALYSIS"

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

    # 3. ACTION_RECOMMENDATION / REDUCTION_PRIORITY: Steps to reduce emissions, reduction intelligence priorities, or improve sustainability

    reduction_verbs = ["reduce", "reduction", "lower", "lowering", "decrease", "decreasing", "cut", "cutting", "minimize", "minimizing", "mitigate"]
    emissions_terms = ["emission", "emissions", "carbon", "footprint", "ghg", "scope 1", "scope 2", "scope1", "scope2"]
    has_reduction_action = any(v in q for v in reduction_verbs) and any(e in q for e in emissions_terms)

    if has_reduction_action or any(k in q for k in [
        "how can we reduce", "how can i reduce", "reduce emission", "reduce emissions", 
        "how to reduce", "can we reduce", "can i reduce", "recommendation", "recommendations", "how to improve", 
        "what actions", "action recommendation", "next steps", "focus on first", "focus first",
        "what should i focus", "what to focus", "where should i focus", "where should we focus", "where to focus",
        "what can i do", "what can we do", "what should i do",
        "biggest opportunity", "biggest sustainability opportunity", "biggest reduction opportunity",
        "opportunity", "opportunities", "where is our biggest",
        "what should i focus on first", "what should we focus on first", "where should i focus first", "where should we focus first",
        "where can i reduce emissions", "where can we reduce emissions",
        "what is my biggest reduction opportunity", "why is electricity my top priority", "why is electricity top priority",
        "what should i work on next", "what should we work on next",
        "which emission source needs attention most", "which source needs attention",
        "reduction priority", "reduction priorities", "reduction intelligence",
        "top reduction priority", "highest reduction priority",
        "reduction plan", "reduction roadmap", "reduction target", "reach my target",
        "reach my reduction target", "reach our reduction target", "reach target",
        "how far am i from my target", "how far are we from target",
        "what is blocking my reduction target", "what is blocking my target",
        "create a reduction plan", "plan to reduce"
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
        "increased", "decreased", "period over period", "month over month", "vs last month",
        "previous period", "previous month", "how did that change", "what about before"
    ]):
        return "TREND_ANALYSIS"

    # 6. METRIC_QUERY: Specific sustainability parameters and latest values
    if any(k in q for k in [
        "consumption", "electricity", "energy", "water", "fuel", "diesel", 
        "kwh", "kl", "waste", "hazardous", "metric", "metrics", "latest value", 
        "total cost", "payable amount", "peak demand"
    ]) or (history and any(k in combined_context for k in ["electricity", "water", "fuel", "waste", "emission"]) and any(f in q for f in ["what about", "how much", "previous"])):
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
    Senseible AI Copilot Grounded Context Layer (Step 11B & 11C).
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

    def build_context(
        self,
        db: Session,
        query: str,
        history: Optional[List[Dict[str, str]]] = None,
        document_id: Optional[int] = None
    ) -> CopilotContext:
        """
        Build compact, intent-aware grounded context object from real Senseible data.
        If document_id is provided, scopes all context strictly to that document.
        """
        intent = classify_intent(query, history=history)
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

        target_doc = None
        if document_id is not None:
            target_doc = db.query(Document).filter(Document.id == document_id).first()
            if target_doc:
                all_docs = [target_doc]
                all_metrics = db.query(SustainabilityMetric).filter(SustainabilityMetric.document_id == document_id).order_by(desc(SustainabilityMetric.created_at)).all()
                all_insights = [i for i in all_insights if i.source_document_id == document_id]

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

            # Include relevant documents and sources for recommendations
            rel_doc_ids = {m.document_id for m in all_metrics[:MAX_METRICS] if m.document_id}
            rel_docs = [d for d in all_docs if d.id in rel_doc_ids][:MAX_DOCUMENTS]
            if not rel_docs and all_docs:
                rel_docs = all_docs[:MAX_DOCUMENTS]

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

        # 6. Intent: METRIC_QUERY
        elif intent == "METRIC_QUERY":
            q_lower = query.lower()
            exact_type_matches = []
            category_matches = []

            for m in all_metrics:
                type_words = m.metric_type.split("_")
                if any(w in q_lower for w in type_words if len(w) > 3):
                    exact_type_matches.append(m)
                elif m.category in q_lower or (m.unit and m.unit.lower() in q_lower):
                    category_matches.append(m)

            matched_metrics = exact_type_matches if exact_type_matches else category_matches
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

        if document_id is not None and target_doc:
            if not any(d.document_id == target_doc.id for d in docs_ctx):
                docs_ctx.insert(0, DocumentContext(
                    document_id=target_doc.id,
                    filename=target_doc.original_filename or target_doc.filename,
                    document_type=target_doc.document_type,
                    company_name=target_doc.company_name,
                    reporting_period=target_doc.reporting_period,
                    status=target_doc.status,
                    quality_score=float(target_doc.quality_score or 0.0),
                    verification_status=target_doc.review_status or "READY"
                ))
            if not sources_ctx:
                sources_ctx = self.extract_sources_from_documents([target_doc], limit=MAX_SOURCES)

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
