"""
schemas/industry_benchmark.py — Pydantic schemas for Industry Benchmarking & Intelligence (Step 24 & Patches 1–14).
"""
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# ---------------------------------------------------------------------------
# Business Profile Schemas (Patch 1 & 8)
# ---------------------------------------------------------------------------

class BusinessProfileBase(BaseModel):
    organization_name: Optional[str] = "Default Business"
    industry: Optional[str] = None
    sub_industry: Optional[str] = None
    geography: Optional[str] = None
    business_size_band: Optional[str] = None
    facility_type: Optional[str] = None
    reporting_year: Optional[int] = None
    benchmark_version: Optional[str] = "1.0"

    # Numerical metrics & Provenance
    employee_count: Optional[int] = None
    employee_data_status: str = Field(default="NOT_PROVIDED", description="NOT_PROVIDED, USER_PROVIDED, VERIFIED")

    revenue_amount: Optional[Decimal] = None
    revenue_currency: str = Field(default="INR")
    revenue_data_status: str = Field(default="NOT_PROVIDED", description="NOT_PROVIDED, USER_PROVIDED, VERIFIED")

    production_volume: Optional[Decimal] = None
    production_unit: Optional[str] = None
    production_data_status: str = Field(default="NOT_PROVIDED", description="NOT_PROVIDED, USER_PROVIDED, VERIFIED")


class BusinessProfileCreate(BusinessProfileBase):
    pass


class BusinessProfileUpdate(BaseModel):
    organization_name: Optional[str] = None
    industry: Optional[str] = None
    sub_industry: Optional[str] = None
    geography: Optional[str] = None
    business_size_band: Optional[str] = None
    facility_type: Optional[str] = None
    reporting_year: Optional[int] = None
    benchmark_version: Optional[str] = None

    employee_count: Optional[int] = None
    employee_data_status: Optional[str] = None

    revenue_amount: Optional[Decimal] = None
    revenue_currency: Optional[str] = None
    revenue_data_status: Optional[str] = None

    production_volume: Optional[Decimal] = None
    production_unit: Optional[str] = None
    production_data_status: Optional[str] = None


class BusinessProfileResponse(BusinessProfileBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Industry Benchmark Registry Schemas (Patch 3 & 4)
# ---------------------------------------------------------------------------

class IndustryBenchmarkBase(BaseModel):
    benchmark_code: str
    benchmark_name: str
    industry: str
    sub_industry: Optional[str] = None
    geography: str
    business_size_band: Optional[str] = None

    metric_name: str
    metric_unit: str
    benchmark_type: str = Field(default="ABSOLUTE", description="ABSOLUTE, INTENSITY, PERCENTILE, RANGE")

    benchmark_value: Decimal
    lower_bound: Optional[Decimal] = None
    upper_bound: Optional[Decimal] = None
    percentile_25: Optional[Decimal] = None
    median: Optional[Decimal] = None
    percentile_75: Optional[Decimal] = None
    sample_size: Optional[int] = None

    source_name: str
    source_reference: str
    source_year: int
    methodology: str
    version: str = "1.0"
    status: str = "ACTIVE"
    source_type: str = Field(default="CURATED_SOURCE", description="AUTHORITATIVE_SOURCE, CURATED_SOURCE, USER_PROVIDED, TEST_FIXTURE")

    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    notes: Optional[str] = None


class IndustryBenchmarkCreate(IndustryBenchmarkBase):
    pass


class IndustryBenchmarkResponse(IndustryBenchmarkBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IndustryBenchmarkListResponse(BaseModel):
    total: int
    benchmarks: List[IndustryBenchmarkResponse]


# ---------------------------------------------------------------------------
# Benchmark Comparison Schemas (Patch 2, 10 & 11)
# ---------------------------------------------------------------------------

class BenchmarkComparisonResponse(BaseModel):
    id: int
    business_scope: str
    metric_name: str
    metric_unit: str
    business_value: Decimal
    benchmark_value: Decimal
    lower_bound: Optional[Decimal] = None
    upper_bound: Optional[Decimal] = None
    gap: Decimal
    gap_percentage: Optional[Decimal] = None  # NULL when benchmark_value == 0 (Patch 2 & 11)
    classification: str  # BETTER_THAN_BENCHMARK, WITHIN_BENCHMARK, WORSE_THAN_BENCHMARK, NOT_COMPARABLE
    comparison_method: str  # STANDARD_RANGE, ZERO_BENCHMARK_NONZERO_BUSINESS, BOTH_VALUES_ZERO, etc.

    benchmark_id: Optional[int] = None
    benchmark_code: Optional[str] = None
    benchmark_name: Optional[str] = None
    benchmark_version: str
    source_type: str
    source_name: Optional[str] = None
    source_year: Optional[int] = None
    engine_version: str

    reporting_period: Optional[str] = None
    data_status: str
    data_quality_confidence: str

    source_document_id: Optional[int] = None
    source_ledger_entry_id: Optional[int] = None

    explanation: Optional[str] = None
    limitation: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BenchmarkComparisonListResponse(BaseModel):
    total: int
    comparisons: List[BenchmarkComparisonResponse]


# ---------------------------------------------------------------------------
# Eligibility & Evaluation Schemas
# ---------------------------------------------------------------------------

class EligibilityCheckItem(BaseModel):
    check_name: str
    status: str  # PASSED, FAILED, WARNING
    message: str


class BenchmarkEligibilityResponse(BaseModel):
    status: str  # ELIGIBLE, PARTIALLY_ELIGIBLE, NOT_ELIGIBLE, BENCHMARK_UNAVAILABLE
    reason: str
    industry: Optional[str] = None
    sub_industry: Optional[str] = None
    geography: Optional[str] = None
    business_size_band: Optional[str] = None
    available_metrics_count: int = 0
    checks: List[EligibilityCheckItem] = []


class BenchmarkInsightItem(BaseModel):
    insight_code: str
    category: str  # ENERGY_GAP, EMISSIONS_GAP, SCOPE_GAP, INTENSITY_GAP, PERFORMANCE_STRENGTH, DATA_COVERAGE, BENCHMARK_LIMITATION
    metric_name: str
    title: str
    message: str
    recommendation: Optional[str] = None
    comparison_id: Optional[int] = None


class BenchmarkInsightResponse(BaseModel):
    insights: List[BenchmarkInsightItem]
    total: int


class BenchmarkSummaryResponse(BaseModel):
    status: str
    benchmark_version: str
    source_year: Optional[int] = None
    source_type: Optional[str] = None
    last_evaluated: Optional[datetime] = None
    eligible: bool
    eligibility_reason: Optional[str] = None
    metrics_compared: int
    better_count: int
    within_count: int
    worse_count: int
    comparisons: List[BenchmarkComparisonResponse]
    top_gaps: List[BenchmarkComparisonResponse]
    strengths: List[BenchmarkComparisonResponse]
    insights: List[BenchmarkInsightItem]
    data_quality_confidence: str
    peer_matching_type: str  # EXACT_PEER_MATCH, BROADER_INDUSTRY_MATCH, NO_EXACT_PEER_MATCH, BENCHMARK_UNAVAILABLE


class BenchmarkEvaluationRequest(BaseModel):
    reporting_period: Optional[str] = None
    document_id: Optional[int] = None
    force_refresh: bool = False


class BenchmarkEvaluationResponse(BaseModel):
    success: bool
    evaluated_at: datetime
    reporting_period: Optional[str] = None
    comparisons_count: int
    comparisons: List[BenchmarkComparisonResponse]
    insights_count: int
    message: str


class BenchmarkRecalculateResponse(BaseModel):
    success: bool
    recalculated_at: datetime
    comparisons_count: int
    message: str


class BenchmarkDataQualityResponse(BaseModel):
    overall_confidence: str  # HIGH, MEDIUM, LOW, INSUFFICIENT
    benchmark_sample_size: Optional[int] = None
    benchmark_source_type: str
    benchmark_age_years: Optional[int] = None
    actual_ledger_data_coverage: str
    segmentation_match: str  # EXACT_SUB_INDUSTRY, BROADER_INDUSTRY, GENERIC
    details: Dict[str, Any] = {}


class BenchmarkSourceItem(BaseModel):
    source_name: str
    source_type: str
    source_reference: str
    source_year: int
    methodology: str
    version: str
    sample_size: Optional[int] = None
    benchmarks_count: int = 0


class BenchmarkSourcesResponse(BaseModel):
    sources: List[BenchmarkSourceItem]
    total: int
