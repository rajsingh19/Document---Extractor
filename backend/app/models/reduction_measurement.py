"""
models/reduction_measurement.py — SQLAlchemy Models for Reduction Measurement & Verification (Step 17).

Stores deterministic before-and-after accounting measurements derived strictly from POSTED CarbonLedgerEntry records.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, Text, DateTime, ForeignKey
from backend.app.database.base import Base


class ReductionMeasurement(Base):
    __tablename__ = "reduction_measurements"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("reduction_projects.id"), nullable=False, index=True)

    # Measurement Scope Configuration
    measurement_scope_type = Column(String(50), default="TOTAL", nullable=False)  # TOTAL, SCOPE, CATEGORY, ACTIVITY
    measurement_scope = Column(String(50), nullable=True)  # SCOPE_1, SCOPE_2, SCOPE_3
    measurement_category = Column(String(50), nullable=True)  # ENERGY, FUEL, TRANSPORT, etc.
    measurement_activity_type = Column(String(100), nullable=True)

    # Comparison Periods
    reference_period = Column(String(50), nullable=False, index=True)  # e.g., '2024-10'
    measurement_period = Column(String(50), nullable=False, index=True)  # e.g., '2025-10'
    reference_year = Column(Integer, nullable=True)
    measurement_year = Column(Integer, nullable=True)

    # Footprint Values (Stored in Decimal kgCO2e, displayed in tCO2e)
    reference_co2e = Column(Numeric(24, 6), nullable=True)
    measurement_co2e = Column(Numeric(24, 6), nullable=True)
    reference_co2e_unit = Column(String(50), default="kgCO2e", nullable=False)
    measurement_co2e_unit = Column(String(50), default="kgCO2e", nullable=False)

    # Observed Accounting Result
    observed_change = Column(Numeric(24, 6), nullable=True)  # measurement - reference
    observed_change_percentage = Column(Numeric(10, 4), nullable=True)  # ((meas - ref) / ref) * 100

    # Status Fields
    measurement_status = Column(String(50), default="DRAFT", nullable=False, index=True)  # DRAFT, READY, MEASURED, NEEDS_REVIEW, FINALIZED
    evidence_status = Column(String(50), default="NONE", nullable=False)  # NONE, ACCOUNTING_DATA, DOCUMENT_EVIDENCE, MULTI_SOURCE
    verification_status = Column(String(50), default="NOT_SUBMITTED", nullable=False, index=True)  # NOT_SUBMITTED, INTERNAL_REVIEW, ACCEPTED, REJECTED, EXTERNAL_VERIFICATION_PENDING, EXTERNALLY_VERIFIED

    # Methodology & Guardrail Context
    methodology_note = Column(Text, nullable=True)
    limitations = Column(
        Text,
        default=(
            "This comparison shows an observed change in accounting data between the selected periods. "
            "It does not establish that the reduction project caused the change."
        ),
        nullable=False,
    )
    measurement_version = Column(Integer, default=1, nullable=False)
    calculated_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ReductionMeasurementEvent(Base):
    """
    Immutable audit log of all measurement lifecycle events and verification decisions.
    """
    __tablename__ = "reduction_measurement_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    measurement_id = Column(Integer, ForeignKey("reduction_measurements.id"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)  # CREATED, MEASURED, STATUS_CHANGE, VERIFICATION_SUBMITTED, VERIFICATION_ACCEPTED, VERIFICATION_REJECTED
    previous_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
