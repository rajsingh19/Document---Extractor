"""
models/emission_factor.py — Emission Factor Database Model (Step 12A).

Stores versioned, auditable emission factor records for activity data carbon calculations.
Emission factors are strictly non-AI generated structured reference data.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from backend.app.database.base import Base


class EmissionFactor(Base):
    __tablename__ = "emission_factors"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    factor_code = Column(String(100), unique=True, nullable=False, index=True)
    factor_name = Column(String(255), nullable=False)
    
    # Activity classification: purchased_electricity, diesel, petrol, natural_gas, lpg, water, waste, freight, other
    activity_type = Column(String(100), nullable=False, index=True)
    
    # Category: ENERGY, FUEL, TRANSPORT, WATER, WASTE, OTHER
    category = Column(String(50), nullable=False, index=True)
    
    # Scope: SCOPE_1, SCOPE_2, SCOPE_3, NOT_APPLICABLE
    scope = Column(String(50), nullable=False, index=True)
    
    # Numerical factor value (e.g. 0.71, 2.68). Must be positive.
    factor_value = Column(Float, nullable=False)
    
    # Factor unit (e.g. kgCO2e/kWh, kgCO2e/L, kgCO2e/tonne_km)
    factor_unit = Column(String(50), nullable=False)
    
    # Expected activity unit (e.g. kWh, L, scm, tonne_km)
    activity_unit = Column(String(50), nullable=False)
    
    # Geographical boundary (e.g. India, IN, Global, US)
    geography = Column(String(100), nullable=False, default="GLOBAL", index=True)
    
    # Applicable calendar year (e.g. 2024, 2025)
    applicable_year = Column(Integer, nullable=True, index=True)
    
    # Provenance and lineage
    source_name = Column(String(255), nullable=False)
    source_reference = Column(String(500), nullable=True)
    methodology = Column(String(255), nullable=True)
    
    # Versioning
    version = Column(String(50), nullable=False, default="1.0")
    effective_from = Column(String(50), nullable=True)
    effective_to = Column(String(50), nullable=True)
    
    # Status: ACTIVE, INACTIVE, DRAFT (only ACTIVE participates in candidate matching)
    status = Column(String(50), nullable=False, default="ACTIVE", index=True)
    
    # Additional audit notes
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "factor_code": self.factor_code,
            "factor_name": self.factor_name,
            "activity_type": self.activity_type,
            "category": self.category,
            "scope": self.scope,
            "factor_value": self.factor_value,
            "factor_unit": self.factor_unit,
            "activity_unit": self.activity_unit,
            "geography": self.geography,
            "applicable_year": self.applicable_year,
            "source_name": self.source_name,
            "source_reference": self.source_reference,
            "methodology": self.methodology,
            "version": self.version,
            "effective_from": self.effective_from,
            "effective_to": self.effective_to,
            "status": self.status,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
