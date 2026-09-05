"""
services/industry_benchmark.py — Core Industry Benchmarking & Comparison Engine (Step 24 & Patches 1–14).

Adheres to:
1. No fake benchmark data: strictly returns BENCHMARK_UNAVAILABLE when data/parameters are missing.
2. Exact peer matching with explicit broader industry fallback (Patch 16 from prompt):
   - 1. exact sub_industry, industry, geography, size_band
   - 2. exact sub_industry, industry, geography
   - 3. industry, geography, size_band
   - 4. industry, geography (BROADER_INDUSTRY_MATCH)
   - 5. NO_EXACT_PEER_MATCH / BENCHMARK_UNAVAILABLE
3. Zero benchmark mathematical safety (Patch 2 & 11):
   - gap_percentage is None (never 0.0%) when benchmark_value == 0
   - Case A: business > 0, benchmark == 0 -> WORSE_THAN_BENCHMARK, comparison_method = "ZERO_BENCHMARK_NONZERO_BUSINESS"
   - Case B: business == 0, benchmark == 0 -> WITHIN_BENCHMARK, comparison_method = "BOTH_VALUES_ZERO"
4. Decimal arithmetic only (no float precision loss for sustainability numbers).
5. Benchmark version immutability (Patch 10):
   - Persists benchmark_version, source_year, source_type, comparison_method, engine_version = "1.0".
6. Actual data only from posted ledger entries (Patch 7).
7. Test fixture isolation (Patch 4): source_type == "TEST_FIXTURE" filtered unless explicitly requested.
8. Single source of priority truth: does NOT invent priority scores; integrates with Step 22A without overriding.
"""
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_, and_

from backend.app.models.industry_benchmark import (
    BusinessProfile,
    IndustryBenchmark,
    BenchmarkComparison,
)
from backend.app.models.carbon_ledger import CarbonLedgerEntry
from backend.app.services.benchmark_eligibility import BenchmarkEligibilityService

logger = logging.getLogger("senseible-document-ai")

BENCHMARK_ENGINE_VERSION = "1.0"


class IndustryBenchmarkService:
    """
    Deterministic Benchmarking & Comparison Engine.
    """

    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self.engine_version = BENCHMARK_ENGINE_VERSION
        self._last_evaluated: Optional[datetime] = None

    def get_last_evaluated(self) -> Optional[datetime]:
        return self._last_evaluated

    # -----------------------------------------------------------------------
    # Business Actual Aggregation (Actual Posted Ledger Data Only - Patch 7)
    # -----------------------------------------------------------------------

    def extract_business_actuals(
        self,
        db: Session,
        document_id: Optional[int] = None,
        reporting_period: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate verified POSTED carbon ledger entries into deterministic actual totals.
        Returns mapping:
        {
            "total_emissions": {"value": Decimal, "unit": "tCO2e", "count": int},
            "scope_1": {"value": Decimal, "unit": "tCO2e", "count": int},
            "scope_2": {"value": Decimal, "unit": "tCO2e", "count": int},
            "electricity_consumption": {"value": Decimal, "unit": "kWh", "count": int},
            "fuel_consumption": {"value": Decimal, "unit": "Liters", "count": int},
        }
        """
        query = db.query(CarbonLedgerEntry).filter(CarbonLedgerEntry.accounting_status == "POSTED")
        if document_id:
            query = query.filter(CarbonLedgerEntry.document_id == document_id)
        if reporting_period:
            query = query.filter(CarbonLedgerEntry.reporting_period == reporting_period)

        entries = query.all()
        if not entries:
            return {}

        actuals: Dict[str, Dict[str, Any]] = {
            "total_emissions": {"value": Decimal("0.0000"), "unit": "tCO2e", "count": 0, "entries": []},
            "scope_1": {"value": Decimal("0.0000"), "unit": "tCO2e", "count": 0, "entries": []},
            "scope_2": {"value": Decimal("0.0000"), "unit": "tCO2e", "count": 0, "entries": []},
            "electricity_consumption": {"value": Decimal("0.0000"), "unit": "kWh", "count": 0, "entries": []},
            "fuel_consumption": {"value": Decimal("0.0000"), "unit": "Liters", "count": 0, "entries": []},
        }

        for e in entries:
            # calculated_co2e is in kgCO2e or tCO2e based on unit; standard ledger stores kgCO2e
            raw_co2 = Decimal(str(e.calculated_co2e or 0.0))
            if getattr(e, "calculated_co2e_unit", "kgCO2e") == "kgCO2e":
                tco2e = (raw_co2 / Decimal("1000.0")).quantize(Decimal("0.0001"))
            else:
                tco2e = raw_co2.quantize(Decimal("0.0001"))

            scope_str = str(e.scope or "").upper()
            activity_str = str(e.activity_type or "").upper()
            unit_str = str(e.activity_unit or "").lower()
            qty = Decimal(str(e.quantity or 0.0))

            # Total
            actuals["total_emissions"]["value"] += tco2e
            actuals["total_emissions"]["count"] += 1
            actuals["total_emissions"]["entries"].append(e.id)

            # Scope 1 vs Scope 2
            if "1" in scope_str:
                actuals["scope_1"]["value"] += tco2e
                actuals["scope_1"]["count"] += 1
                actuals["scope_1"]["entries"].append(e.id)
            elif "2" in scope_str:
                actuals["scope_2"]["value"] += tco2e
                actuals["scope_2"]["count"] += 1
                actuals["scope_2"]["entries"].append(e.id)

            # Activity consumption: Electricity
            if "ELECTRICITY" in activity_str or "GRID" in activity_str or "kwh" in unit_str:
                actuals["electricity_consumption"]["value"] += qty
                actuals["electricity_consumption"]["count"] += 1
                actuals["electricity_consumption"]["entries"].append(e.id)

            # Activity consumption: Fuel (Diesel / Petrol / LPG)
            if any(f in activity_str for f in ["DIESEL", "FUEL", "PETROL", "LPG", "GAS"]) or "liter" in unit_str or "l" == unit_str:
                actuals["fuel_consumption"]["value"] += qty
                actuals["fuel_consumption"]["count"] += 1
                actuals["fuel_consumption"]["entries"].append(e.id)

        return actuals

    # -----------------------------------------------------------------------
    # Peer Matching Logic (Deterministic Hierarchy - Patch 16 from Prompt)
    # -----------------------------------------------------------------------

    def match_benchmark_for_metric(
        self,
        db: Session,
        metric_name: str,
        profile: BusinessProfile,
        include_fixtures: bool = False
    ) -> Tuple[Optional[IndustryBenchmark], str]:
        """
        Deterministic peer matching order:
        1. Exact sub-industry + industry + geography + size_band
        2. Exact sub-industry + industry + geography
        3. Industry + geography + size_band (Broader match)
        4. Industry + geography (Broader industry match)
        Returns: (matched_benchmark, matching_type)
        matching_type is one of:
        - "EXACT_PEER_MATCH"
        - "BROADER_INDUSTRY_MATCH"
        - "NO_EXACT_PEER_MATCH"
        """
        if not profile.industry or not profile.geography:
            return None, "NO_EXACT_PEER_MATCH"

        base_q = db.query(IndustryBenchmark).filter(
            IndustryBenchmark.metric_name == metric_name,
            IndustryBenchmark.status == "ACTIVE",
            IndustryBenchmark.industry.ilike(profile.industry),
            IndustryBenchmark.geography.ilike(profile.geography),
        )
        if not include_fixtures:
            base_q = base_q.filter(IndustryBenchmark.source_type != "TEST_FIXTURE")

        # 1. Exact sub-industry + size_band
        if profile.sub_industry and profile.business_size_band:
            b1 = base_q.filter(
                IndustryBenchmark.sub_industry.ilike(profile.sub_industry),
                IndustryBenchmark.business_size_band.ilike(profile.business_size_band),
            ).first()
            if b1:
                return b1, "EXACT_PEER_MATCH"

        # 2. Exact sub-industry
        if profile.sub_industry:
            b2 = base_q.filter(
                IndustryBenchmark.sub_industry.ilike(profile.sub_industry)
            ).first()
            if b2:
                return b2, "EXACT_PEER_MATCH"

        # 3. Industry + size_band
        if profile.business_size_band:
            b3 = base_q.filter(
                IndustryBenchmark.business_size_band.ilike(profile.business_size_band)
            ).first()
            if b3:
                return b3, "BROADER_INDUSTRY_MATCH"

        # 4. Industry + geography (broader match)
        b4 = base_q.first()
        if b4:
            return b4, "BROADER_INDUSTRY_MATCH"

        return None, "NO_EXACT_PEER_MATCH"

    # -----------------------------------------------------------------------
    # Zero-Safe Gap & Classification Formulas (Patch 2 & 11)
    # -----------------------------------------------------------------------

    @staticmethod
    def calculate_gap_and_classification(
        business_val: Decimal,
        benchmark_val: Decimal,
        lower_bound: Optional[Decimal] = None,
        upper_bound: Optional[Decimal] = None,
        benchmark_type: str = "ABSOLUTE"
    ) -> Tuple[Decimal, Optional[Decimal], str, str, Optional[str]]:
        """
        Calculate gap, gap_percentage, classification, comparison_method, and limitation.
        Guarantees zero-safe calculation:
        Case A: business_value > 0 and benchmark_value == 0:
            gap = business_value
            gap_percentage = None
            comparison_method = "ZERO_BENCHMARK_NONZERO_BUSINESS"
            classification = "WORSE_THAN_BENCHMARK"
            limitation = "Percentage difference cannot be calculated because the benchmark value is zero."
        Case B: business_value == 0 and benchmark_value == 0:
            gap = 0
            gap_percentage = None
            comparison_method = "BOTH_VALUES_ZERO"
            classification = "WITHIN_BENCHMARK"
            limitation = None
        Case C: Normal nonzero benchmark_value:
            gap = business_value - benchmark_value
            gap_percentage = ((business_value - benchmark_value) / benchmark_value) * 100
        """
        gap = business_val - benchmark_val
        gap_pct: Optional[Decimal] = None
        limitation: Optional[str] = None

        # Zero Benchmark Safety (Patch 2)
        if benchmark_val == Decimal("0.0000") or benchmark_val == Decimal("0"):
            if business_val > Decimal("0"):
                classification = "WORSE_THAN_BENCHMARK"
                comparison_method = "ZERO_BENCHMARK_NONZERO_BUSINESS"
                limitation = "Percentage difference cannot be calculated because the benchmark value is zero."
            elif business_val == Decimal("0"):
                classification = "WITHIN_BENCHMARK"
                comparison_method = "BOTH_VALUES_ZERO"
            else:
                classification = "NOT_COMPARABLE"
                comparison_method = "NEGATIVE_BUSINESS_VALUE"
                limitation = "Negative business sustainability values cannot be compared against zero benchmark."
            return gap, None, classification, comparison_method, limitation

        # Normal nonzero benchmark
        gap_pct = ((business_val - benchmark_val) / benchmark_val) * Decimal("100")
        gap_pct = gap_pct.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        # Classification based on bounds or point benchmark
        if lower_bound is not None and upper_bound is not None:
            comparison_method = "STANDARD_RANGE"
            if business_val < lower_bound:
                classification = "BETTER_THAN_BENCHMARK"
            elif business_val > upper_bound:
                classification = "WORSE_THAN_BENCHMARK"
            else:
                classification = "WITHIN_BENCHMARK"
        else:
            comparison_method = "POINT_COMPARISON"
            if gap < Decimal("0"):
                classification = "BETTER_THAN_BENCHMARK"
            elif gap > Decimal("0"):
                classification = "WORSE_THAN_BENCHMARK"
            else:
                classification = "WITHIN_BENCHMARK"

        return gap, gap_pct, classification, comparison_method, limitation

    # -----------------------------------------------------------------------
    # Evaluation Engine (Deterministic & Idempotent)
    # -----------------------------------------------------------------------

    def evaluate_benchmarks(
        self,
        db: Session,
        reporting_period: Optional[str] = None,
        document_id: Optional[int] = None,
        force_refresh: bool = False,
        include_fixtures: bool = False
    ) -> List[BenchmarkComparison]:
        """
        Evaluate business actuals against active industry benchmarks.
        Idempotent: updates existing comparison records or creates new ones.
        Never rewrites historical records with different benchmark versions (Patch 10).
        """
        profile = db.query(BusinessProfile).first()
        if not profile:
            profile = BenchmarkEligibilityService.get_or_create_default_profile(db)

        # 1. Eligibility Check
        eligibility = BenchmarkEligibilityService.evaluate_eligibility(
            db, profile, document_id, reporting_period, include_fixtures
        )
        if eligibility["status"] in ("BENCHMARK_UNAVAILABLE", "NOT_ELIGIBLE"):
            logger.info(f"Skipping benchmark evaluation: {eligibility['reason']}")
            return []

        # 2. Extract Business Actuals (from POSTED carbon ledger entries only - Patch 7)
        actuals = self.extract_business_actuals(db, document_id, reporting_period)
        if not actuals:
            return []

        # Supported core comparison metrics
        metrics_to_evaluate = [
            ("total_emissions", actuals["total_emissions"]["value"], "tCO2e"),
            ("scope_1", actuals["scope_1"]["value"], "tCO2e"),
            ("scope_2", actuals["scope_2"]["value"], "tCO2e"),
        ]

        if actuals["electricity_consumption"]["count"] > 0:
            metrics_to_evaluate.append(
                ("electricity_consumption", actuals["electricity_consumption"]["value"], "kWh")
            )
        if actuals["fuel_consumption"]["count"] > 0:
            metrics_to_evaluate.append(
                ("fuel_consumption", actuals["fuel_consumption"]["value"], "Liters")
            )

        # Intensity metrics (Patch 1 & 9: require explicit USER_PROVIDED or VERIFIED denominator > 0)
        tot_tco2e = actuals["total_emissions"]["value"]

        # Revenue Intensity (tCO2e / Crore or currency unit)
        if (
            profile.revenue_amount is not None
            and profile.revenue_amount > Decimal("0")
            and profile.revenue_data_status in ("USER_PROVIDED", "VERIFIED")
        ):
            rev_intensity = (tot_tco2e / profile.revenue_amount).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_UP
            )
            unit_label = f"tCO2e/{profile.revenue_currency or 'INR'}"
            metrics_to_evaluate.append(("emissions_intensity_revenue", rev_intensity, unit_label))

        # Employee Intensity (tCO2e / employee)
        if (
            profile.employee_count is not None
            and profile.employee_count > 0
            and profile.employee_data_status in ("USER_PROVIDED", "VERIFIED")
        ):
            emp_intensity = (tot_tco2e / Decimal(str(profile.employee_count))).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_UP
            )
            metrics_to_evaluate.append(("emissions_intensity_employee", emp_intensity, "tCO2e/employee"))

        comparisons: List[BenchmarkComparison] = []
        now = datetime.utcnow()

        for metric_name, business_val, unit in metrics_to_evaluate:
            bench, match_type = self.match_benchmark_for_metric(
                db, metric_name, profile, include_fixtures
            )
            if not bench:
                continue

            bench_val = Decimal(str(bench.benchmark_value))
            low_b = Decimal(str(bench.lower_bound)) if bench.lower_bound is not None else None
            high_b = Decimal(str(bench.upper_bound)) if bench.upper_bound is not None else None

            # Zero-safe calculation (Patch 2 & 11)
            gap, gap_pct, classification, method, limitation = self.calculate_gap_and_classification(
                business_val, bench_val, low_b, high_b, bench.benchmark_type
            )

            # Safe claim explanation (Patch 5)
            if classification == "WORSE_THAN_BENCHMARK":
                explanation = (
                    f"Your measured {metric_name.replace('_', ' ')} of {business_val:.4f} {unit} "
                    f"is above the selected benchmark value of {bench_val:.4f} {unit}."
                )
            elif classification == "BETTER_THAN_BENCHMARK":
                explanation = (
                    f"Your measured {metric_name.replace('_', ' ')} of {business_val:.4f} {unit} "
                    f"is below the selected benchmark value of {bench_val:.4f} {unit}."
                )
            else:
                explanation = (
                    f"Your measured {metric_name.replace('_', ' ')} of {business_val:.4f} {unit} "
                    f"is within the selected benchmark range."
                )

            if match_type == "BROADER_INDUSTRY_MATCH":
                explanation += f" (Note: Evaluated against broader {profile.industry} industry benchmark)."

            # Confidence assessment
            confidence = "HIGH"
            if bench.sample_size and bench.sample_size < 30:
                confidence = "LOW"
            elif match_type == "BROADER_INDUSTRY_MATCH":
                confidence = "MEDIUM"
            if bench.source_type == "USER_PROVIDED":
                confidence = "MEDIUM"

            # Check for existing record to maintain idempotency (reporting_period + metric_name + benchmark_version)
            existing_q = db.query(BenchmarkComparison).filter(
                BenchmarkComparison.metric_name == metric_name,
                BenchmarkComparison.benchmark_version == bench.version,
                BenchmarkComparison.reporting_period == reporting_period,
                BenchmarkComparison.source_document_id == document_id,
            )
            existing = existing_q.first()

            if existing and not force_refresh:
                # Update existing comparison record deterministically
                existing.business_value = business_val
                existing.benchmark_value = bench_val
                existing.lower_bound = low_b
                existing.upper_bound = high_b
                existing.gap = gap
                existing.gap_percentage = gap_pct
                existing.classification = classification
                existing.comparison_method = method
                existing.benchmark_id = bench.id
                existing.benchmark_code = bench.benchmark_code
                existing.benchmark_name = bench.benchmark_name
                existing.source_type = bench.source_type
                existing.source_name = bench.source_name
                existing.source_year = bench.source_year
                existing.data_quality_confidence = confidence
                existing.explanation = explanation
                existing.limitation = limitation
                comparisons.append(existing)
            else:
                if existing and force_refresh:
                    db.delete(existing)
                    db.flush()

                new_comp = BenchmarkComparison(
                    business_scope="DOCUMENT" if document_id else "ORGANIZATION",
                    metric_name=metric_name,
                    metric_unit=unit,
                    business_value=business_val,
                    benchmark_value=bench_val,
                    lower_bound=low_b,
                    upper_bound=high_b,
                    gap=gap,
                    gap_percentage=gap_pct,
                    classification=classification,
                    comparison_method=method,
                    benchmark_id=bench.id,
                    benchmark_code=bench.benchmark_code,
                    benchmark_name=bench.benchmark_name,
                    benchmark_version=bench.version,
                    source_type=bench.source_type,
                    source_name=bench.source_name,
                    source_year=bench.source_year,
                    engine_version=self.engine_version,
                    reporting_period=reporting_period,
                    data_status="ACTUAL_POSTED",
                    data_quality_confidence=confidence,
                    source_document_id=document_id,
                    explanation=explanation,
                    limitation=limitation,
                    created_at=now
                )
                db.add(new_comp)
                comparisons.append(new_comp)

        db.commit()
        for c in comparisons:
            db.refresh(c)

        self._last_evaluated = now
        return comparisons

    # -----------------------------------------------------------------------
    # Insights Generator (Deterministic Rules - Grounded Contract)
    # -----------------------------------------------------------------------

    def generate_benchmark_insights(
        self,
        comparisons: List[BenchmarkComparison],
        profile: Optional[BusinessProfile] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate deterministic insights based on comparison results.
        Categories: ENERGY_GAP, EMISSIONS_GAP, SCOPE_GAP, INTENSITY_GAP,
                    PERFORMANCE_STRENGTH, DATA_COVERAGE, BENCHMARK_LIMITATION.
        """
        insights: List[Dict[str, Any]] = []

        for c in comparisons:
            metric_clean = c.metric_name.replace("_", " ").title()

            # Strength
            if c.classification == "BETTER_THAN_BENCHMARK":
                insights.append({
                    "insight_code": f"STRENGTH_{c.metric_name.upper()}",
                    "category": "PERFORMANCE_STRENGTH",
                    "metric_name": c.metric_name,
                    "title": f"{metric_clean} Below Benchmark",
                    "message": (
                        f"Your measured {c.metric_name.replace('_', ' ')} of {c.business_value:.4f} {c.metric_unit} "
                        f"is below the peer benchmark ({c.benchmark_value:.4f} {c.metric_unit})."
                    ),
                    "recommendation": "Maintain operational controls that contribute to this performance.",
                    "comparison_id": c.id
                })

            # Gaps
            elif c.classification == "WORSE_THAN_BENCHMARK":
                cat = "EMISSIONS_GAP"
                if "electricity" in c.metric_name or "scope_2" in c.metric_name:
                    cat = "ENERGY_GAP"
                elif "intensity" in c.metric_name:
                    cat = "INTENSITY_GAP"

                pct_str = f" (+{c.gap_percentage:.1f}%)" if c.gap_percentage is not None else ""
                insights.append({
                    "insight_code": f"GAP_{c.metric_name.upper()}",
                    "category": cat,
                    "metric_name": c.metric_name,
                    "title": f"{metric_clean} Above Benchmark",
                    "message": (
                        f"Your measured {c.metric_name.replace('_', ' ')} is {c.gap:.4f} {c.metric_unit}{pct_str} "
                        f"above the selected peer benchmark ({c.benchmark_value:.4f} {c.metric_unit})."
                    ),
                    "recommendation": (
                        f"Review {c.metric_name.replace('_', ' ')} activity drivers alongside Step 22A reduction intelligence."
                    ),
                    "comparison_id": c.id
                })

            # Zero-benchmark limitation
            if c.limitation:
                insights.append({
                    "insight_code": f"LIMITATION_{c.metric_name.upper()}",
                    "category": "BENCHMARK_LIMITATION",
                    "metric_name": c.metric_name,
                    "title": f"{metric_clean} Calculation Limitation",
                    "message": c.limitation,
                    "recommendation": "Use absolute gap difference for evaluation.",
                    "comparison_id": c.id
                })

        # Data coverage insight if intensity metrics were excluded
        if profile:
            if profile.revenue_data_status not in ("USER_PROVIDED", "VERIFIED") or not profile.revenue_amount:
                insights.append({
                    "insight_code": "COVERAGE_REVENUE_INTENSITY",
                    "category": "DATA_COVERAGE",
                    "metric_name": "emissions_intensity_revenue",
                    "title": "Revenue Intensity Uncalculated",
                    "message": "Emissions intensity per revenue cannot be compared because verified revenue is not provided.",
                    "recommendation": "Provide verified annual revenue in business profile to enable intensity benchmarking.",
                    "comparison_id": None
                })
            if profile.employee_data_status not in ("USER_PROVIDED", "VERIFIED") or not profile.employee_count:
                insights.append({
                    "insight_code": "COVERAGE_EMPLOYEE_INTENSITY",
                    "category": "DATA_COVERAGE",
                    "metric_name": "emissions_intensity_employee",
                    "title": "Employee Intensity Uncalculated",
                    "message": "Emissions intensity per employee cannot be compared because employee count is not provided.",
                    "recommendation": "Provide verified employee count in business profile to enable intensity benchmarking.",
                    "comparison_id": None
                })

        return insights

    # -----------------------------------------------------------------------
    # Summary Endpoint Data Provider
    # -----------------------------------------------------------------------

    def get_benchmark_summary(
        self,
        db: Session,
        document_id: Optional[int] = None,
        reporting_period: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Produce top-level summary for the Industry Intelligence page and dashboard.
        """
        profile = db.query(BusinessProfile).first()
        if not profile:
            profile = BenchmarkEligibilityService.get_or_create_default_profile(db)

        eligibility = BenchmarkEligibilityService.evaluate_eligibility(
            db, profile, document_id, reporting_period
        )

        query = db.query(BenchmarkComparison)
        if document_id:
            query = query.filter(BenchmarkComparison.source_document_id == document_id)
        if reporting_period:
            query = query.filter(BenchmarkComparison.reporting_period == reporting_period)

        comparisons = query.order_by(desc(BenchmarkComparison.gap)).all()

        better_count = sum(1 for c in comparisons if c.classification == "BETTER_THAN_BENCHMARK")
        within_count = sum(1 for c in comparisons if c.classification == "WITHIN_BENCHMARK")
        worse_count = sum(1 for c in comparisons if c.classification == "WORSE_THAN_BENCHMARK")

        top_gaps = [c for c in comparisons if c.classification == "WORSE_THAN_BENCHMARK"][:3]
        strengths = [c for c in comparisons if c.classification == "BETTER_THAN_BENCHMARK"][:3]

        insights = self.generate_benchmark_insights(comparisons, profile)

        # Peer matching classification overall
        peer_match = "EXACT_PEER_MATCH"
        if profile.industry and not profile.sub_industry:
            peer_match = "BROADER_INDUSTRY_MATCH"
        if eligibility["status"] == "BENCHMARK_UNAVAILABLE":
            peer_match = "BENCHMARK_UNAVAILABLE"

        confidence = "HIGH"
        if any(c.data_quality_confidence == "LOW" for c in comparisons):
            confidence = "LOW"
        elif any(c.data_quality_confidence == "MEDIUM" for c in comparisons) or peer_match == "BROADER_INDUSTRY_MATCH":
            confidence = "MEDIUM"
        if not comparisons:
            confidence = "INSUFFICIENT"

        # Latest benchmark source metadata
        first_comp = comparisons[0] if comparisons else None

        return {
            "status": eligibility["status"],
            "benchmark_version": first_comp.benchmark_version if first_comp else "1.0",
            "source_year": first_comp.source_year if first_comp else None,
            "source_type": first_comp.source_type if first_comp else None,
            "last_evaluated": self._last_evaluated or (first_comp.created_at if first_comp else None),
            "eligible": eligibility["status"] in ("ELIGIBLE", "PARTIALLY_ELIGIBLE"),
            "eligibility_reason": eligibility["reason"],
            "metrics_compared": len(comparisons),
            "better_count": better_count,
            "within_count": within_count,
            "worse_count": worse_count,
            "comparisons": comparisons,
            "top_gaps": top_gaps,
            "strengths": strengths,
            "insights": insights,
            "data_quality_confidence": confidence,
            "peer_matching_type": peer_match,
        }


industry_benchmark_service = IndustryBenchmarkService()
