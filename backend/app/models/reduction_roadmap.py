"""
models/reduction_roadmap.py — SQLAlchemy Models for Personalized Reduction Roadmap Engine (Step 22B).

Defines persistent models for user reduction targets, structured phased roadmap items,
and immutable event audit trails.
"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Numeric, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database.base import Base
from backend.app.config.reduction_roadmap import (
    REDUCTION_ROADMAP_VERSION,
    ROADMAP_STATUS_DRAFT,
    ITEM_STATUS_NOT_STARTED,
    CONTRIBUTION_STATUS_NOT_QUANTIFIED,
    TARGET_FEASIBILITY_UNKNOWN,
    PRIORITY_MEDIUM,
    EFFORT_MEDIUM,
)


class ReductionRoadmap(Base):
    """
    User-defined or portfolio reduction target and corresponding structured action roadmap.
    """
    __tablename__ = "reduction_roadmaps"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    roadmap_code = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)

    # Scoping & Document Linkage
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True)
    reporting_year = Column(Integer, nullable=True, index=True)

    # Baseline Parameters (Sourced from POSTED CarbonLedgerEntry)
    baseline_period = Column(String(50), nullable=False)
    baseline_emissions_kgco2e = Column(Numeric(24, 6), nullable=False, default=0.0)
    baseline_emissions_tco2e = Column(Numeric(18, 6), nullable=False, default=0.0)

    # Target Configuration (Deterministic Arithmetic)
    target_reduction_percent = Column(Numeric(6, 2), nullable=False)
    target_year = Column(Integer, nullable=True)
    target_period = Column(String(50), nullable=True)

    # Derived Target Values
    target_emissions_kgco2e = Column(Numeric(24, 6), nullable=False, default=0.0)
    target_emissions_tco2e = Column(Numeric(18, 6), nullable=False, default=0.0)
    reduction_gap_kgco2e = Column(Numeric(24, 6), nullable=False, default=0.0)
    reduction_gap_tco2e = Column(Numeric(18, 6), nullable=False, default=0.0)

    # Target Feasibility & Status
    target_status = Column(String(50), nullable=False, default=TARGET_FEASIBILITY_UNKNOWN)
    status = Column(String(50), nullable=False, default=ROADMAP_STATUS_DRAFT, index=True)
    confidence = Column(String(50), nullable=False, default="MEDIUM")
    feasibility_explanation = Column(Text, nullable=True)

    # Versioning & Audit
    roadmap_version = Column(String(50), nullable=False, default=REDUCTION_ROADMAP_VERSION)
    calculation_version = Column(String(50), nullable=False, default="1.0")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    items = relationship(
        "ReductionRoadmapItem",
        back_populates="roadmap",
        cascade="all, delete-orphan",
        order_by="ReductionRoadmapItem.sequence",
    )
    events = relationship(
        "ReductionRoadmapEvent",
        back_populates="roadmap",
        cascade="all, delete-orphan",
        order_by="ReductionRoadmapEvent.created_at",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "roadmap_code": self.roadmap_code,
            "name": self.name,
            "document_id": self.document_id,
            "reporting_year": self.reporting_year,
            "baseline_period": self.baseline_period,
            "baseline_emissions_kgco2e": float(self.baseline_emissions_kgco2e) if self.baseline_emissions_kgco2e is not None else 0.0,
            "baseline_emissions_tco2e": float(self.baseline_emissions_tco2e) if self.baseline_emissions_tco2e is not None else 0.0,
            "target_reduction_percent": float(self.target_reduction_percent) if self.target_reduction_percent is not None else 0.0,
            "target_year": self.target_year,
            "target_period": self.target_period,
            "target_emissions_kgco2e": float(self.target_emissions_kgco2e) if self.target_emissions_kgco2e is not None else 0.0,
            "target_emissions_tco2e": float(self.target_emissions_tco2e) if self.target_emissions_tco2e is not None else 0.0,
            "reduction_gap_kgco2e": float(self.reduction_gap_kgco2e) if self.reduction_gap_kgco2e is not None else 0.0,
            "reduction_gap_tco2e": float(self.reduction_gap_tco2e) if self.reduction_gap_tco2e is not None else 0.0,
            "target_status": self.target_status,
            "status": self.status,
            "confidence": self.confidence,
            "feasibility_explanation": self.feasibility_explanation,
            "roadmap_version": self.roadmap_version,
            "calculation_version": self.calculation_version,
            "items_count": len(self.items) if self.items else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ReductionRoadmapItem(Base):
    """
    Individual structured action item within a reduction roadmap.
    """
    __tablename__ = "reduction_roadmap_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    roadmap_id = Column(Integer, ForeignKey("reduction_roadmaps.id", ondelete="CASCADE"), nullable=False, index=True)

    # Lineage to intelligence layers
    priority_id = Column(Integer, ForeignKey("reduction_priorities.id", ondelete="SET NULL"), nullable=True, index=True)
    opportunity_id = Column(Integer, ForeignKey("reduction_opportunities.id", ondelete="SET NULL"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("reduction_projects.id", ondelete="SET NULL"), nullable=True, index=True)

    sequence = Column(Integer, nullable=False, index=True)
    phase = Column(String(50), nullable=False, index=True)  # PHASE_1_FOUNDATION, PHASE_2_ACTION, etc.
    title = Column(String(255), nullable=False)
    action_type = Column(String(50), nullable=False, index=True)
    category = Column(String(50), nullable=True)
    scope = Column(String(50), nullable=True)

    # Source emissions context (from ledger/priority)
    current_emissions_kgco2e = Column(Numeric(24, 6), nullable=True)
    current_emissions_tco2e = Column(Numeric(18, 6), nullable=True)

    # Contribution towards target (Only populated when verified data exists, otherwise NULL)
    target_contribution_kgco2e = Column(Numeric(24, 6), nullable=True)
    target_contribution_tco2e = Column(Numeric(18, 6), nullable=True)
    contribution_status = Column(String(50), nullable=False, default=CONTRIBUTION_STATUS_NOT_QUANTIFIED)

    priority = Column(String(50), nullable=False, default=PRIORITY_MEDIUM)
    effort_level = Column(String(50), nullable=False, default=EFFORT_MEDIUM)

    # Planning Context & Dependencies
    dependency = Column(Text, nullable=True)
    prerequisite = Column(Text, nullable=True)
    required_data = Column(Text, nullable=True)
    measurement_method = Column(Text, nullable=True)
    verification_method = Column(Text, nullable=True)

    status = Column(String(50), nullable=False, default=ITEM_STATUS_NOT_STARTED, index=True)

    # Provenance & Limitations
    evidence_reference = Column(Text, nullable=True)
    reason = Column(Text, nullable=True)
    limitation = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    roadmap = relationship("ReductionRoadmap", back_populates="items")

    def to_dict(self):
        return {
            "id": self.id,
            "roadmap_id": self.roadmap_id,
            "priority_id": self.priority_id,
            "opportunity_id": self.opportunity_id,
            "project_id": self.project_id,
            "sequence": self.sequence,
            "phase": self.phase,
            "title": self.title,
            "action_type": self.action_type,
            "category": self.category,
            "scope": self.scope,
            "current_emissions_kgco2e": float(self.current_emissions_kgco2e) if self.current_emissions_kgco2e is not None else None,
            "current_emissions_tco2e": float(self.current_emissions_tco2e) if self.current_emissions_tco2e is not None else None,
            "target_contribution_kgco2e": float(self.target_contribution_kgco2e) if self.target_contribution_kgco2e is not None else None,
            "target_contribution_tco2e": float(self.target_contribution_tco2e) if self.target_contribution_tco2e is not None else None,
            "contribution_status": self.contribution_status,
            "priority": self.priority,
            "effort_level": self.effort_level,
            "dependency": self.dependency,
            "prerequisite": self.prerequisite,
            "required_data": self.required_data,
            "measurement_method": self.measurement_method,
            "verification_method": self.verification_method,
            "status": self.status,
            "evidence_reference": self.evidence_reference,
            "reason": self.reason,
            "limitation": self.limitation,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ReductionRoadmapEvent(Base):
    """
    Immutable audit record tracking status transitions and milestones in a roadmap.
    """
    __tablename__ = "reduction_roadmap_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    roadmap_id = Column(Integer, ForeignKey("reduction_roadmaps.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    old_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=True)
    actor = Column(String(100), default="SYSTEM")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    roadmap = relationship("ReductionRoadmap", back_populates="events")

    def to_dict(self):
        return {
            "id": self.id,
            "roadmap_id": self.roadmap_id,
            "event_type": self.event_type,
            "old_status": self.old_status,
            "new_status": self.new_status,
            "actor": self.actor,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
