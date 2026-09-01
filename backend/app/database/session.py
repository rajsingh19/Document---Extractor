import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from backend.app.database.base import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./senseible_documents.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=False
)

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
