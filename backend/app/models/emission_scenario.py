"""
models/emission_scenario.py — SQLAlchemy Models for Emissions Scenario / What-If Engine (Step 22C).

Defines persistent models for hypothetical decarbonization scenarios, structured
user assumptions, and source-level calculation results with immutable factor snapshots.
Uses SQLAlchemy Numeric precision (Numeric(18, 6) and Numeric(24, 6)) for Decimal arithmetic.
"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Numeric, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database.base import Base
from backend.app.config.emission_scenario import (
    SCENARIO_CALCULATION_VERSION,
    SCENARIO_STATUS_DRAFT,
    QUANTIFICATION_STATUS_NOT_QUANTIFIABLE,
    TARGET_STATUS_NOT_DEFINED,
    RESULT_STATUS_QUANTIFIED,
)


class EmissionScenario(Base):
    """
    Hypothetical decarbonization scenario record.
    Evaluates what-if assumptions against verified baseline ledger actuals.
    """
    __tablename__ = "emission_scenarios"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    scenario_code = Column(String(100), unique=True, nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True)
    roadmap_id = Column(Integer, ForeignKey("reduction_roadmaps.id", ondelete="SET NULL"), nullable=True, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    scenario_type = Column(String(50), nullable=False, index=True)  # REDUCE_ACTIVITY, REPLACE_SOURCE, SHIFT_SOURCE, etc.
    status = Column(String(50), nullable=False, default=SCENARIO_STATUS_DRAFT, index=True)  # DRAFT, CALCULATED, ARCHIVED

    # Baseline dimensions (strictly sourced from POSTED CarbonLedgerEntry)
    baseline_period = Column(String(50), nullable=True)
    baseline_emissions_kgco2e = Column(Numeric(24, 6), nullable=False, default=Decimal("0.0"))
    baseline_emissions_tco2e = Column(Numeric(18, 6), nullable=False, default=Decimal("0.0"))

    # Modeled scenario emissions (NULL if unquantifiable)
    scenario_emissions_kgco2e = Column(Numeric(24, 6), nullable=True)
    scenario_emissions_tco2e = Column(Numeric(18, 6), nullable=True)

    # Modeled reduction (NULL if unquantifiable)
    reduction_kgco2e = Column(Numeric(24, 6), nullable=True)
    reduction_tco2e = Column(Numeric(18, 6), nullable=True)
    reduction_percent = Column(Numeric(8, 4), nullable=True)

    # Target comparison (relative to linked or active ReductionRoadmap)
    remaining_target_gap_kgco2e = Column(Numeric(24, 6), nullable=True)
    remaining_target_gap_tco2e = Column(Numeric(18, 6), nullable=True)
    target_status = Column(String(50), nullable=False, default=TARGET_STATUS_NOT_DEFINED)

    # Quantification status
    quantification_status = Column(String(50), nullable=False, default=QUANTIFICATION_STATUS_NOT_QUANTIFIABLE)

    # Assumption and limitation summaries
    assumption_summary = Column(Text, nullable=True)
    limitation_summary = Column(Text, nullable=True)

    # Versioning & Lineage
    calculation_version = Column(String(50), nullable=False, default=SCENARIO_CALCULATION_VERSION)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    inputs = relationship("ScenarioInput", back_populates="scenario", cascade="all, delete-orphan", lazy="selectin")
    results = relationship("ScenarioResult", back_populates="scenario", cascade="all, delete-orphan", lazy="selectin")

    def to_dict(self):
        return {
            "id": self.id,
            "scenario_code": self.scenario_code,
            "document_id": self.document_id,
            "roadmap_id": self.roadmap_id,
            "name": self.name,
            "description": self.description,
            "scenario_type": self.scenario_type,
            "status": self.status,
            "baseline_period": self.baseline_period,
            "baseline_emissions_kgco2e": float(self.baseline_emissions_kgco2e) if self.baseline_emissions_kgco2e is not None else 0.0,
            "baseline_emissions_tco2e": float(self.baseline_emissions_tco2e) if self.baseline_emissions_tco2e is not None else 0.0,
            "scenario_emissions_kgco2e": float(self.scenario_emissions_kgco2e) if self.scenario_emissions_kgco2e is not None else None,
            "scenario_emissions_tco2e": float(self.scenario_emissions_tco2e) if self.scenario_emissions_tco2e is not None else None,
            "reduction_kgco2e": float(self.reduction_kgco2e) if self.reduction_kgco2e is not None else None,
            "reduction_tco2e": float(self.reduction_tco2e) if self.reduction_tco2e is not None else None,
            "reduction_percent": float(self.reduction_percent) if self.reduction_percent is not None else None,
            "remaining_target_gap_kgco2e": float(self.remaining_target_gap_kgco2e) if self.remaining_target_gap_kgco2e is not None else None,
            "remaining_target_gap_tco2e": float(self.remaining_target_gap_tco2e) if self.remaining_target_gap_tco2e is not None else None,
            "target_status": self.target_status,
            "quantification_status": self.quantification_status,
            "assumption_summary": self.assumption_summary,
            "limitation_summary": self.limitation_summary,
            "calculation_version": self.calculation_version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "inputs_count": len(self.inputs) if self.inputs else 0,
            "results_count": len(self.results) if self.results else 0,
        }


class ScenarioInput(Base):
    """
    User-provided scenario assumption specifying changes to activity or sources.
    """
    __tablename__ = "scenario_inputs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    scenario_id = Column(Integer, ForeignKey("emission_scenarios.id", ondelete="CASCADE"), nullable=False, index=True)

    activity_data_id = Column(Integer, ForeignKey("activity_data.id", ondelete="SET NULL"), nullable=True, index=True)
    source_ledger_entry_id = Column(Integer, ForeignKey("carbon_ledger.id", ondelete="SET NULL"), nullable=True, index=True)

    activity_type = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False, default="OTHER")
    scope = Column(String(50), nullable=True)

    # Quantities before and after modeled change
    baseline_quantity = Column(Numeric(18, 6), nullable=False)
    baseline_unit = Column(String(50), nullable=False)
    scenario_quantity = Column(Numeric(18, 6), nullable=False)
    scenario_unit = Column(String(50), nullable=False)

    # Change parameters
    change_type = Column(String(50), nullable=False)  # REDUCE_ACTIVITY, REPLACE_SOURCE, etc.
    change_percent = Column(Numeric(8, 4), nullable=True)
    replacement_source = Column(String(100), nullable=True)
    replacement_activity_data_id = Column(Integer, ForeignKey("activity_data.id", ondelete="SET NULL"), nullable=True)

    # Resolved factor references
    emission_factor_id = Column(Integer, ForeignKey("emission_factors.id", ondelete="SET NULL"), nullable=True)
    replacement_emission_factor_id = Column(Integer, ForeignKey("emission_factors.id", ondelete="SET NULL"), nullable=True)

    assumption = Column(Text, nullable=True)
    evidence_reference = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    scenario = relationship("EmissionScenario", back_populates="inputs")

    def to_dict(self):
        return {
            "id": self.id,
            "scenario_id": self.scenario_id,
            "activity_data_id": self.activity_data_id,
            "source_ledger_entry_id": self.source_ledger_entry_id,
            "activity_type": self.activity_type,
            "category": self.category,
            "scope": self.scope,
            "baseline_quantity": float(self.baseline_quantity) if self.baseline_quantity is not None else 0.0,
            "baseline_unit": self.baseline_unit,
            "scenario_quantity": float(self.scenario_quantity) if self.scenario_quantity is not None else 0.0,
            "scenario_unit": self.scenario_unit,
            "change_type": self.change_type,
            "change_percent": float(self.change_percent) if self.change_percent is not None else None,
            "replacement_source": self.replacement_source,
            "replacement_activity_data_id": self.replacement_activity_data_id,
            "emission_factor_id": self.emission_factor_id,
            "replacement_emission_factor_id": self.replacement_emission_factor_id,
            "assumption": self.assumption,
            "evidence_reference": self.evidence_reference,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ScenarioResult(Base):
    """
    Source-level modeled calculation output preserving immutable factor snapshots.
    """
    __tablename__ = "scenario_results"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    scenario_id = Column(Integer, ForeignKey("emission_scenarios.id", ondelete="CASCADE"), nullable=False, index=True)

    source_name = Column(String(255), nullable=False)
    scope = Column(String(50), nullable=True)
    category = Column(String(50), nullable=False, default="OTHER")
    activity_type = Column(String(100), nullable=False)

    baseline_quantity = Column(Numeric(18, 6), nullable=False)
    scenario_quantity = Column(Numeric(18, 6), nullable=False)
    unit = Column(String(50), nullable=False)

    baseline_emissions_kgco2e = Column(Numeric(24, 6), nullable=False)
    scenario_emissions_kgco2e = Column(Numeric(24, 6), nullable=True)
    reduction_kgco2e = Column(Numeric(24, 6), nullable=True)

    # Immutable factor snapshots
    baseline_factor = Column(Numeric(18, 6), nullable=True)
    scenario_factor = Column(Numeric(18, 6), nullable=True)
    factor_unit = Column(String(100), nullable=True)
    factor_source = Column(String(255), nullable=True)
    factor_version = Column(String(50), nullable=True)
    factor_code = Column(String(100), nullable=True)

    calculation_formula = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default=RESULT_STATUS_QUANTIFIED)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    scenario = relationship("EmissionScenario", back_populates="results")

    def to_dict(self):
        return {
            "id": self.id,
            "scenario_id": self.scenario_id,
            "source_name": self.source_name,
            "scope": self.scope,
            "category": self.category,
            "activity_type": self.activity_type,
            "baseline_quantity": float(self.baseline_quantity) if self.baseline_quantity is not None else 0.0,
            "scenario_quantity": float(self.scenario_quantity) if self.scenario_quantity is not None else 0.0,
            "unit": self.unit,
            "baseline_emissions_kgco2e": float(self.baseline_emissions_kgco2e) if self.baseline_emissions_kgco2e is not None else 0.0,
            "scenario_emissions_kgco2e": float(self.scenario_emissions_kgco2e) if self.scenario_emissions_kgco2e is not None else None,
            "reduction_kgco2e": float(self.reduction_kgco2e) if self.reduction_kgco2e is not None else None,
            "baseline_factor": float(self.baseline_factor) if self.baseline_factor is not None else None,
            "scenario_factor": float(self.scenario_factor) if self.scenario_factor is not None else None,
            "factor_unit": self.factor_unit,
            "factor_source": self.factor_source,
            "factor_version": self.factor_version,
            "factor_code": self.factor_code,
            "calculation_formula": self.calculation_formula,
            "status": self.status,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
