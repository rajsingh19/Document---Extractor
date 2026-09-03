"""
models/activity_data.py — Canonical Activity Data Model (Step 12C).

Stores normalized, calculation-ready physical activity data (e.g. kWh, L, scm, tonne_km).
Physical activity quantities ONLY — NEVER stores calculated CO2e values.
Supports activity roles (TOTAL, COMPONENT, SUPPORTING), calculation eligibility,
activity grouping (to prevent double counting), and strict nullable geography.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from backend.app.database.base import Base


class ActivityData(Base):
    __tablename__ = "activity_data"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    document_id = Column(Integer, nullable=True, index=True)
    metric_id = Column(Integer, nullable=True, index=True)

    # Activity classification: purchased_electricity, diesel, petrol, natural_gas, lpg, water, waste, freight, other
    activity_type = Column(String(100), nullable=False, index=True)

    # Category: ENERGY, FUEL, TRANSPORT, WATER, WASTE, OTHER
    category = Column(String(50), nullable=False, default="OTHER", index=True)

    # Activity role: TOTAL, COMPONENT, SUPPORTING
    activity_role = Column(String(50), nullable=False, default="TOTAL", index=True)

    # Calculation eligibility: Derived deterministically from activity_role.
    # TOTAL -> True, COMPONENT -> True, SUPPORTING -> False
    calculation_eligible = Column(Boolean, nullable=False, default=True, index=True)

    # Activity grouping identifier to prevent double-counting across components & totals
    # (e.g. "doc_1_electricity_2024_10")
    activity_group_id = Column(String(100), nullable=True, index=True)

    # Physical activity quantity (e.g. 48750.0, 420.0). MUST NOT BE NEGATIVE. NOT CO2e!
    quantity = Column(Float, nullable=False)

    # Standardized unit: kWh, MWh, L, scm, kg, tonne, tonne_km, kL
    unit = Column(String(50), nullable=False)

    # Geographic boundary: Nullable, defaults to None (strictly never fabricated)
    geography = Column(String(100), nullable=True, default=None, index=True)

    # Reporting period and year (e.g. "2024-10" and 2024)
    reporting_period = Column(String(50), nullable=True)
    reporting_year = Column(Integer, nullable=True, index=True)

    # Associated Scope: SCOPE_1, SCOPE_2, SCOPE_3, NOT_APPLICABLE
    scope = Column(String(50), nullable=True, index=True)

    # Lineage / Provenance
    source_field = Column(String(255), nullable=True)
    source_text = Column(Text, nullable=True)
    page = Column(Integer, nullable=True)
    verification_status = Column(String(50), default="UNVERIFIED")

    # Normalization metadata
    normalization_status = Column(String(50), nullable=False, default="VALID", index=True)  # VALID, NEEDS_REVIEW, INVALID
    normalization_reasons = Column(Text, nullable=True)
    normalization_version = Column(String(50), nullable=False, default="1.0")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "document_id": self.document_id,
            "metric_id": self.metric_id,
            "activity_type": self.activity_type,
            "category": self.category,
            "activity_role": self.activity_role,
            "calculation_eligible": self.calculation_eligible,
            "activity_group_id": self.activity_group_id,
            "quantity": self.quantity,
            "unit": self.unit,
            "geography": self.geography,
            "reporting_period": self.reporting_period,
            "reporting_year": self.reporting_year,
            "scope": self.scope,
            "source_field": self.source_field,
            "source_text": self.source_text,
            "page": self.page,
            "verification_status": self.verification_status,
            "normalization_status": self.normalization_status,
            "normalization_reasons": self.normalization_reasons,
            "normalization_version": self.normalization_version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
