"""
models/reduction_intelligence.py — SQLAlchemy Model for Reduction Opportunity Intelligence Engine (Step 22A).

Stores deterministic, grounded reduction priorities derived from POSTED CarbonLedgerEntry history,
historical trends, Step 21 predictive forecasts, ReductionOpportunities, and ReductionProjects.

CRITICAL PRODUCT BOUNDARIES:
- Never determines emissions, scores, or rankings via LLM.
- Strictly uses Decimal/Numeric for all numerical values.
- Never mutates accounting truth or historical ledger entries.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, Text, DateTime, ForeignKey
from backend.app.database.base import Base
from backend.app.config.reduction_intelligence import REDUCTION_INTELLIGENCE_VERSION


class ReductionPriority(Base):
    """
    Persisted record of a deterministic reduction priority.
    """
    __tablename__ = "reduction_priorities"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    priority_code = Column(String(100), unique=True, nullable=False, index=True)

    # Scoping & Linkages
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True)
    opportunity_id = Column(Integer, ForeignKey("reduction_opportunities.id", ondelete="SET NULL"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("reduction_projects.id", ondelete="SET NULL"), nullable=True, index=True)

    # Classification & Context
    scope = Column(String(50), nullable=True, index=True)  # SCOPE_1, SCOPE_2, SCOPE_3, ALL
    category = Column(String(100), nullable=True, index=True)  # ENERGY, FUEL, TRANSPORT, WATER, WASTE, DATA_QUALITY
    activity_type = Column(String(100), nullable=True, index=True)

    # Ranking & Priority
    priority_rank = Column(Integer, nullable=True, index=True)
    priority_score = Column(Numeric(6, 2), nullable=False, default=0.0)  # 0.00 to 100.00
    priority_level = Column(String(50), nullable=False, index=True)  # CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL

    # Transparent Signal Scores (0 - max tier)
    impact_score = Column(Numeric(6, 2), nullable=False, default=0.0)
    trend_score = Column(Numeric(6, 2), nullable=False, default=0.0)
    forecast_score = Column(Numeric(6, 2), nullable=False, default=0.0)
    persistence_score = Column(Numeric(6, 2), nullable=False, default=0.0)
    actionability_score = Column(Numeric(6, 2), nullable=False, default=0.0)
    data_quality_score = Column(Numeric(6, 2), nullable=False, default=0.0)
    blocker_score = Column(Numeric(6, 2), nullable=False, default=0.0)

    # Content & Explanation
    title = Column(String(255), nullable=False)
    reason = Column(Text, nullable=False)

    # Quantitative Grounded Values (Strict Decimal precision)
    current_emissions_kgco2e = Column(Numeric(24, 6), nullable=False, default=0.0)
    current_emissions_tco2e = Column(Numeric(18, 6), nullable=False, default=0.0)
    previous_emissions_kgco2e = Column(Numeric(24, 6), nullable=True)
    change_percent = Column(Numeric(10, 4), nullable=True)
    forecast_emissions_kgco2e = Column(Numeric(24, 6), nullable=True)

    # Traceability & Provenance Evidence
    source_reference = Column(String(255), nullable=True)
    evidence_reference = Column(Text, nullable=True)
    calculation_version = Column(String(50), default=REDUCTION_INTELLIGENCE_VERSION, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "priority_code": self.priority_code,
            "document_id": self.document_id,
            "opportunity_id": self.opportunity_id,
            "project_id": self.project_id,
            "scope": self.scope,
            "category": self.category,
            "activity_type": self.activity_type,
            "priority_rank": self.priority_rank,
            "priority_score": float(self.priority_score) if self.priority_score is not None else 0.0,
            "priority_level": self.priority_level,
            "impact_score": float(self.impact_score) if self.impact_score is not None else 0.0,
            "trend_score": float(self.trend_score) if self.trend_score is not None else 0.0,
            "forecast_score": float(self.forecast_score) if self.forecast_score is not None else 0.0,
            "persistence_score": float(self.persistence_score) if self.persistence_score is not None else 0.0,
            "actionability_score": float(self.actionability_score) if self.actionability_score is not None else 0.0,
            "data_quality_score": float(self.data_quality_score) if self.data_quality_score is not None else 0.0,
            "blocker_score": float(self.blocker_score) if self.blocker_score is not None else 0.0,
            "title": self.title,
            "reason": self.reason,
            "current_emissions_kgco2e": float(self.current_emissions_kgco2e) if self.current_emissions_kgco2e is not None else 0.0,
            "current_emissions_tco2e": float(self.current_emissions_tco2e) if self.current_emissions_tco2e is not None else 0.0,
            "previous_emissions_kgco2e": float(self.previous_emissions_kgco2e) if self.previous_emissions_kgco2e is not None else None,
            "change_percent": float(self.change_percent) if self.change_percent is not None else None,
            "forecast_emissions_kgco2e": float(self.forecast_emissions_kgco2e) if self.forecast_emissions_kgco2e is not None else None,
            "source_reference": self.source_reference,
            "evidence_reference": self.evidence_reference,
            "calculation_version": self.calculation_version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
