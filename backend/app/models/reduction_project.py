"""
models/reduction_project.py — SQLAlchemy Models for Carbon Reduction Projects & Audit Trail (Step 16).

Tracks business reduction projects linked to identified opportunities, including status history, user targets, and observed accounting baselines.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, Text, DateTime, Date, ForeignKey
from backend.app.database.base import Base


class ReductionProject(Base):
    __tablename__ = "reduction_projects"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_code = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False, index=True)
    scope = Column(String(50), nullable=True, index=True)
    opportunity_id = Column(Integer, ForeignKey("reduction_opportunities.id"), nullable=True, index=True)
    activity_type = Column(String(100), nullable=True, index=True)
    status = Column(String(50), nullable=False, default="PLANNED", index=True)  # PLANNED, IN_PROGRESS, ON_HOLD, COMPLETED, CANCELLED
    owner = Column(String(150), nullable=True)

    start_date = Column(DateTime, nullable=True)
    target_date = Column(DateTime, nullable=True)

    # Reference Footprint (Accounting Baseline Reference)
    baseline_period = Column(String(50), nullable=True)
    baseline_co2e = Column(Numeric(24, 6), nullable=True)
    baseline_co2e_unit = Column(String(50), default="kgCO2e", nullable=False)

    # User-defined Target (Non-fabricated)
    target_description = Column(Text, nullable=True)

    # Observed Accounting Results (Post-implementation, nullable)
    actual_post_project_co2e = Column(Numeric(24, 6), nullable=True)
    actual_post_project_unit = Column(String(50), default="kgCO2e", nullable=False)

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ReductionProjectEvent(Base):
    """
    Immutable audit trail recording state changes and milestones for reduction projects.
    """
    __tablename__ = "reduction_project_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("reduction_projects.id"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)  # CREATED, STATUS_CHANGE, TARGET_SET, ACTUAL_RECORDED, NOTE_ADDED
    previous_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
