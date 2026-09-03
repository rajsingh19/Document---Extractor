"""
models/verification_record.py — SQLAlchemy Model for External & Internal Verification Records (Step 17).

Stores verification workflow metadata, auditor/verifier provenance, and verification decisions.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey
from backend.app.database.base import Base


class VerificationRecord(Base):
    __tablename__ = "verification_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("reduction_projects.id"), nullable=False, index=True)
    measurement_id = Column(Integer, ForeignKey("reduction_measurements.id"), nullable=False, unique=True, index=True)

    verifier_name = Column(String(150), nullable=True)
    verifier_organization = Column(String(200), nullable=True)
    verification_reference = Column(String(150), nullable=True)
    verification_date = Column(DateTime, nullable=True)
    verification_notes = Column(Text, nullable=True)
    verification_status = Column(String(50), default="NOT_SUBMITTED", nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
