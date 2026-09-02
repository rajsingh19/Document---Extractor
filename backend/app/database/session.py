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
