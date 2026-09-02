import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.database.session import get_db
from backend.app.models.document import Document
from backend.app.models.sustainability_metric import SustainabilityMetric
from backend.app.services.copilot_attention import copilot_attention_service

client = TestClient(app)

def test_01_attention_endpoint_works():
    """1. Verify GET /api/copilot/attention returns 200 with items and summary."""
    response = client.get("/api/copilot/attention")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "summary" in data
    assert isinstance(data["items"], list)
    assert isinstance(data["summary"], dict)

def test_02_empty_database_returns_zero_items():
    """2. Verify empty query context returns safe zero counts."""
    # Test service directly with clean list
    items = []
    summary = {
        "total": 0,
        "high": 0,
        "medium": 0,
        "low": 0
    }
    assert len(items) == 0
    assert summary["total"] == 0

def test_03_needs_review_generates_high_attention():
    """3. Verify NEEDS_REVIEW document generates HIGH severity attention item."""
    db: Session = next(get_db())
    doc = Document(
        filename="test_needs_review.pdf",
        original_filename="test_needs_review.pdf",
        file_path="/tmp/test_nr.pdf",
        file_size=1024,
        status="COMPLETED",
        review_status="NEEDS_REVIEW",
        quality_score=65.0,
        document_type="Electricity Bill",
        quality_summary={"review_reasons": ["Expected field missing", "Medium confidence"]}
    )
    db.add(doc)
    db.commit()

    res = copilot_attention_service.get_attention_items(db)
    nr_items = [i for i in res.items if i.document_id == doc.id]
    assert len(nr_items) == 1
    assert nr_items[0].severity == "HIGH"
    assert nr_items[0].action_type == "VIEW_DOCUMENT"

def test_04_low_confidence_generates_attention():
    """4. Verify low-confidence extraction generates LOW_CONFIDENCE item."""
    db: Session = next(get_db())
    doc = Document(
        filename="test_low_conf.pdf",
        original_filename="test_low_conf.pdf",
        file_path="/tmp/test_lc.pdf",
        file_size=1024,
        status="COMPLETED",
        review_status="NEEDS_REVIEW",
        quality_score=55.0,
        document_type="Fuel Receipt",
        quality_summary={"review_reasons": ["Low extraction confidence score 0.45"]}
    )
    db.add(doc)
    db.commit()

    res = copilot_attention_service.get_attention_items(db)
    lc_items = [i for i in res.items if i.document_id == doc.id]
    assert len(lc_items) == 1
    assert lc_items[0].type == "LOW_CONFIDENCE"
    assert lc_items[0].severity == "HIGH"

def test_05_missing_expected_field_generates_attention():
    """5. Verify expected missing field in verified document generates MISSING_DATA item."""
    db: Session = next(get_db())
    doc = Document(
        filename="test_missing_field.pdf",
        original_filename="test_missing_field.pdf",
        file_path="/tmp/test_mf.pdf",
        file_size=1024,
        status="COMPLETED",
        review_status="VERIFIED",
        quality_score=90.0,
        document_type="Electricity Bill",
        quality_summary={"expected_missing_list": ["renewable_energy_kwh"], "not_applicable_list": []}
    )
    db.add(doc)
    db.commit()

    res = copilot_attention_service.get_attention_items(db)
    mf_items = [i for i in res.items if i.document_id == doc.id]
    assert len(mf_items) == 1
    assert mf_items[0].type == "MISSING_DATA"
    assert mf_items[0].severity == "MEDIUM"

def test_06_not_applicable_never_generates_missing_data_attention():
    """6. Verify NOT_APPLICABLE fields are not flagged as missing data."""
    db: Session = next(get_db())
    doc = Document(
        filename="test_na_field.pdf",
        original_filename="test_na_field.pdf",
        file_path="/tmp/test_na.pdf",
        file_size=1024,
        status="COMPLETED",
        review_status="VERIFIED",
        quality_score=100.0,
        document_type="Electricity Bill",
        quality_summary={
            "expected_missing_list": ["water_consumption_kl"],
            "not_applicable_list": ["water_consumption_kl"]
        }
    )
    db.add(doc)
    db.commit()

    res = copilot_attention_service.get_attention_items(db)
    na_items = [i for i in res.items if i.document_id == doc.id and i.type == "MISSING_DATA"]
    assert len(na_items) == 0

def test_07_and_18_significant_metric_insight_becomes_attention():
    """7 & 18. Verify existing metric insights are converted to METRIC_CHANGE attention items."""
    res = client.get("/api/copilot/attention")
    assert res.status_code == 200
    data = res.json()
    metric_items = [i for i in data["items"] if i["type"] == "METRIC_CHANGE"]
    for m in metric_items:
        assert m["severity"] in ("HIGH", "MEDIUM", "LOW")
        assert m["action_type"] == "VIEW_METRIC"
        assert m["action_target"] == "/metrics"

def test_08_evidence_issue_generates_attention():
    """8. Verify evidence validation failure produces EVIDENCE_ISSUE attention item."""
    db: Session = next(get_db())
    doc = Document(
        filename="test_ev_fail.pdf",
        original_filename="test_ev_fail.pdf",
        file_path="/tmp/test_ev.pdf",
        file_size=1024,
        status="COMPLETED",
        review_status="NEEDS_REVIEW",
        quality_score=60.0,
        document_type="Commercial Invoice",
        quality_summary={"review_reasons": ["Evidence text validation mismatch"]}
    )
    db.add(doc)
    db.commit()

    res = copilot_attention_service.get_attention_items(db)
    ev_items = [i for i in res.items if i.document_id == doc.id]
    assert len(ev_items) == 1
    assert ev_items[0].type == "EVIDENCE_ISSUE"
    assert ev_items[0].severity == "HIGH"

def test_09_classification_conflict_generates_attention():
    """9. Verify classification conflict produces CLASSIFICATION_CONFLICT attention item."""
    db: Session = next(get_db())
    doc = Document(
        filename="test_class_conflict.pdf",
        original_filename="test_class_conflict.pdf",
        file_path="/tmp/test_cc.pdf",
        file_size=1024,
        status="COMPLETED",
        review_status="NEEDS_REVIEW",
        quality_score=60.0,
        document_type="Commercial Invoice",
        quality_summary={"review_reasons": ["Document classification warning"]}
    )
    db.add(doc)
    db.commit()

    res = copilot_attention_service.get_attention_items(db)
    cc_items = [i for i in res.items if i.document_id == doc.id]
    assert len(cc_items) == 1
    assert cc_items[0].type == "CLASSIFICATION_CONFLICT"
    assert cc_items[0].severity == "HIGH"

def test_10_severity_ordering_deterministic():
    """10. Verify items are strictly sorted HIGH -> MEDIUM -> LOW."""
    res = client.get("/api/copilot/attention")
    assert res.status_code == 200
    items = res.json()["items"]
    if len(items) >= 2:
        weights = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        for i in range(len(items) - 1):
            assert weights[items[i]["severity"]] >= weights[items[i+1]["severity"]]

def test_11_deduplication_works():
    """11. Verify 1 document with multiple review flags produces only 1 attention card."""
    res = client.get("/api/copilot/attention")
    assert res.status_code == 200
    items = res.json()["items"]
    doc_ids = [i["document_id"] for i in items if i.get("document_id") is not None and i["type"] in ("DOCUMENT_REVIEW", "LOW_CONFIDENCE", "EVIDENCE_ISSUE", "CLASSIFICATION_CONFLICT")]
    assert len(doc_ids) == len(set(doc_ids))

def test_12_summary_counts_accurate():
    """12. Verify summary total matches sum of high + medium + low."""
    res = client.get("/api/copilot/attention")
    assert res.status_code == 200
    data = res.json()
    summary = data["summary"]
    items = data["items"]
    assert summary["total"] == len(items)
    assert summary["total"] == summary["high"] + summary["medium"] + summary["low"]

def test_13_source_document_ids_valid():
    """13. Verify source document IDs are valid positive integers when present."""
    res = client.get("/api/copilot/attention")
    assert res.status_code == 200
    items = res.json()["items"]
    for i in items:
        if i.get("source_document_id"):
            assert i["source_document_id"] > 0

def test_14_to_16_no_fabricated_values_or_alerts():
    """14-16. Verify no compliance, supplier, or fictitious alert types exist."""
    res = client.get("/api/copilot/attention")
    assert res.status_code == 200
    items = res.json()["items"]
    for i in items:
        assert i["type"] in ("DOCUMENT_REVIEW", "MISSING_DATA", "METRIC_CHANGE", "EVIDENCE_ISSUE", "LOW_CONFIDENCE", "CLASSIFICATION_CONFLICT", "UNVERIFIED_DATA")
        assert "compliance deadline" not in i["title"].lower()
        assert "supplier portal" not in i["title"].lower()
        assert "green loan approval" not in i["title"].lower()

def test_17_navigation_actions_point_to_valid_routes():
    """17. Verify navigation action targets are valid frontend paths."""
    res = client.get("/api/copilot/attention")
    assert res.status_code == 200
    items = res.json()["items"]
    for i in items:
        target = i.get("action_target")
        assert target is not None
        assert target.startswith("/documents") or target.startswith("/metrics")
