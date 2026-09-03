"""
models/green_finance.py — Database Models for Green Finance Readiness Engine (Step 19).

Models for assessing business application readiness for green-finance review.
Measures evidence completeness, carbon accounting posture, reduction projects, verification, and reporting.

CRITICAL PRODUCT BOUNDARIES:
- Does NOT approve/reject loans or predict loan approval.
- Does NOT calculate credit scores or creditworthiness.
- Does NOT calculate loan amounts, interest rates, or default probabilities.
- Does NOT perform financial underwriting.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database.base import Base


class GreenFinanceAssessment(Base):
    __tablename__ = "green_finance_assessments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    assessment_code = Column(String(100), unique=True, nullable=False, index=True)
    business_name = Column(String(255), nullable=False, default="TARA ENGINEERING WORKS")
    reporting_period = Column(String(100), nullable=False, index=True)
    reporting_year = Column(Integer, nullable=True, index=True)
    assessment_version = Column(String(50), nullable=False, default="1.0")

    # Numeric score (0.0 to 100.0)
    overall_readiness_score = Column(Float, nullable=False, default=0.0)
    
    # Readiness band: NOT_READY (0-39), PARTIALLY_READY (40-69), READY_FOR_REVIEW (70-100)
    readiness_band = Column(String(50), nullable=False, default="NOT_READY", index=True)
    
    # Status: DRAFT, GENERATED, NEEDS_REVIEW, READY_FOR_APPLICATION, FINALIZED
    status = Column(String(50), nullable=False, default="DRAFT", index=True)

    notes = Column(Text, nullable=True)
    generated_at = Column(DateTime, nullable=True)
    finalized_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    requirements = relationship(
        "GreenFinanceRequirement",
        backref="assessment",
        cascade="all, delete-orphan",
        order_by="GreenFinanceRequirement.id",
    )
    events = relationship(
        "GreenFinanceAssessmentEvent",
        backref="assessment",
        cascade="all, delete-orphan",
        order_by="GreenFinanceAssessmentEvent.created_at",
    )


class GreenFinanceRequirement(Base):
    __tablename__ = "green_finance_requirements"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    assessment_id = Column(Integer, ForeignKey("green_finance_assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    requirement_code = Column(String(100), nullable=False, index=True)
    requirement_name = Column(String(255), nullable=False)
    
    # Category: DATA_READINESS, CARBON_ACCOUNTING, EVIDENCE, EMISSIONS_DATA, REDUCTION_PLAN,
    # REDUCTION_PROJECTS, MEASUREMENT_VERIFICATION, REPORTING, GOVERNANCE, FINANCE_DOCUMENT_READINESS
    category = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    weight = Column(Float, nullable=False, default=1.0)
    required = Column(Boolean, nullable=False, default=True)

    # Status: SUPPORTED, PARTIALLY_SUPPORTED, MISSING, NEEDS_REVIEW, NOT_APPLICABLE
    status = Column(String(50), nullable=False, default="MISSING", index=True)
    reason = Column(Text, nullable=True)

    source_type = Column(String(100), nullable=True)
    source_id = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship to evidence records
    evidence_items = relationship(
        "GreenFinanceEvidence",
        backref="requirement",
        cascade="all, delete-orphan",
        order_by="GreenFinanceEvidence.id",
    )


class GreenFinanceEvidence(Base):
    __tablename__ = "green_finance_evidence"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    assessment_id = Column(Integer, ForeignKey("green_finance_assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    requirement_id = Column(Integer, ForeignKey("green_finance_requirements.id", ondelete="CASCADE"), nullable=False, index=True)

    source_type = Column(String(100), nullable=True)  # DOCUMENT, CARBON_LEDGER, ACTIVITY_DATA, METRIC, PROJECT, REPORT
    source_id = Column(Integer, nullable=True)
    document_id = Column(Integer, nullable=True, index=True)
    source_field = Column(String(100), nullable=True)
    source_text = Column(Text, nullable=True)
    reporting_period = Column(String(100), nullable=True)
    page_number = Column(Integer, nullable=True)

    evidence_status = Column(String(50), nullable=False, default="VERIFIED")  # VERIFIED, UNVERIFIED, NEEDS_REVIEW
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class GreenFinanceAssessmentEvent(Base):
    __tablename__ = "green_finance_assessment_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    assessment_id = Column(Integer, ForeignKey("green_finance_assessments.id", ondelete="CASCADE"), nullable=False, index=True)

    event_type = Column(String(100), nullable=False)  # CREATED, GENERATED, STATUS_CHANGE, USER_OVERRIDE, FINALIZED
    previous_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    actor = Column(String(100), nullable=False, default="SYSTEM")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
