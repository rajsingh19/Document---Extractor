"""
models/reduction_opportunity.py — SQLAlchemy Model for Carbon Reduction Opportunities (Step 16).

Stores deterministic, evidence-backed reduction opportunities derived from POSTED CarbonLedgerEntry records.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, Text, DateTime, ForeignKey
from backend.app.database.base import Base


class ReductionOpportunity(Base):
    __tablename__ = "reduction_opportunities"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    opportunity_code = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50), nullable=False, index=True)  # ENERGY, FUEL, TRANSPORT, WATER, WASTE, EMISSIONS, DATA_QUALITY
    activity_type = Column(String(100), nullable=True, index=True)
    scope = Column(String(50), nullable=True, index=True)  # SCOPE_1, SCOPE_2, SCOPE_3
    priority = Column(String(50), nullable=False, default="MEDIUM", index=True)  # HIGH, MEDIUM, LOW
    trigger_type = Column(String(100), nullable=False, index=True)  # HIGH_EMISSION_SOURCE, INCREASING_EMISSIONS, REPEATED_INCREASE, HIGH_FUEL_USE, HIGH_ENERGY_USE, DATA_QUALITY, UNRESOLVED_FACTOR, MANUAL
    status = Column(String(50), nullable=False, default="OPEN", index=True)  # OPEN, ACKNOWLEDGED, IN_PROGRESS, COMPLETED, DISMISSED

    # Traceability & Provenance Evidence
    evidence_document_id = Column(Integer, ForeignKey("documents.id"), nullable=True, index=True)
    evidence_metric_id = Column(Integer, ForeignKey("sustainability_metrics.id"), nullable=True, index=True)
    evidence_ledger_entry_id = Column(Integer, ForeignKey("carbon_ledger.id"), nullable=True, index=True)

    # Quantitative Context (nullable, exact Decimal)
    current_value = Column(Numeric(18, 6), nullable=True)
    current_unit = Column(String(50), nullable=True)
    previous_value = Column(Numeric(18, 6), nullable=True)
    previous_unit = Column(String(50), nullable=True)
    change_absolute = Column(Numeric(18, 6), nullable=True)
    change_percentage = Column(Numeric(10, 4), nullable=True)

    # Footprint Context
    calculated_co2e = Column(Numeric(24, 6), nullable=True)
    calculated_co2e_unit = Column(String(50), default="kgCO2e", nullable=False)

    # Decision Support & Investigation Context
    rationale = Column(Text, nullable=False)
    recommended_action = Column(Text, nullable=False)
    limitations = Column(Text, nullable=False)
    detection_version = Column(String(50), default="1.0", nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
