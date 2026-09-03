"""
models/carbon_ledger.py — Deterministic Carbon Accounting Ledger Model (Step 14).

Represents an immutable, auditable accounting entry derived from a CarbonCalculation.
Uses SQLAlchemy Numeric precision (Numeric(18, 6) and Numeric(24, 6)) to interface with Python Decimal.
Never recalculates emissions; strictly stores posted snapshots and accounting lineage.
"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, DateTime, Text, Numeric, ForeignKey
from backend.app.database.base import Base


class CarbonLedgerEntry(Base):
    __tablename__ = "carbon_ledger"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    carbon_calculation_id = Column(Integer, ForeignKey("carbon_calculations.id", ondelete="CASCADE"), nullable=False, index=True)
    activity_data_id = Column(Integer, ForeignKey("activity_data.id", ondelete="SET NULL"), nullable=True, index=True)
    document_id = Column(Integer, nullable=True, index=True)
    metric_id = Column(Integer, nullable=True, index=True)

    # Activity snapshot
    activity_type = Column(String(100), nullable=False, index=True)
    category = Column(String(50), nullable=False, default="OTHER", index=True)
    activity_role = Column(String(50), nullable=False, default="TOTAL")
    activity_group_id = Column(String(100), nullable=True, index=True)
    quantity = Column(Numeric(18, 6), nullable=False)
    activity_unit = Column(String(50), nullable=False)

    # Calculation snapshot
    calculated_co2e = Column(Numeric(24, 6), nullable=True)
    calculated_co2e_unit = Column(String(50), default="kgCO2e")
    calculation_version = Column(String(50), default="1.0")

    # Factor snapshot
    emission_factor_id = Column(Integer, nullable=True, index=True)
    factor_code = Column(String(100), nullable=True)
    factor_name = Column(String(255), nullable=True)
    factor_value = Column(Numeric(18, 6), nullable=True)
    factor_unit = Column(String(100), nullable=True)
    factor_version = Column(String(50), nullable=True)
    factor_source = Column(String(255), nullable=True)

    # Accounting dimensions
    geography = Column(String(100), nullable=True, index=True)
    reporting_period = Column(String(50), nullable=True)
    reporting_year = Column(Integer, nullable=True, index=True)
    scope = Column(String(50), nullable=True, index=True)

    # Ledger metadata
    # Statuses: POSTED, EXCLUDED, PENDING, INVALID, SUPERSEDED
    accounting_status = Column(String(50), nullable=False, default="POSTED", index=True)
    accounting_reason = Column(Text, nullable=True)
    ledger_version = Column(String(50), nullable=False, default="1.0")

    # Provenance & Audit Lineage
    source_field = Column(String(255), nullable=True)
    source_text = Column(Text, nullable=True)
    page = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "carbon_calculation_id": self.carbon_calculation_id,
            "activity_data_id": self.activity_data_id,
            "document_id": self.document_id,
            "metric_id": self.metric_id,
            "activity_type": self.activity_type,
            "category": self.category,
            "activity_role": self.activity_role,
            "activity_group_id": self.activity_group_id,
            "quantity": float(self.quantity) if self.quantity is not None else None,
            "activity_unit": self.activity_unit,
            "calculated_co2e": float(self.calculated_co2e) if self.calculated_co2e is not None else None,
            "calculated_co2e_unit": self.calculated_co2e_unit,
            "calculation_version": self.calculation_version,
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
            "accounting_status": self.accounting_status,
            "accounting_reason": self.accounting_reason,
            "ledger_version": self.ledger_version,
            "source_field": self.source_field,
            "source_text": self.source_text,
            "page": self.page,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
