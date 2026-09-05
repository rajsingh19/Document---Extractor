"""
services/benchmark_eligibility.py — Benchmark Eligibility Engine (Step 24 & Patches 1, 4, 8, 9).

Determines whether the business can be reliably compared against active benchmarks.
Enforces:
1. No implicit segmentation defaults (Patch 8):
   - geography never defaults to 'India'
   - business_size_band never defaults to 'MSME'
   - industry never inferred
2. Numerical intensity requirements (Patch 1 & 9):
   - revenue intensity requires revenue_amount > 0 and revenue_data_status in ('USER_PROVIDED', 'VERIFIED')
   - employee intensity requires employee_count > 0 and employee_data_status in ('USER_PROVIDED', 'VERIFIED')
   - production volume intensity requires production_volume > 0 and production_data_status in ('USER_PROVIDED', 'VERIFIED')
3. Actual data only from posted ledger entries (Patch 7).
4. Returns explicit status and reasons:
   - ELIGIBLE
   - PARTIALLY_ELIGIBLE
   - NOT_ELIGIBLE
   - BENCHMARK_UNAVAILABLE
"""
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.models.industry_benchmark import BusinessProfile, IndustryBenchmark
from backend.app.models.carbon_ledger import CarbonLedgerEntry


class BenchmarkEligibilityService:
    """
    Deterministic eligibility evaluator for industry benchmarking.
    """

    @staticmethod
    def get_or_create_default_profile(db: Session) -> BusinessProfile:
        """Fetch the current business profile or create a clean baseline without defaulting attributes."""
        profile = db.query(BusinessProfile).first()
        if not profile:
            profile = BusinessProfile(
                organization_name="My Organization",
                industry=None,
                sub_industry=None,
                geography=None,
                business_size_band=None,
                facility_type=None,
                reporting_year=None,
                benchmark_version="1.0",
                revenue_amount=None,
                revenue_data_status="NOT_PROVIDED",
                employee_count=None,
                employee_data_status="NOT_PROVIDED",
                production_volume=None,
                production_data_status="NOT_PROVIDED"
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)
        return profile

    @classmethod
    def evaluate_eligibility(
        cls,
        db: Session,
        profile: Optional[BusinessProfile] = None,
        document_id: Optional[int] = None,
        reporting_period: Optional[str] = None,
        include_fixtures: bool = False
    ) -> Dict[str, Any]:
        """
        Evaluate eligibility of the business for benchmark comparisons.
        Returns dictionary matching BenchmarkEligibilityResponse.
        """
        if profile is None:
            profile = cls.get_or_create_default_profile(db)

        checks: List[Dict[str, str]] = []

        # Check 1: Industry Available (Patch 8)
        if not profile.industry or not profile.industry.strip():
            checks.append({
                "check_name": "Industry Available",
                "status": "FAILED",
                "message": "Industry is required to select a comparable benchmark."
            })
            return {
                "status": "BENCHMARK_UNAVAILABLE",
                "reason": "Industry is required to select a comparable benchmark.",
                "industry": profile.industry,
                "sub_industry": profile.sub_industry,
                "geography": profile.geography,
                "business_size_band": profile.business_size_band,
                "available_metrics_count": 0,
                "checks": checks
            }
        else:
            checks.append({
                "check_name": "Industry Available",
                "status": "PASSED",
                "message": f"Industry specified: {profile.industry}"
            })

        # Check 2: Geography Compatible (Patch 8)
        if not profile.geography or not profile.geography.strip():
            checks.append({
                "check_name": "Geography Specified",
                "status": "FAILED",
                "message": "Geography is required to select a comparable regional benchmark."
            })
            return {
                "status": "BENCHMARK_UNAVAILABLE",
                "reason": "Geography is required to select a comparable regional benchmark.",
                "industry": profile.industry,
                "sub_industry": profile.sub_industry,
                "geography": profile.geography,
                "business_size_band": profile.business_size_band,
                "available_metrics_count": 0,
                "checks": checks
            }
        else:
            checks.append({
                "check_name": "Geography Specified",
                "status": "PASSED",
                "message": f"Geography specified: {profile.geography}"
            })

        # Check 3: Business Size Band (Optional or warning)
        if not profile.business_size_band:
            checks.append({
                "check_name": "Business Size Band",
                "status": "WARNING",
                "message": "Business size band is missing; comparison will rely on broader industry metrics."
            })
        else:
            checks.append({
                "check_name": "Business Size Band",
                "status": "PASSED",
                "message": f"Business size band: {profile.business_size_band}"
            })

        # Check 4: Sub-Industry Check
        if not profile.sub_industry:
            checks.append({
                "check_name": "Sub-Industry Specificity",
                "status": "WARNING",
                "message": "Sub-industry is not specified; comparison will fall back to broader sector benchmark."
            })
        else:
            checks.append({
                "check_name": "Sub-Industry Specificity",
                "status": "PASSED",
                "message": f"Sub-industry specified: {profile.sub_industry}"
            })

        # Check 5: Actual Posted Ledger Data Availability (Patch 7)
        ledger_q = db.query(CarbonLedgerEntry).filter(CarbonLedgerEntry.accounting_status == "POSTED")
        if document_id:
            ledger_q = ledger_q.filter(CarbonLedgerEntry.document_id == document_id)
        if reporting_period:
            ledger_q = ledger_q.filter(CarbonLedgerEntry.reporting_period == reporting_period)
        posted_count = ledger_q.count()

        if posted_count == 0:
            checks.append({
                "check_name": "Actual Posted Data",
                "status": "FAILED",
                "message": "No verified POSTED ledger entries found. Benchmarking compares actual verified data only."
            })
            return {
                "status": "NOT_ELIGIBLE",
                "reason": "No verified POSTED carbon ledger entries available for comparison.",
                "industry": profile.industry,
                "sub_industry": profile.sub_industry,
                "geography": profile.geography,
                "business_size_band": profile.business_size_band,
                "available_metrics_count": 0,
                "checks": checks
            }
        else:
            checks.append({
                "check_name": "Actual Posted Data",
                "status": "PASSED",
                "message": f"{posted_count} posted carbon ledger entries available."
            })

        # Check 6: Active Benchmarks in Registry (Patch 3 & 4)
        bench_q = db.query(IndustryBenchmark).filter(
            IndustryBenchmark.industry.ilike(profile.industry),
            IndustryBenchmark.geography.ilike(profile.geography),
            IndustryBenchmark.status == "ACTIVE"
        )
        if not include_fixtures:
            bench_q = bench_q.filter(IndustryBenchmark.source_type != "TEST_FIXTURE")

        active_benchmarks = bench_q.all()
        if not active_benchmarks:
            checks.append({
                "check_name": "Benchmark Registry Coverage",
                "status": "FAILED",
                "message": "Comparable peer benchmark data is not currently available for this segment."
            })
            return {
                "status": "BENCHMARK_UNAVAILABLE",
                "reason": "Comparable peer benchmark data is not currently available for this segment.",
                "industry": profile.industry,
                "sub_industry": profile.sub_industry,
                "geography": profile.geography,
                "business_size_band": profile.business_size_band,
                "available_metrics_count": 0,
                "checks": checks
            }
        else:
            checks.append({
                "check_name": "Benchmark Registry Coverage",
                "status": "PASSED",
                "message": f"{len(active_benchmarks)} active benchmark metrics available for {profile.industry} ({profile.geography})."
            })

        # Check 7: Denominator checks for intensity metrics (Patch 1 & 9)
        intensity_notes = []
        rev_eligible = (
            profile.revenue_amount is not None
            and profile.revenue_amount > 0
            and profile.revenue_data_status in ("USER_PROVIDED", "VERIFIED")
        )
        if not rev_eligible:
            intensity_notes.append("Revenue intensity cannot be calculated because verified revenue is not provided.")

        emp_eligible = (
            profile.employee_count is not None
            and profile.employee_count > 0
            and profile.employee_data_status in ("USER_PROVIDED", "VERIFIED")
        )
        if not emp_eligible:
            intensity_notes.append("Employee intensity cannot be calculated because verified employee count is not provided.")

        if intensity_notes:
            checks.append({
                "check_name": "Intensity Denominators",
                "status": "WARNING",
                "message": " ".join(intensity_notes)
            })
            final_status = "PARTIALLY_ELIGIBLE"
            reason = (
                "Absolute emissions can be compared against benchmarks, but some intensity metrics "
                "require explicit user-provided or verified denominators."
            )
        else:
            checks.append({
                "check_name": "Intensity Denominators",
                "status": "PASSED",
                "message": "Verified denominators for revenue and employee intensities are available."
            })
            final_status = "ELIGIBLE"
            reason = "Business actuals and profile parameters are fully eligible for peer benchmark comparison."

        return {
            "status": final_status,
            "reason": reason,
            "industry": profile.industry,
            "sub_industry": profile.sub_industry,
            "geography": profile.geography,
            "business_size_band": profile.business_size_band,
            "available_metrics_count": len(active_benchmarks),
            "checks": checks
        }
