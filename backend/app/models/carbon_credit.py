"""
models/carbon_credit.py — Database Models for Carbon Credit Readiness & Project Eligibility Assessment Engine (Step 20).

Models for assessing whether an existing reduction/removal project has sufficient:
- project documentation
- baseline information
- activity data
- emissions accounting
- reduction evidence
- monitoring structure
- measurement history
- verification readiness
- reporting structure
- supporting evidence
to BEGIN a carbon-credit certification / project-development pathway.

CRITICAL PRODUCT BOUNDARIES:
- Carbon footprint != carbon credit.
- Does NOT issue, create, sell, or predict tradable carbon credits.
- Does NOT predict market values, revenue, or carbon credit prices.
- Does NOT guarantee additionality, permanence, or certification.
- Does NOT fabricate methodology requirements or verification records.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Numeric, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database.base import Base


class CarbonCreditAssessment(Base):
    """
    Project-scoped Carbon Credit Readiness Assessment entity.
    Must be tied to an existing ReductionProject.
    """
    __tablename__ = "carbon_credit_assessments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    assessment_code = Column(String(100), unique=True, nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("reduction_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    project_name = Column(String(255), nullable=False)
    reporting_period = Column(String(100), nullable=False, index=True)
    assessment_version = Column(String(50), nullable=False, default="1.0")

    # Numeric score (0.00 to 100.00)
    overall_readiness_score = Column(Numeric(10, 2), nullable=False, default=0.0)

    # Readiness band: NOT_READY (0-39), PARTIALLY_READY (40-69), READY_FOR_METHODOLOGY_REVIEW (70-100)
    readiness_band = Column(String(50), nullable=False, default="NOT_READY", index=True)

    # Status: DRAFT, GENERATED, NEEDS_REVIEW, READY_FOR_METHODOLOGY_REVIEW, FINALIZED
    status = Column(String(50), nullable=False, default="DRAFT", index=True)

    # Methodology & Standard Status: READY, PARTIAL, MISSING, NEEDS_REVIEW
    methodology_status = Column(String(50), nullable=False, default="NEEDS_REVIEW", index=True)
    standard_status = Column(String(50), nullable=False, default="NEEDS_REVIEW", index=True)

    notes = Column(Text, nullable=True)
    generated_at = Column(DateTime, nullable=True)
    finalized_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    requirements = relationship(
        "CarbonCreditRequirement",
        backref="assessment",
        cascade="all, delete-orphan",
        order_by="CarbonCreditRequirement.id",
    )
    evidence_items = relationship(
        "CarbonCreditEvidence",
        backref="assessment",
        cascade="all, delete-orphan",
        order_by="CarbonCreditEvidence.id",
    )
    events = relationship(
        "CarbonCreditAssessmentEvent",
        backref="assessment",
        cascade="all, delete-orphan",
        order_by="CarbonCreditAssessmentEvent.created_at",
    )


class CarbonCreditRequirement(Base):
    """
    Individual readiness requirement / criteria evaluated across 15 dimensions.
    """
    __tablename__ = "carbon_credit_requirements"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    assessment_id = Column(Integer, ForeignKey("carbon_credit_assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    requirement_code = Column(String(100), nullable=False, index=True)
    requirement_name = Column(String(255), nullable=False)

    # Category: PROJECT_DEFINITION, BASELINE, ACTIVITY_DATA, CARBON_ACCOUNTING, EMISSION_FACTORS,
    # REDUCTION_EVIDENCE, ADDITIONALITY_READINESS, MONITORING, MEASUREMENT, VERIFICATION,
    # EVIDENCE, REPORTING, METHODOLOGY_READINESS, STANDARD_READINESS, GOVERNANCE
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
        "CarbonCreditEvidence",
        backref="requirement",
        cascade="all, delete-orphan",
        order_by="CarbonCreditEvidence.id",
    )


class CarbonCreditEvidence(Base):
    """
    Audit provenance and source lineage record for Carbon Credit readiness requirements.
    Every evidence item preserves provenance. No fabricated evidence.
    """
    __tablename__ = "carbon_credit_evidence"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    assessment_id = Column(Integer, ForeignKey("carbon_credit_assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    requirement_id = Column(Integer, ForeignKey("carbon_credit_requirements.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(Integer, nullable=False, index=True)

    source_type = Column(String(100), nullable=True)  # DOCUMENT, CARBON_LEDGER, ACTIVITY_DATA, EMISSION_FACTOR, MEASUREMENT, VERIFICATION_RECORD, COMPLIANCE_REPORT, REDUCTION_OPPORTUNITY, REDUCTION_PROJECT
    source_id = Column(Integer, nullable=True)
    document_id = Column(Integer, nullable=True, index=True)
    source_field = Column(String(100), nullable=True)
    source_text = Column(Text, nullable=True)
    reporting_period = Column(String(100), nullable=True)
    page_number = Column(Integer, nullable=True)

    evidence_status = Column(String(50), nullable=False, default="VERIFIED")  # VERIFIED, UNVERIFIED, NEEDS_REVIEW
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class CarbonCreditAssessmentEvent(Base):
    """
    Immutable audit trail for carbon credit assessment lifecycle.
    """
    __tablename__ = "carbon_credit_assessment_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    assessment_id = Column(Integer, ForeignKey("carbon_credit_assessments.id", ondelete="CASCADE"), nullable=False, index=True)

    event_type = Column(String(100), nullable=False)  # CREATED, GENERATED, STATUS_CHANGE, USER_OVERRIDE, FINALIZED
    previous_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    actor = Column(String(100), nullable=False, default="SYSTEM")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
