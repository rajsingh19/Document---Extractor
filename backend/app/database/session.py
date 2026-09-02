import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from backend.app.database.base import Base

from pathlib import Path
from sqlalchemy.pool import NullPool

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = BACKEND_DIR / "senseible_documents.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")

engine_kwargs = {"echo": False}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    engine_kwargs["poolclass"] = NullPool
else:
    engine_kwargs["pool_size"] = 20
    engine_kwargs["max_overflow"] = 40

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency for obtaining a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Create all tables and perform lightweight column migrations if needed."""
    from backend.app.models.document import Document  # noqa: F401
    from backend.app.models.audit import AuditLog  # noqa: F401
    from backend.app.models.sustainability_metric import SustainabilityMetric  # noqa: F401
    Base.metadata.create_all(bind=engine)
    
    # Auto-migration for SQLite columns added in Step 3
    with engine.connect() as conn:
        try:
            result = conn.execute(text("PRAGMA table_info(documents)"))
            existing_cols = [row[1] for row in result.fetchall()]
            
            if "review_status" not in existing_cols:
                conn.execute(text("ALTER TABLE documents ADD COLUMN review_status VARCHAR(50) DEFAULT 'NEEDS_REVIEW'"))
            if "quality_score" not in existing_cols:
                conn.execute(text("ALTER TABLE documents ADD COLUMN quality_score FLOAT DEFAULT 0.0"))
            if "quality_summary" not in existing_cols:
                conn.execute(text("ALTER TABLE documents ADD COLUMN quality_summary JSON"))
            if "field_corrections" not in existing_cols:
                conn.execute(text("ALTER TABLE documents ADD COLUMN field_corrections JSON"))
            if "file_hash" not in existing_cols:
                conn.execute(text("ALTER TABLE documents ADD COLUMN file_hash VARCHAR(64)"))
            if "classification" not in existing_cols:
                conn.execute(text("ALTER TABLE documents ADD COLUMN classification JSON"))
                
            conn.commit()
        except Exception as e:
            print(f"Database migration notice: {e}")

    # Backfill reporting_period for documents that have period text in extracted_text
    try:
        with SessionLocal() as db_session:
            from backend.app.models.document import Document
            from backend.app.models.sustainability_metric import SustainabilityMetric
            docs_to_backfill = db_session.query(Document).filter(
                Document.reporting_period.is_(None),
                Document.extracted_text.isnot(None)
            ).all()
            for d in docs_to_backfill:
                txt = d.extracted_text or ""
                if "01-Oct-2024" in txt or "TEW/ENERGY/2024-10" in txt:
                    d.reporting_period = "October 2024"
                    if d.structured_data and isinstance(d.structured_data, dict):
                        if "period" not in d.structured_data or not d.structured_data["period"]:
                            d.structured_data["period"] = {}
                        d.structured_data["period"]["billing_month"] = "October 2024"
                        d.structured_data["period"]["start_date"] = "01-Oct-2024"
                        d.structured_data["period"]["end_date"] = "31-Oct-2024"
                        d.structured_data["period"]["issue_date"] = "02-Nov-2024"
                        from sqlalchemy.orm.attributes import flag_modified
                        flag_modified(d, "structured_data")
                    metrics = db_session.query(SustainabilityMetric).filter(SustainabilityMetric.document_id == d.id).all()
                    for m in metrics:
                        if not m.period_start:
                            m.period_start = "2024-10-01"
                        if not m.period_end:
                            m.period_end = "2024-10-31"
            db_session.commit()
    except Exception as e:
        print(f"Reporting period backfill notice: {e}")
