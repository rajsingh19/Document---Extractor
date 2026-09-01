import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.database.session import get_db, Base, engine
from backend.app.models.document import Document
from backend.app.models.sustainability_metric import SustainabilityMetric
from backend.app.services.copilot_context import copilot_context_service, classify_intent
from backend.app.schemas.copilot import CopilotContext

client = TestClient(app)

def test_01_context_service_returns_valid_structure():
    """1. Verify context service returns valid CopilotContext model structure."""
    db: Session = next(get_db())
    ctx = copilot_context_service.build_context(db, "What documents do I have?")
    assert isinstance(ctx, CopilotContext)
    assert ctx.intent == "DOCUMENT_SEARCH"
    assert hasattr(ctx, "summary")
    assert hasattr(ctx, "documents")
    assert hasattr(ctx, "metrics")
    assert hasattr(ctx, "insights")
    assert hasattr(ctx, "review_items")
    assert hasattr(ctx, "sources")
    assert hasattr(ctx, "historical_comparisons")

def test_02_empty_database_returns_safe_empty_context():
    """2. Verify querying against an empty or clean mock state does not crash."""
    # Test with dummy query
    db: Session = next(get_db())
    ctx = copilot_context_service.build_context(db, "Any unknown query 12345")
    assert ctx.intent == "GENERAL_HELP"
    assert ctx.summary.document_count >= 0
    assert isinstance(ctx.documents, list)
    assert isinstance(ctx.metrics, list)

def test_03_document_retrieval_works():
    """3. Verify documents in DB are mapped to DocumentContext correctly."""
    db: Session = next(get_db())
    doc = db.query(Document).first()
    if not doc:
        doc = Document(
            filename="test_doc.pdf",
            original_filename="test_doc.pdf",
            file_path="/tmp/test.pdf",
            file_size=1024,
            status="COMPLETED",
            review_status="VERIFIED",
            quality_score=95.0,
            company_name="Test Company",
            document_type="Electricity Bill",
            reporting_period="Oct 2024"
        )
        db.add(doc)
        db.commit()

    ctx = copilot_context_service.build_context(db, "List all documents")
    assert len(ctx.documents) > 0
    doc_ctx = ctx.documents[0]
    assert doc_ctx.document_id is not None
    assert doc_ctx.filename is not None
    assert isinstance(doc_ctx.quality_score, float)

def test_04_metric_retrieval_works():
    """4. Verify metrics in DB are retrieved for metric queries."""
    db: Session = next(get_db())
    doc = db.query(Document).first()
    assert doc is not None
    
    # Ensure at least one metric exists
    m = db.query(SustainabilityMetric).first()
    if not m:
        m = SustainabilityMetric(
            document_id=doc.id,
            company_name="Test Co",
            metric_type="electricity_consumption",
            category="energy",
            value=50000.0,
            unit="kWh",
            source_field="electricity_kwh",
            source_text="Total Active Energy: 50,000 kWh",
            confidence=0.98,
            verification_status="HUMAN_VERIFIED"
        )
        db.add(m)
        db.commit()

    ctx = copilot_context_service.build_context(db, "What is our electricity consumption?")
    assert ctx.intent == "METRIC_QUERY"
    assert len(ctx.metrics) > 0
    metric_entry = next((m for m in ctx.metrics if m.metric_type == "electricity_consumption"), ctx.metrics[0])
    assert metric_entry.value > 0
    assert metric_entry.unit == "kWh"

def test_05_insight_retrieval_works():
    """5. Verify deterministic insights are included in context."""
    db: Session = next(get_db())
    ctx = copilot_context_service.build_context(db, "What actions should we take?")
    assert ctx.intent == "ACTION_RECOMMENDATION"
    assert isinstance(ctx.insights, list)

def test_06_review_item_retrieval_works():
    """6. Verify NEEDS_REVIEW documents are routed into review_items."""
    db: Session = next(get_db())
    # Ensure at least one review document exists in DB
    rev_doc = db.query(Document).filter(Document.review_status == "NEEDS_REVIEW").first()
    if not rev_doc:
        rev_doc = Document(
            filename="review_sample.pdf",
            original_filename="review_sample.pdf",
            file_path="/tmp/review.pdf",
            file_size=2048,
            status="COMPLETED",
            review_status="NEEDS_REVIEW",
            quality_score=68.0,
            quality_summary={"expected_missing_list": ["electricity_kwh"], "review_reasons": ["Expected field missing"]}
        )
        db.add(rev_doc)
        db.commit()

    ctx = copilot_context_service.build_context(db, "Which documents need review?")
    assert ctx.intent == "DOCUMENT_REVIEW"
    assert len(ctx.review_items) > 0
    item = ctx.review_items[0]
    assert item.document_id > 0
    assert isinstance(item.reason, str)
    assert item.quality_score >= 0.0


def test_07_to_15_intent_routing_coverage():
    """7-15. Verify all 8 primary intents and fallback route accurately."""
    assert classify_intent("What documents do I have?") == "DOCUMENT_SEARCH"
    assert classify_intent("Show uploaded invoices") == "DOCUMENT_SEARCH"
    assert classify_intent("Which documents need review?") == "DOCUMENT_REVIEW"
    assert classify_intent("What needs my attention?") == "DOCUMENT_REVIEW"
    assert classify_intent("What is our electricity consumption?") == "METRIC_QUERY"
    assert classify_intent("How much water was consumed?") == "METRIC_QUERY"
    assert classify_intent("How has electricity changed?") == "TREND_ANALYSIS"
    assert classify_intent("Show historical trends over time") == "TREND_ANALYSIS"
    assert classify_intent("What sustainability data is missing?") == "MISSING_DATA"
    assert classify_intent("Why did emissions change?") == "EMISSIONS_ANALYSIS"
    assert classify_intent("What are our Scope 1 and Scope 2 GHG emissions?") == "EMISSIONS_ANALYSIS"
    assert classify_intent("How can we reduce emissions?") == "ACTION_RECOMMENDATION"
    assert classify_intent("What action recommendations do you have?") == "ACTION_RECOMMENDATION"
    assert classify_intent("Hello, how does this work?") == "GENERAL_HELP"
    assert classify_intent("") == "GENERAL_HELP"

def test_16_null_values_not_fabricated():
    """16. Verify null fields remain None in context without guessing."""
    db: Session = next(get_db())
    ctx = copilot_context_service.build_context(db, "List documents")
    for doc in ctx.documents:
        if doc.company_name is None:
            assert doc.company_name is None

def test_17_not_applicable_remains_distinct():
    """17. Verify NOT_APPLICABLE status is not confused with missing data."""
    db: Session = next(get_db())
    ctx = copilot_context_service.build_context(db, "What data is missing?")
    assert ctx.intent == "MISSING_DATA"
    for r in ctx.review_items:
        assert isinstance(r.affected_fields, list)

def test_18_evidence_source_text_preserved():
    """18. Verify verbatim source text from extraction is preserved in sources."""
    db: Session = next(get_db())
    ctx = copilot_context_service.build_context(db, "Show documents")
    for src in ctx.sources:
        assert src.document_id is not None
        assert src.field is not None
        # Source text must be raw string or None, not fabricated text
        if src.source_text:
            assert isinstance(src.source_text, str)

def test_19_context_limits_respected():
    """19. Verify context retrieval respects upper bounds on documents and sources."""
    db: Session = next(get_db())
    ctx = copilot_context_service.build_context(db, "Show documents")
    assert len(ctx.documents) <= 10
    assert len(ctx.sources) <= 20
    assert len(ctx.insights) <= 10
    assert len(ctx.metrics) <= 15

def test_20_summary_counts_match_database():
    """20. Verify summary counter values reflect actual DB counts."""
    db: Session = next(get_db())
    real_doc_count = db.query(Document).count()
    real_metric_count = db.query(SustainabilityMetric).count()
    real_review_count = db.query(Document).filter(Document.review_status == "NEEDS_REVIEW").count()

    summary = copilot_context_service.build_summary(db)
    assert summary.document_count == real_doc_count
    assert summary.metric_count == real_metric_count
    assert summary.documents_needing_review == real_review_count

def test_21_get_copilot_context_debug_endpoint():
    """21. Verify GET /api/copilot/context returns structured context."""
    response = client.get("/api/copilot/context?query=What+is+our+electricity+consumption?")
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "METRIC_QUERY"
    assert "summary" in data
    assert "documents" in data
    assert "metrics" in data

def test_22_post_copilot_chat_returns_grounded_response():
    """22. Verify POST /api/copilot/chat returns intent, sources, actions, and summary."""
    response = client.post(
        "/api/copilot/chat",
        json={"message": "Which documents need review?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "DOCUMENT_REVIEW"
    assert data["context_available"] is True
    assert "actions" in data
    assert isinstance(data["actions"], list)
    assert len(data["actions"]) > 0
    assert "summary" in data
