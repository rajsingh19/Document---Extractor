"""
api/industry_benchmark.py — REST API router for Industry Benchmarking & Intelligence (Step 24 & Patches 1–14).

Endpoints:
- POST /api/benchmarks/evaluate
- GET  /api/benchmarks
- GET  /api/benchmarks/{benchmark_id}
- GET  /api/benchmarks/eligibility
- GET  /api/benchmarks/comparisons
- GET  /api/benchmarks/comparisons/{comparison_id}
- GET  /api/benchmarks/insights
- GET  /api/benchmarks/summary
- GET  /api/benchmarks/data-quality
- GET  /api/benchmarks/history
- GET  /api/benchmarks/sources
- POST /api/benchmarks/recalculate
- GET  /api/benchmarks/profile
- PUT  /api/benchmarks/profile
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from backend.app.database.session import get_db
from backend.app.models.industry_benchmark import (
    BusinessProfile,
    IndustryBenchmark,
    BenchmarkComparison,
)
from backend.app.schemas.industry_benchmark import (
    BusinessProfileResponse,
    BusinessProfileUpdate,
    IndustryBenchmarkResponse,
    IndustryBenchmarkListResponse,
    BenchmarkComparisonResponse,
    BenchmarkComparisonListResponse,
    BenchmarkEligibilityResponse,
    BenchmarkSummaryResponse,
    BenchmarkInsightResponse,
    BenchmarkEvaluationRequest,
    BenchmarkEvaluationResponse,
    BenchmarkRecalculateResponse,
    BenchmarkDataQualityResponse,
    BenchmarkSourcesResponse,
    BenchmarkSourceItem,
)
from backend.app.services.benchmark_eligibility import BenchmarkEligibilityService
from backend.app.services.industry_benchmark import industry_benchmark_service

router = APIRouter(prefix="/benchmarks", tags=["Industry Benchmarking"])


# ---------------------------------------------------------------------------
# Business Profile Endpoints (Patch 1 & 8)
# ---------------------------------------------------------------------------

@router.get("/profile", response_model=BusinessProfileResponse)
def get_business_profile(db: Session = Depends(get_db)):
    """Fetch current business profile segmentation and provenance."""
    profile = BenchmarkEligibilityService.get_or_create_default_profile(db)
    return profile


@router.put("/profile", response_model=BusinessProfileResponse)
def update_business_profile(update_data: BusinessProfileUpdate, db: Session = Depends(get_db)):
    """Update business profile fields with strict provenance tracking (Patch 1 & 8)."""
    profile = BenchmarkEligibilityService.get_or_create_default_profile(db)

    update_dict = update_data.model_dump(exclude_unset=True)
    for field, val in update_dict.items():
        setattr(profile, field, val)

    profile.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)
    return profile


# ---------------------------------------------------------------------------
# Eligibility & Evaluation Endpoints
# ---------------------------------------------------------------------------

@router.get("/eligibility", response_model=BenchmarkEligibilityResponse)
def get_benchmark_eligibility(
    document_id: Optional[int] = Query(None, description="Optional document filter"),
    reporting_period: Optional[str] = Query(None, description="Optional reporting period"),
    include_fixtures: bool = Query(False, description="Include test fixtures"),
    db: Session = Depends(get_db)
):
    """Deterministic eligibility check for industry benchmarking."""
    profile = BenchmarkEligibilityService.get_or_create_default_profile(db)
    return BenchmarkEligibilityService.evaluate_eligibility(
        db, profile, document_id, reporting_period, include_fixtures
    )


@router.post("/evaluate", response_model=BenchmarkEvaluationResponse)
def evaluate_benchmarks(
    req: BenchmarkEvaluationRequest,
    include_fixtures: bool = Query(False, description="Include test fixtures"),
    db: Session = Depends(get_db)
):
    """
    Deterministic & idempotent evaluation of actual posted carbon ledger performance
    against peer industry benchmarks.
    """
    comparisons = industry_benchmark_service.evaluate_benchmarks(
        db=db,
        reporting_period=req.reporting_period,
        document_id=req.document_id,
        force_refresh=req.force_refresh,
        include_fixtures=include_fixtures
    )

    profile = db.query(BusinessProfile).first()
    insights = industry_benchmark_service.generate_benchmark_insights(comparisons, profile)

    return BenchmarkEvaluationResponse(
        success=True,
        evaluated_at=datetime.utcnow(),
        reporting_period=req.reporting_period,
        comparisons_count=len(comparisons),
        comparisons=[BenchmarkComparisonResponse.model_validate(c) for c in comparisons],
        insights_count=len(insights),
        message=f"Successfully evaluated {len(comparisons)} benchmark comparisons."
    )


@router.post("/recalculate", response_model=BenchmarkRecalculateResponse)
def recalculate_benchmarks(
    reporting_period: Optional[str] = Query(None),
    document_id: Optional[int] = Query(None),
    include_fixtures: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Force re-evaluation of all benchmark comparisons."""
    comparisons = industry_benchmark_service.evaluate_benchmarks(
        db=db,
        reporting_period=reporting_period,
        document_id=document_id,
        force_refresh=True,
        include_fixtures=include_fixtures
    )
    return BenchmarkRecalculateResponse(
        success=True,
        recalculated_at=datetime.utcnow(),
        comparisons_count=len(comparisons),
        message="Benchmark calculations successfully refreshed."
    )


# ---------------------------------------------------------------------------
# Benchmark Registry Endpoints (Patch 3 & 4: Test Fixture Isolation)
# ---------------------------------------------------------------------------

@router.get("", response_model=IndustryBenchmarkListResponse)
def list_benchmarks(
    industry: Optional[str] = Query(None),
    metric_name: Optional[str] = Query(None),
    status: Optional[str] = Query("ACTIVE"),
    include_fixtures: bool = Query(False, description="Exclude test fixtures in production (Patch 4)"),
    db: Session = Depends(get_db)
):
    """List registered benchmarks with provenance, isolating test fixtures."""
    q = db.query(IndustryBenchmark)
    if not include_fixtures:
        q = q.filter(IndustryBenchmark.source_type != "TEST_FIXTURE")
    if industry:
        q = q.filter(IndustryBenchmark.industry.ilike(f"%{industry}%"))
    if metric_name:
        q = q.filter(IndustryBenchmark.metric_name == metric_name)
    if status:
        q = q.filter(IndustryBenchmark.status == status)

    benchmarks = q.all()
    return IndustryBenchmarkListResponse(
        total=len(benchmarks),
        benchmarks=[IndustryBenchmarkResponse.model_validate(b) for b in benchmarks]
    )


@router.get("/sources", response_model=BenchmarkSourcesResponse)
def get_benchmark_sources(
    include_fixtures: bool = Query(False),
    db: Session = Depends(get_db)
):
    """List benchmark data sources with authority types (Patch 3 & 4)."""
    q = db.query(
        IndustryBenchmark.source_name,
        IndustryBenchmark.source_type,
        IndustryBenchmark.source_reference,
        IndustryBenchmark.source_year,
        IndustryBenchmark.methodology,
        IndustryBenchmark.version,
        IndustryBenchmark.sample_size,
        func.count(IndustryBenchmark.id).label("benchmarks_count")
    )
    if not include_fixtures:
        q = q.filter(IndustryBenchmark.source_type != "TEST_FIXTURE")

    grouped = q.group_by(
        IndustryBenchmark.source_name,
        IndustryBenchmark.source_type,
        IndustryBenchmark.source_reference,
        IndustryBenchmark.source_year,
        IndustryBenchmark.methodology,
        IndustryBenchmark.version,
        IndustryBenchmark.sample_size
    ).all()

    items = [
        BenchmarkSourceItem(
            source_name=row.source_name,
            source_type=row.source_type,
            source_reference=row.source_reference,
            source_year=row.source_year,
            methodology=row.methodology,
            version=row.version,
            sample_size=row.sample_size,
            benchmarks_count=row.benchmarks_count
        )
        for row in grouped
    ]
    return BenchmarkSourcesResponse(sources=items, total=len(items))


@router.get("/summary", response_model=BenchmarkSummaryResponse)
def get_benchmark_summary(
    document_id: Optional[int] = Query(None),
    reporting_period: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get high-level benchmark summary for UI cards and dashboard integration."""
    summary_data = industry_benchmark_service.get_benchmark_summary(
        db, document_id, reporting_period
    )
    # Serialize comparisons
    summary_data["comparisons"] = [
        BenchmarkComparisonResponse.model_validate(c) for c in summary_data["comparisons"]
    ]
    summary_data["top_gaps"] = [
        BenchmarkComparisonResponse.model_validate(c) for c in summary_data["top_gaps"]
    ]
    summary_data["strengths"] = [
        BenchmarkComparisonResponse.model_validate(c) for c in summary_data["strengths"]
    ]
    return summary_data


@router.get("/insights", response_model=BenchmarkInsightResponse)
def get_benchmark_insights(
    document_id: Optional[int] = Query(None),
    reporting_period: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Retrieve deterministic benchmark insights."""
    q = db.query(BenchmarkComparison)
    if document_id:
        q = q.filter(BenchmarkComparison.source_document_id == document_id)
    if reporting_period:
        q = q.filter(BenchmarkComparison.reporting_period == reporting_period)
    comparisons = q.all()

    profile = db.query(BusinessProfile).first()
    insights = industry_benchmark_service.generate_benchmark_insights(comparisons, profile)
    return BenchmarkInsightResponse(insights=insights, total=len(insights))


@router.get("/data-quality", response_model=BenchmarkDataQualityResponse)
def get_benchmark_data_quality(db: Session = Depends(get_db)):
    """Assess benchmark and actual data quality state (Patch 15 from prompt)."""
    profile = BenchmarkEligibilityService.get_or_create_default_profile(db)
    comparisons = db.query(BenchmarkComparison).all()

    overall_conf = "HIGH"
    if not comparisons:
        overall_conf = "INSUFFICIENT"
    elif any(c.data_quality_confidence == "LOW" for c in comparisons):
        overall_conf = "LOW"
    elif any(c.data_quality_confidence == "MEDIUM" for c in comparisons):
        overall_conf = "MEDIUM"

    avg_sample = db.query(func.avg(IndustryBenchmark.sample_size)).scalar()
    first_b = db.query(IndustryBenchmark).first()

    return BenchmarkDataQualityResponse(
        overall_confidence=overall_conf,
        benchmark_sample_size=int(avg_sample) if avg_sample else None,
        benchmark_source_type=first_b.source_type if first_b else "NOT_AVAILABLE",
        benchmark_age_years=(datetime.utcnow().year - first_b.source_year) if (first_b and first_b.source_year) else None,
        actual_ledger_data_coverage="HIGH" if len(comparisons) >= 3 else "MEDIUM",
        segmentation_match="EXACT_SUB_INDUSTRY" if profile.sub_industry else "BROADER_INDUSTRY",
        details={
            "industry": profile.industry,
            "sub_industry": profile.sub_industry,
            "geography": profile.geography,
            "revenue_provenance": profile.revenue_data_status,
            "employee_provenance": profile.employee_data_status
        }
    )


@router.get("/comparisons", response_model=BenchmarkComparisonListResponse)
def list_benchmark_comparisons(
    document_id: Optional[int] = Query(None),
    reporting_period: Optional[str] = Query(None),
    metric_name: Optional[str] = Query(None),
    classification: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """List benchmark comparison records."""
    q = db.query(BenchmarkComparison)
    if document_id:
        q = q.filter(BenchmarkComparison.source_document_id == document_id)
    if reporting_period:
        q = q.filter(BenchmarkComparison.reporting_period == reporting_period)
    if metric_name:
        q = q.filter(BenchmarkComparison.metric_name == metric_name)
    if classification:
        q = q.filter(BenchmarkComparison.classification == classification)

    comps = q.order_by(desc(BenchmarkComparison.gap)).all()
    return BenchmarkComparisonListResponse(
        total=len(comps),
        comparisons=[BenchmarkComparisonResponse.model_validate(c) for c in comps]
    )


@router.get("/comparisons/{comparison_id}", response_model=BenchmarkComparisonResponse)
def get_benchmark_comparison_detail(comparison_id: int, db: Session = Depends(get_db)):
    """Retrieve detail of a specific benchmark comparison record."""
    comp = db.query(BenchmarkComparison).filter(BenchmarkComparison.id == comparison_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail=f"Benchmark comparison {comparison_id} not found.")
    return BenchmarkComparisonResponse.model_validate(comp)


@router.get("/history", response_model=BenchmarkComparisonListResponse)
def get_benchmark_history(
    metric_name: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Retrieve historical benchmark comparisons across version iterations (Patch 10)."""
    q = db.query(BenchmarkComparison)
    if metric_name:
        q = q.filter(BenchmarkComparison.metric_name == metric_name)

    comps = q.order_by(desc(BenchmarkComparison.created_at)).all()
    return BenchmarkComparisonListResponse(
        total=len(comps),
        comparisons=[BenchmarkComparisonResponse.model_validate(c) for c in comps]
    )


@router.get("/{benchmark_id}", response_model=IndustryBenchmarkResponse)
def get_benchmark_detail(benchmark_id: int, db: Session = Depends(get_db)):
    """Retrieve detail of a registered industry benchmark."""
    bench = db.query(IndustryBenchmark).filter(IndustryBenchmark.id == benchmark_id).first()
    if not bench:
        raise HTTPException(status_code=404, detail=f"Benchmark {benchmark_id} not found.")
    return IndustryBenchmarkResponse.model_validate(bench)
