import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_copilot_chat_endpoint_valid_message():
    """Verify Copilot endpoint returns structured response for valid question."""
    response = client.post(
        "/api/copilot/chat",
        json={"message": "What needs my attention?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert isinstance(data["answer"], str)
    assert len(data["answer"]) > 0
    assert "intent" in data
    assert "sources" in data
    assert isinstance(data["sources"], list)
    assert "actions" in data
    assert isinstance(data["actions"], list)

def test_copilot_chat_empty_message_rejected():
    """Verify empty or whitespace-only messages are rejected with 400 or 422."""
    response = client.post(
        "/api/copilot/chat",
        json={"message": "   "}
    )
    assert response.status_code in [400, 422]

def test_copilot_chat_missing_message_field():
    """Verify missing message field is rejected."""
    response = client.post(
        "/api/copilot/chat",
        json={}
    )
    assert response.status_code in [400, 422]

def test_copilot_chat_oversized_message_rejected():
    """Verify messages exceeding 2000 characters are rejected safely."""
    huge_message = "A" * 2500
    response = client.post(
        "/api/copilot/chat",
        json={"message": huge_message}
    )
    assert response.status_code in [400, 422]

def test_copilot_chat_no_internal_stack_trace_on_errors():
    """Verify error responses are safe and don't expose stack traces or internal paths."""
    response = client.post(
        "/api/copilot/chat",
        json={"message": ""}
    )
    assert response.status_code in [400, 422]
    error_text = str(response.json()).lower()
    assert "traceback" not in error_text
    assert "/home/" not in error_text
    assert ".py" not in error_text

def test_copilot_chat_with_document_id():
    """Verify Copilot endpoint supports document_id and contextual questions."""
    # First seed a sample document to ensure one exists
    seed_resp = client.post("/api/documents/sample-seed?sample_type=electricity")
    assert seed_resp.status_code in [200, 201]
    doc = seed_resp.json()
    doc_id = doc["id"]

    # Ask document-specific questions using document_id
    response = client.post(
        "/api/copilot/chat",
        json={"document_id": doc_id, "question": "What is the electricity consumption?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "electricity" in data["answer"].lower() or "kwh" in data["answer"].lower()

    # Ask for peak demand
    response_pd = client.post(
        "/api/copilot/chat",
        json={"document_id": doc_id, "message": "What is the peak demand?"}
    )
    assert response_pd.status_code == 200
    data_pd = response_pd.json()
    assert "128" in data_pd["answer"] or "peak demand" in data_pd["answer"].lower()

def test_copilot_chat_hallucination_prevention_on_document():
    """Verify chatbot states information cannot be found rather than hallucinating."""
    seed_resp = client.post("/api/documents/sample-seed?sample_type=electricity")
    assert seed_resp.status_code in [200, 201]
    doc_id = seed_resp.json()["id"]

    response = client.post(
        "/api/copilot/chat",
        json={"document_id": doc_id, "question": "What is the CEO personal phone number and flight ticket cost?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "couldn't find" in data["answer"].lower() or "not find" in data["answer"].lower() or "don't have" in data["answer"].lower()
