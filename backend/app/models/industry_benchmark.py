"""
models/industry_benchmark.py — SQLAlchemy models for Industry Benchmarking & Intelligence (Step 24 & Patches 1–14).

Adheres to:
1. No fake benchmark data: explicit provenance, versions, sample sizes, and source types.
2. BusinessProfile numerical data provenance (Patch 1): revenue_data_status, employee_data_status.
3. Zero-safe mathematical comparisons (Patch 2): NULL gap percentages, zero-safe comparison methods.
4. Source authority hierarchy (Patch 3): AUTHORITATIVE_SOURCE, CURATED_SOURCE, USER_PROVIDED, TEST_FIXTURE.
5. Strict Decimal precision for all sustainability metrics.
6. Benchmark version immutability (Patch 10).
"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    Text,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from backend.app.database.base import Base


class BusinessProfile(Base):
    """
    Segmentation and profile parameters for the reporting business.
    Numerical values (revenue, employees) require explicit user-provided or verified
    provenance before being used in intensity benchmarking (Patch 1 & 8).
    """
    __tablename__ = "business_profiles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    organization_name = Column(String(255), nullable=False, default="Default Business")
    industry = Column(String(100), nullable=True, index=True)
    sub_industry = Column(String(100), nullable=True, index=True)
    geography = Column(String(100), nullable=True, index=True)  # No implicit default (Patch 8)
    business_size_band = Column(String(50), nullable=True, index=True)  # No implicit default (Patch 8)
    facility_type = Column(String(100), nullable=True)
    reporting_year = Column(Integer, nullable=True, index=True)
    benchmark_version = Column(String(50), nullable=True, default="1.0")

    # Numerical metrics with explicit provenance (Patch 1)
    employee_count = Column(Integer, nullable=True)
    employee_data_status = Column(
        String(50), nullable=False, default="NOT_PROVIDED", index=True
    )  # NOT_PROVIDED, USER_PROVIDED, VERIFIED

    revenue_amount = Column(Numeric(18, 4), nullable=True)
    revenue_currency = Column(String(10), nullable=False, default="INR")
    revenue_data_status = Column(
        String(50), nullable=False, default="NOT_PROVIDED", index=True
    )  # NOT_PROVIDED, USER_PROVIDED, VERIFIED

    production_volume = Column(Numeric(18, 4), nullable=True)
    production_unit = Column(String(50), nullable=True)
    production_data_status = Column(
        String(50), nullable=False, default="NOT_PROVIDED", index=True
    )  # NOT_PROVIDED, USER_PROVIDED, VERIFIED

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class IndustryBenchmark(Base):
    """
    Versioned registry of authoritative or curated industry benchmarks.
    Never fabricated; strictly audited with source provenance and source type (Patch 3 & 4).
    """
    __tablename__ = "industry_benchmarks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    benchmark_code = Column(String(100), unique=True, nullable=False, index=True)
    benchmark_name = Column(String(255), nullable=False)
    industry = Column(String(100), nullable=False, index=True)
    sub_industry = Column(String(100), nullable=True, index=True)
    geography = Column(String(100), nullable=False, index=True)
    business_size_band = Column(String(50), nullable=True, index=True)

    metric_name = Column(String(100), nullable=False, index=True)  # e.g. total_emissions, scope_1, scope_2, electricity_consumption, fuel_consumption, emissions_intensity_revenue, emissions_intensity_employee
    metric_unit = Column(String(50), nullable=False)  # e.g. tCO2e, kWh, Liters, tCO2e/INR_Crore, tCO2e/employee
    benchmark_type = Column(String(50), nullable=False, default="ABSOLUTE")  # ABSOLUTE, INTENSITY, PERCENTILE, RANGE

    benchmark_value = Column(Numeric(18, 4), nullable=False)
    lower_bound = Column(Numeric(18, 4), nullable=True)
    upper_bound = Column(Numeric(18, 4), nullable=True)
    percentile_25 = Column(Numeric(18, 4), nullable=True)
    median = Column(Numeric(18, 4), nullable=True)
    percentile_75 = Column(Numeric(18, 4), nullable=True)
    sample_size = Column(Integer, nullable=True)

    # Source Provenance & Authority (Patch 3 & 4)
    source_name = Column(String(255), nullable=False)
    source_reference = Column(String(255), nullable=False)
    source_year = Column(Integer, nullable=False)
    methodology = Column(Text, nullable=False)
    version = Column(String(50), nullable=False, default="1.0", index=True)
    status = Column(String(50), nullable=False, default="ACTIVE", index=True)  # ACTIVE, INACTIVE, SUPERSEDED
    source_type = Column(
        String(50), nullable=False, default="CURATED_SOURCE", index=True
    )  # AUTHORITATIVE_SOURCE, CURATED_SOURCE, USER_PROVIDED, TEST_FIXTURE

    effective_from = Column(DateTime, nullable=True)
    effective_to = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_benchmark_lookup", "industry", "metric_name", "status", "version"),
    )


class BenchmarkComparison(Base):
    """
    Persisted deterministic comparison between verified BUSINESS ACTUAL posted ledger data
    and an active benchmark registry entry.
    Maintains historical immutability (Patch 10) and zero-safe mathematical contract (Patch 2 & 11).
    """
    __tablename__ = "benchmark_comparisons"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    business_scope = Column(String(100), nullable=False, default="ORGANIZATION")  # ORGANIZATION, FACILITY, DOCUMENT
    metric_name = Column(String(100), nullable=False, index=True)
    metric_unit = Column(String(50), nullable=False)

    # Numerical values
    business_value = Column(Numeric(18, 4), nullable=False)
    benchmark_value = Column(Numeric(18, 4), nullable=False)
    lower_bound = Column(Numeric(18, 4), nullable=True)
    upper_bound = Column(Numeric(18, 4), nullable=True)
    gap = Column(Numeric(18, 4), nullable=False)  # business_value - benchmark_value
    gap_percentage = Column(Numeric(10, 4), nullable=True)  # NULL if benchmark_value == 0 (Patch 2)

    # Classification & Provenance
    classification = Column(
        String(50), nullable=False, index=True
    )  # BETTER_THAN_BENCHMARK, WITHIN_BENCHMARK, WORSE_THAN_BENCHMARK, NOT_COMPARABLE
    comparison_method = Column(
        String(100), nullable=False, default="STANDARD_RANGE"
    )  # STANDARD_RANGE, ZERO_BENCHMARK_NONZERO_BUSINESS, BOTH_VALUES_ZERO, POINT_COMPARISON

    benchmark_id = Column(Integer, ForeignKey("industry_benchmarks.id", ondelete="SET NULL"), nullable=True, index=True)
    benchmark_code = Column(String(100), nullable=True)
    benchmark_name = Column(String(255), nullable=True)
    benchmark_version = Column(String(50), nullable=False, default="1.0")
    source_type = Column(String(50), nullable=False, default="CURATED_SOURCE")
    source_name = Column(String(255), nullable=True)
    source_year = Column(Integer, nullable=True)
    engine_version = Column(String(50), nullable=False, default="1.0")

    reporting_period = Column(String(100), nullable=True, index=True)
    data_status = Column(
        String(50), nullable=False, default="ACTUAL_POSTED"
    )  # ACTUAL_POSTED, ESTIMATED, INSUFFICIENT
    data_quality_confidence = Column(
        String(50), nullable=False, default="HIGH", index=True
    )  # HIGH, MEDIUM, LOW, INSUFFICIENT

    source_document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True)
    source_ledger_entry_id = Column(Integer, nullable=True, index=True)

    # Explanations & Limitations (Patch 5 & 11)
    explanation = Column(Text, nullable=True)
    limitation = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
