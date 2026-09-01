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
