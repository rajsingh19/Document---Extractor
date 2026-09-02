# Senseible Document AI

> **AI Document Intelligence System for MSME Sustainability & Business Operations**
> 
> Production-ready B2B platform built with **FastAPI**, **PyMuPDF**, **Tesseract OCR Fallback**, **Deterministic Classifier**, **Context-Aware Number Parser**, **Verifiable Evidence Validator**, **Quality Scoring Engine**, **OpenAI LLM Extraction**, **Pydantic Validation**, **SQLAlchemy/SQLite**, and a clean **React + Vite + Tailwind CSS** UI.

---

## 1. Product Workflow & Architecture

The end-to-end user workflow follows a calm, deterministic pipeline:

```
[Upload PDF]
     │
     ▼
[Identify Document Type] ────► Automatic Multi-Signal Classifier (Electricity, Fuel, Water, Waste, ESG)
     │
     ▼
[Text / OCR Extraction]  ────► PyMuPDF Layout Preservation + Tesseract OCR Fallback
     │
     ▼
[Extract Structured Data]────► OpenAI LLM / Deterministic Non-Hallucinating Heuristic Engine
     │
     ▼
[Validate Evidence]      ────► Verifiable Source Text Containment & Unit Semantic Matching
     │
     ▼
[Quality Scoring]        ────► Deterministic Quality Score (0–100) & Review Routing
     │
     ▼
[Human Review & Verify]  ────► Audit-Logged Field Correction & User Verification Sign-Off
     │
     ▼
[Normalize & Aggregate]  ────► Historical Trends & Period-over-Period Sustainability Metrics
     │
     ▼
[Actionable Insights]    ────► Deterministic Rule-Based Alerts & Operational Recommendations
```

---

## 2. Quick Start Guide

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- (Optional) `tesseract-ocr` for local image OCR

---

### Backend Setup

1. **Navigate to the backend directory and activate the virtual environment:**
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   ```bash
   cp ../.env.example .env
   # Edit .env if you wish to provide an OPENAI_API_KEY (optional; deterministic fallback is active by default)
   ```

3. **Start the FastAPI backend server:**
   ```bash
   # From inside the backend directory:
   uvicorn app.main:app --host 0.0.0.0 --port 8005 --reload
   ```
   Backend will be accessible at `http://localhost:8005`.
   Interactive OpenAPI documentation is available at `http://localhost:8005/docs`.


---

### Frontend Setup

1. **Navigate to the frontend directory and install dependencies:**
   ```bash
   cd frontend
   npm install
   ```

2. **Start the Vite development server:**
   ```bash
   npm run dev
   ```
   Frontend will be accessible at `http://localhost:5173`.

3. **Build production bundle:**
   ```bash
   npm run build
   ```

---

## 3. Running the Test Suites & Validation Benchmark

### Run Backend Pytest Suite (54 Tests)
```bash
PYTHONPATH=. backend/venv/bin/pytest backend/tests/ -v
```

### Run Step 9 MSME Validation Benchmark (18 Real-World PDFs)
```bash
PYTHONPATH=. backend/venv/bin/python backend/validation_dataset/run_validation.py
```

---

## 4. Main API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Diagnostic system health check (DB, OCR, LLM) |
| `GET` | `/api/stats` | Aggregated dashboard statistics and counts |
| `POST` | `/api/documents/upload` | Upload PDF document with SHA-256 duplicate detection |
| `GET` | `/api/documents` | List documents with pagination, status filter, and search |
| `GET` | `/api/documents/{id}` | Get complete document details, structured data & evidence |
| `POST` | `/api/documents/{id}/verify` | Verify specific field with human review audit log |
| `POST` | `/api/documents/{id}/correct` | Correct field value and unit with audit trail |
| `PATCH` | `/api/documents/{id}/review-status` | Update document review status (`VERIFIED`, `NEEDS_REVIEW`) |
| `PATCH` | `/api/documents/{id}/classification` | Update or correct document classification type |
| `DELETE` | `/api/documents/{id}` | Delete document, file, and associated normalized metrics |
| `GET` | `/api/documents/{id}/audit-trail` | Retrieve immutable audit history for document |
| `GET` | `/api/metrics` | Retrieve all normalized sustainability metrics |
| `GET` | `/api/metrics/summary` | Retrieve KPI totals (Energy kWh, Water kL, GHG tCO2e) |
| `GET` | `/api/metrics/trends` | Retrieve chronological period trend data |
| `GET` | `/api/metrics/change` | Retrieve period-over-period delta calculation |
| `GET` | `/api/insights` | Retrieve deterministic rule-based actionable insights |
| `POST` | `/api/samples/seed` | Seed fictional sample demo documents (`electricity`, `esg`, `scanned`) |

---

## 5. Demonstration Workflow (2–5 Minute Demo)

1. **Open Dashboard**: Go to `http://localhost:5173`. Notice the clean B2B light aesthetic and system status indicator in the top navbar.
2. **Try Demo Data**: In the top navbar, click **Demo Data** &rarr; **Electricity Bill**. A realistic fictional HT electricity bill is processed automatically.
3. **Review Extraction & Evidence**: Click **View** to inspect the Document Detail page:
   - Check **Extraction Quality** (100 / 100 with explanation checklist).
   - Check **Extracted Information** table (Consumption, Demand, Power Factor, Cost).
   - Check **Source Evidence** (verbatim text excerpts showing where values were extracted).
4. **Human Review / Correction**: Edit a field, click **Save Correction**, and note the **Human Verified** badge and updated **Audit Trail**.
5. **Verify Document**: Click **Verify Document** &rarr; Status updates to **VERIFIED** with user timestamp.
6. **Inspect Normalized Metrics & Insights**: Click **Metrics** in the top navigation:
   - View top 4 KPI cards (Latest Period, Energy, Water, GHG).
   - Track **Historical Trends** across reporting periods.
   - Review **Actionable Insights** flagging period-over-period changes and operational recommendations.
