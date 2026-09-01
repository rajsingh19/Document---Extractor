# Senseible Document AI

> **AI Document Extraction System for MSME Sustainability & Business Documents**
> 
> Production-quality MVP built with **FastAPI**, **PyMuPDF**, **Tesseract OCR Fallback**, **OpenAI LLM Extraction**, **Pydantic Validation**, **SQLAlchemy/SQLite**, and a **React + Vite + Tailwind CSS** Dashboard.

---

## Architecture & Extraction Pipeline

```
[User Uploads MSME PDF]
         │
         ▼
[FastAPI /api/documents/upload]
         │
         ├── 1. Saves PDF to uploads/
         ▼
[PyMuPDF (fitz) Text Extraction]
         │
         ├── Extracted text >= 50 characters?
         ├── YES ──► Text ready for LLM
         └── NO  ──► [Tesseract OCR + Pillow Image Fallback] ──► Text ready
                                  │
                                  ▼
        [OpenAI LLM Extraction (gpt-4o-mini / Heuristic Engine)]
                                  │
                                  ▼
        [Pydantic Schema Validation: SustainabilityDocumentExtraction]
                                  │
                                  ▼
        [SQLite Persistence: Documents & Sustainability Metrics]
                                  │
                                  ▼
[React + Vite + Tailwind CSS Web Dashboard]
  • Executive KPI Overview: Total kWh, Scope 1 & 2 GHG (tCO2e), Water (kL), Waste (kg)
  • Real-Time Extraction Status & PyMuPDF vs OCR Badges
  • Interactive Document Repository with Search & Filters
  • Granular Document Modal: Sustainability Metrics, Line Items, JSON Viewer, Raw Text
  • One-Click Sample Generators for immediate testing without finding a PDF!
```

---

## Project Structure

```
sensible/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                     # FastAPI entrypoint, CORS, lifespan DB init
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes.py               # Upload, list, detail, stats, sample seed endpoints
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── base.py                 # DeclarativeBase
│   │   │   └── session.py              # SQLite engine & session factory
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── document.py             # SQLAlchemy Document model
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── document.py             # Document API request/response schemas
│   │   │   └── extraction.py           # Pydantic schemas for MSME Sustainability
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── pdf_service.py          # PyMuPDF page-by-page text extraction
│   │   │   ├── ocr_service.py          # Tesseract OCR fallback with Pillow pre-processing
│   │   │   ├── llm_service.py          # OpenAI API integration + Heuristic fallback parser
│   │   │   └── extraction_service.py   # End-to-end pipeline coordinator
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── helpers.py              # Sanitization, unique naming, file formatting
│   │       └── sample_generator.py     # PDF generator for testing (Electricity, ESG, Scanned)
│   ├── uploads/                        # Uploaded & generated PDFs
│   ├── requirements.txt                # Python dependencies
│   └── .env.example                    # Backend environment template
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.jsx              # System status, health pulse, LLM & OCR badges
│   │   │   ├── StatsCards.jsx          # Aggregate sustainability KPI cards
│   │   │   ├── DocumentUpload.jsx      # Drag & drop upload + sample document triggers
│   │   │   ├── DocumentList.jsx        # Document table with filters, search, & actions
│   │   │   └── DocumentDetailModal.jsx # Multi-tab sustainability details & JSON exporter
│   │   ├── pages/
│   │   │   └── Dashboard.jsx           # Main MSME Sustainability Dashboard
│   │   ├── services/
│   │   │   └── api.js                  # Axios client for FastAPI backend
│   │   ├── App.jsx                     # Root React component
│   │   ├── main.jsx                    # React entrypoint
│   │   └── index.css                   # Tailwind styling & glassmorphism
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── .env.example
├── .env.example
├── .gitignore
└── README.md
```

---

## Prerequisites

- **Python**: 3.11 or higher
- **Node.js**: v18 or higher (v20+ recommended) & npm
- **Tesseract OCR**: (Optional for scanned image PDFs; fallback is enabled)
  - Ubuntu/Debian: `sudo apt-get install tesseract-ocr`
  - macOS: `brew install tesseract`

---

## Installation

### 1. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# (Optional) Setup environment variables
cp .env.example .env
```

If you have an OpenAI API key, add it to `backend/.env`:
```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```
> *Note: If `OPENAI_API_KEY` is not provided, the backend seamlessly runs with its built-in intelligent heuristic sustainability parser, enabling instant offline testing.*

### 2. Frontend Setup

```bash
cd frontend

# Install node dependencies
npm install

# (Optional) Setup frontend environment variables
cp .env.example .env
```

---

## Running the Application

### 1. Start the Backend Server

```bash
# From the repository root (or backend folder with venv activated):
cd backend
source venv/bin/activate
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
- **Backend API URL**: `http://localhost:8000`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`
- **System Health Check**: `http://localhost:8000/api/health`

### 2. Start the Frontend Development Server

```bash
# In a separate terminal:
cd frontend
npm run dev
```
- **Web Dashboard URL**: `http://localhost:5173`

---

## Key Features & End-to-End Workflow

1. **Upload or Sample Document Generation**:
   - Drag & drop any industrial sustainability PDF.
   - Or click **"Quick Test Samples"** on the UI to test:
     - **Industrial Electricity Bill** (Tests clean text extraction via PyMuPDF).
     - **MSME ESG Audit Report** (Tests multi-page sustainability report parsing).
     - **Scanned Waste Manifest** (Tests Tesseract OCR fallback on image-only PDFs).
2. **Text Extraction & OCR Fallback**:
   - PyMuPDF extracts text at high performance.
   - If characters extracted are `< 50` or scanned, the system automatically falls back to Tesseract OCR with Pillow sharpening.
3. **Structured AI Extraction**:
   - Extracts Company details, Reporting period, Energy metrics (kWh, peak demand, power factor, renewable solar), GHG Scope 1 & 2 emissions (tCO2e), Water consumption & recycling (kL), Waste diversion (kg), Certifications (ISO 14001, 50001), Line items, and Executive Summary.
4. **Pydantic Validation**:
   - Enforces types, bounds, and defaults on all extracted JSON.
5. **Interactive Dashboard**:
   - Aggregates real-time portfolio energy, carbon footprint, water, and circular waste.
   - View extracted metrics, copy structured JSON, view raw text, or download `.json` files.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Diagnostic status (LLM key, OCR availability) |
| `POST` | `/api/documents/upload` | Upload PDF and trigger extraction |
| `POST` | `/api/documents/{id}/process` | Reprocess document (with optional `force_ocr`) |
| `GET` | `/api/documents` | List documents with pagination, search, and filters |
| `GET` | `/api/documents/{id}` | Get detailed extracted document |
| `DELETE` | `/api/documents/{id}` | Delete document and remove file from disk |
| `GET` | `/api/documents/{id}/download-json` | Export structured data as a `.json` file |
| `GET` | `/api/stats` | Aggregated MSME sustainability portfolio KPIs |
| `POST` | `/api/documents/sample-seed` | Generate and process test MSME PDF (`electricity`, `esg`, `scanned`) |

---

## What Remains to Implement (Future Enhancements)

While this MVP is fully working end-to-end, future production upgrades include:
1. **User Authentication & Multi-Tenancy**: JWT / OAuth2 authentication, MSME organization accounts, and role-based access control (RBAC).
2. **Cloud Storage**: Transitioning from local filesystem (`uploads/`) to S3 / Google Cloud Storage with presigned URLs.
3. **Asynchronous Task Queue**: Celery / Redis or AWS SQS for processing large batches of hundreds of PDFs concurrently.
4. **Enterprise Database**: Migration from SQLite to PostgreSQL with pgvector for semantic search over sustainability clauses.
5. **Document Visual Bounding Boxes**: Visual highlighting of extracted key-value pairs directly overlaid on the PDF canvas.
6. **Carbon Accounting Integration**: Automated BRSR / GHG Protocol Scope 1, 2, 3 export to national compliance portals.
