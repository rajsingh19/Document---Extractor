"""
models/carbon_calculation.py — Deterministic Carbon Calculation Model (Step 13).

Stores calculated CO2e emissions separate from extracted metrics.
Uses SQLAlchemy Numeric precision (Numeric(18, 6) and Numeric(24, 6)) to interface with Python Decimal.
Stores an immutable snapshot of the matched emission factor, calculation formula, and provenance.
"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, DateTime, Text, Numeric, ForeignKey
from backend.app.database.base import Base


class CarbonCalculation(Base):
    __tablename__ = "carbon_calculations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    activity_data_id = Column(Integer, ForeignKey("activity_data.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(Integer, nullable=True, index=True)
    metric_id = Column(Integer, nullable=True, index=True)

    # Activity classification & role
    activity_type = Column(String(100), nullable=False, index=True)
    activity_role = Column(String(50), nullable=False, default="TOTAL")
    activity_group_id = Column(String(100), nullable=True, index=True)

    # Physical activity amount stored as Numeric/Decimal
    quantity = Column(Numeric(18, 6), nullable=False)
    activity_unit = Column(String(50), nullable=False)

    # Emission Factor Snapshot (immutable historical record)
    emission_factor_id = Column(Integer, nullable=True, index=True)
    factor_code = Column(String(100), nullable=True)
    factor_name = Column(String(255), nullable=True)
    factor_value = Column(Numeric(18, 6), nullable=True)
    factor_unit = Column(String(100), nullable=True)
    factor_version = Column(String(50), nullable=True)
    factor_source = Column(String(255), nullable=True)

    # Context & Boundary (Strict provenance, no fabrication)
    geography = Column(String(100), nullable=True)
    reporting_period = Column(String(50), nullable=True)
    reporting_year = Column(Integer, nullable=True, index=True)
    scope = Column(String(50), nullable=True, index=True)

    # Calculation Result
    calculated_co2e = Column(Numeric(24, 6), nullable=True)
    calculated_co2e_unit = Column(String(50), default="kgCO2e")
    formula = Column(Text, nullable=True)
    calculation_version = Column(String(50), default="1.0")

    # Status: CALCULATED, NO_ACTIVITY, NO_FACTOR, MULTIPLE_FACTORS, INELIGIBLE,
    # INVALID_ACTIVITY, UNSUPPORTED_UNIT, MISSING_GEOGRAPHY, MISSING_YEAR, ERROR
    status = Column(String(50), nullable=False, default="CALCULATED", index=True)
    calculation_reason = Column(Text, nullable=True)

    # Provenance & Audit Lineage
    source_field = Column(String(255), nullable=True)
    source_text = Column(Text, nullable=True)
    page = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "activity_data_id": self.activity_data_id,
            "document_id": self.document_id,
            "metric_id": self.metric_id,
            "activity_type": self.activity_type,
            "activity_role": self.activity_role,
            "activity_group_id": self.activity_group_id,
            "quantity": float(self.quantity) if self.quantity is not None else None,
            "activity_unit": self.activity_unit,
            "emission_factor_id": self.emission_factor_id,
            "factor_code": self.factor_code,
            "factor_name": self.factor_name,
            "factor_value": float(self.factor_value) if self.factor_value is not None else None,
            "factor_unit": self.factor_unit,
            "factor_version": self.factor_version,
            "factor_source": self.factor_source,
            "geography": self.geography,
            "reporting_period": self.reporting_period,
            "reporting_year": self.reporting_year,
            "scope": self.scope,
            "calculated_co2e": float(self.calculated_co2e) if self.calculated_co2e is not None else None,
            "calculated_co2e_unit": self.calculated_co2e_unit,
            "formula": self.formula,
            "calculation_version": self.calculation_version,
            "status": self.status,
            "calculation_reason": self.calculation_reason,
            "source_field": self.source_field,
            "source_text": self.source_text,
            "page": self.page,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
