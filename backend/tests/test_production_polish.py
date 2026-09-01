import io
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health_check_endpoint():
    """Verify production health check returns detailed system status without secrets."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert data["service"] == "senseible-document-ai"
    assert "database" in data
    assert "ocr_available" in data
    assert "llm_status" in data
    # Ensure no secrets or API keys are exposed
    assert "api_key" not in str(data).lower()
    assert "password" not in str(data).lower()

def test_upload_non_pdf_rejection():
    """Verify non-PDF file extension is safely rejected with clear 400 error."""
    response = client.post(
        "/api/documents/upload",
        files={"file": ("test.txt", b"Hello world", "text/plain")}
    )
    assert response.status_code == 400
    assert "Only PDF documents are supported" in response.json()["detail"]

def test_upload_invalid_pdf_magic_bytes_rejection():
    """Verify fake PDF with corrupt/missing %PDF header is rejected."""
    fake_pdf_bytes = b"This is not a real PDF file header"
    response = client.post(
        "/api/documents/upload",
        files={"file": ("fake.pdf", fake_pdf_bytes, "application/pdf")}
    )
    assert response.status_code == 400
    assert "Invalid PDF format" in response.json()["detail"]

def test_upload_empty_file_rejection():
    """Verify empty 0-byte file is rejected cleanly."""
    response = client.post(
        "/api/documents/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")}
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()
