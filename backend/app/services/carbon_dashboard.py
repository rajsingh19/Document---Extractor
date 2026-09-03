"""
services/carbon_dashboard.py — Deterministic Carbon Footprint Dashboard Analytics Service (Step 15).

Builds analytical, business-facing insights exclusively from POSTED CarbonLedgerEntry records.
ZERO LLM calls. ZERO recalculation of emissions.
Strict Python Decimal arithmetic with ROUND_HALF_UP.
Never fabricates missing periods, dates, or zeros for unavailable scopes.
"""
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.models.carbon_ledger import CarbonLedgerEntry
from backend.app.models.carbon_calculation import CarbonCalculation
from backend.app.models.activity_data import ActivityData
from backend.app.models.document import Document
from backend.app.models.sustainability_metric import SustainabilityMetric
from backend.app.schemas.carbon_dashboard import (
    CarbonDashboardSummary,
    CarbonScopeItem,
    CarbonScopeBreakdown,
    CarbonCategoryItem,
    CarbonCategoryBreakdown,
    CarbonActivityItem,
    CarbonActivityBreakdown,
    CarbonDocumentContributionItem,
    CarbonDocumentContribution,
    CarbonHistoricalPoint,
    CarbonYearPoint,
    CarbonPeriodComparison,
    CarbonTrendsResponse,
    CarbonDataCoverage,
    CarbonTopSourceItem,
    CarbonTopSourcesResponse,
    DashboardReconciliationItem,
    CarbonDashboardReconciliation,
    CarbonDashboardResponse,
)

logger = logging.getLogger("senseible-carbon-dashboard-service")


class CarbonDashboardService:
    """
    Deterministic Analytics Service for Carbon Footprint Dashboard.
    Operates strictly on top of the Carbon Accounting Ledger.
    """

    def __init__(self):
        self.dashboard_version = "1.0"

    def _get_base_query(
        self,
        db: Session,
        reporting_year: Optional[int] = None,
        reporting_period: Optional[str] = None,
        scope: Optional[str] = None,
        category: Optional[str] = None,
        document_id: Optional[int] = None,
    ):
        """Builds a filtered SQLAlchemy query on CarbonLedgerEntry."""
        query = db.query(CarbonLedgerEntry)
        if document_id is not None:
            query = query.filter(CarbonLedgerEntry.document_id == document_id)
        if reporting_year is not None:
            query = query.filter(CarbonLedgerEntry.reporting_year == reporting_year)
        if reporting_period:
            query = query.filter(CarbonLedgerEntry.reporting_period == reporting_period)
        if scope:
            query = query.filter(CarbonLedgerEntry.scope == scope.strip().upper())
        if category:
            query = query.filter(CarbonLedgerEntry.category == category.strip().upper())
        return query

    def get_dashboard_summary(
        self,
        db: Session,
        reporting_year: Optional[int] = None,
        reporting_period: Optional[str] = None,
        scope: Optional[str] = None,
        category: Optional[str] = None,
        document_id: Optional[int] = None,
    ) -> CarbonDashboardSummary:
        """
        Compute high-level KPI summary from POSTED ledger entries.
        """
        query = self._get_base_query(
            db, reporting_year, reporting_period, scope, category, document_id
        )
        all_entries = query.all()

        active_entries = [e for e in all_entries if e.accounting_status != "SUPERSEDED"]
        posted_entries = [e for e in active_entries if e.accounting_status == "POSTED"]

        posted_count = len(posted_entries)
        excluded_count = sum(1 for e in active_entries if e.accounting_status == "EXCLUDED")
        superseded_count = sum(1 for e in all_entries if e.accounting_status == "SUPERSEDED")

        scope_1_kg = Decimal("0.0")
        scope_2_kg = Decimal("0.0")
        scope_3_kg = Decimal("0.0")
        total_kg = Decimal("0.0")

        has_s1 = False
        has_s2 = False
        has_s3 = False

        docs = set()
        activities = set()
        periods = set()

        for e in posted_entries:
            if e.calculated_co2e is not None:
                val = Decimal(str(e.calculated_co2e))
                total_kg += val
                if e.scope == "SCOPE_1":
                    scope_1_kg += val
                    has_s1 = True
                elif e.scope == "SCOPE_2":
                    scope_2_kg += val
                    has_s2 = True
                elif e.scope == "SCOPE_3":
                    scope_3_kg += val
                    has_s3 = True

            if e.document_id:
                docs.add(e.document_id)
            if e.activity_type:
                activities.add(e.activity_type)
            if e.reporting_period:
                periods.add(e.reporting_period)

        # Convert to metric tonnes (tCO2e) with 1 tCO2e = 1000 kgCO2e
        total_t = (total_kg / Decimal("1000")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP) if posted_count > 0 else None
        s1_t = (scope_1_kg / Decimal("1000")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP) if has_s1 else None
        s2_t = (scope_2_kg / Decimal("1000")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP) if has_s2 else None
        s3_t = (scope_3_kg / Decimal("1000")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP) if has_s3 else None

        sorted_periods = sorted(list(periods))
        latest_p = sorted_periods[-1] if sorted_periods else None

        return CarbonDashboardSummary(
            total_calculated_co2e_kg=float(total_kg) if posted_count > 0 else None,
            total_calculated_co2e_t=float(total_t) if total_t is not None else None,
            total_calculated_co2e_unit="tCO2e",
            scope_1_co2e_kg=float(scope_1_kg) if has_s1 else None,
            scope_1_co2e_t=float(s1_t) if s1_t is not None else None,
            scope_2_co2e_kg=float(scope_2_kg) if has_s2 else None,
            scope_2_co2e_t=float(s2_t) if s2_t is not None else None,
            scope_3_co2e_kg=float(scope_3_kg) if has_s3 else None,
            scope_3_co2e_t=float(s3_t) if s3_t is not None else None,
            posted_entry_count=posted_count,
            excluded_entry_count=excluded_count,
            superseded_entry_count=superseded_count,
            document_count=len(docs),
            activity_count=len(activities),
            reporting_period_count=len(periods),
            latest_reporting_period=latest_p,
        )

    def get_scope_breakdown(
        self,
        db: Session,
        reporting_year: Optional[int] = None,
        reporting_period: Optional[str] = None,
        scope: Optional[str] = None,
        category: Optional[str] = None,
        document_id: Optional[int] = None,
    ) -> CarbonScopeBreakdown:
        """
        Compute Scope 1, Scope 2, Scope 3 breakdown from POSTED ledger entries.
        """
        query = self._get_base_query(
            db, reporting_year, reporting_period, scope, category, document_id
        ).filter(CarbonLedgerEntry.accounting_status == "POSTED")
        entries = query.all()

        scope_map: Dict[str, Tuple[Decimal, int]] = {
            "SCOPE_1": (Decimal("0.0"), 0),
            "SCOPE_2": (Decimal("0.0"), 0),
            "SCOPE_3": (Decimal("0.0"), 0),
        }
        total_kg = Decimal("0.0")

        for e in entries:
            if e.calculated_co2e is not None and e.scope in scope_map:
                val = Decimal(str(e.calculated_co2e))
                total_kg += val
                cur_val, cur_cnt = scope_map[e.scope]
                scope_map[e.scope] = (cur_val + val, cur_cnt + 1)

        total_t = (total_kg / Decimal("1000")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        items: List[CarbonScopeItem] = []
        scope_labels = {
            "SCOPE_1": "Scope 1 (Direct Fuel & Combustion)",
            "SCOPE_2": "Scope 2 (Indirect Purchased Electricity)",
            "SCOPE_3": "Scope 3 (Value Chain & Upstream/Downstream)",
        }

        for sc in ["SCOPE_1", "SCOPE_2", "SCOPE_3"]:
            val_kg, cnt = scope_map[sc]
            val_t = (val_kg / Decimal("1000")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            pct = None
            if total_kg > Decimal("0.0") and cnt > 0:
                pct = float(((val_kg / total_kg) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

            items.append(
                CarbonScopeItem(
                    scope=sc,
                    scope_label=scope_labels[sc],
                    co2e_kg=float(val_kg),
                    co2e_t=float(val_t),
                    percentage_of_total=pct,
                    entry_count=cnt,
                )
            )

        return CarbonScopeBreakdown(
            total_co2e_kg=float(total_kg),
            total_co2e_t=float(total_t),
            items=items,
        )

    def get_category_breakdown(
        self,
        db: Session,
        reporting_year: Optional[int] = None,
        reporting_period: Optional[str] = None,
        scope: Optional[str] = None,
        category: Optional[str] = None,
        document_id: Optional[int] = None,
    ) -> CarbonCategoryBreakdown:
        """
        Break down emissions by category (ENERGY, FUEL, TRANSPORT, WATER, WASTE, OTHER).
        """
        query = self._get_base_query(
            db, reporting_year, reporting_period, scope, category, document_id
        ).filter(CarbonLedgerEntry.accounting_status == "POSTED")
        entries = query.all()

        cat_map: Dict[str, Tuple[Decimal, int]] = {}
        total_kg = Decimal("0.0")

        for e in entries:
            if e.calculated_co2e is not None:
                val = Decimal(str(e.calculated_co2e))
                total_kg += val
                c_name = (e.category or "OTHER").upper()
                cur_val, cur_cnt = cat_map.get(c_name, (Decimal("0.0"), 0))
                cat_map[c_name] = (cur_val + val, cur_cnt + 1)

        total_t = (total_kg / Decimal("1000")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        items: List[CarbonCategoryItem] = []
        for cat_name, (val_kg, cnt) in sorted(cat_map.items(), key=lambda x: x[1][0], reverse=True):
            val_t = (val_kg / Decimal("1000")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            pct = None
            if total_kg > Decimal("0.0"):
                pct = float(((val_kg / total_kg) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            items.append(
                CarbonCategoryItem(
                    category=cat_name,
                    co2e_kg=float(val_kg),
                    co2e_t=float(val_t),
                    percentage_of_total=pct,
                    entry_count=cnt,
                )
            )

        return CarbonCategoryBreakdown(
            total_co2e_kg=float(total_kg),
            total_co2e_t=float(total_t),
            items=items,
        )

    def get_activity_breakdown(
        self,
        db: Session,
        reporting_year: Optional[int] = None,
        reporting_period: Optional[str] = None,
        scope: Optional[str] = None,
        category: Optional[str] = None,
        document_id: Optional[int] = None,
    ) -> CarbonActivityBreakdown:
        """
        Break down emissions by specific activity type.
        """
        query = self._get_base_query(
            db, reporting_year, reporting_period, scope, category, document_id
        ).filter(CarbonLedgerEntry.accounting_status == "POSTED")
        entries = query.all()

        act_map: Dict[str, Dict[str, Any]] = {}
        total_kg = Decimal("0.0")

        for e in entries:
            if e.calculated_co2e is not None:
                val = Decimal(str(e.calculated_co2e))
                total_kg += val
                act = e.activity_type
                if act not in act_map:
                    act_map[act] = {
                        "category": (e.category or "OTHER").upper(),
                        "scope": e.scope,
                        "co2e_kg": Decimal("0.0"),
                        "count": 0,
                    }
                act_map[act]["co2e_kg"] += val
                act_map[act]["count"] += 1

        items: List[CarbonActivityItem] = []
        for act_name, data in sorted(act_map.items(), key=lambda x: x[1]["co2e_kg"], reverse=True):
            val_kg = data["co2e_kg"]
            val_t = (val_kg / Decimal("1000")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            pct = None
            if total_kg > Decimal("0.0"):
                pct = float(((val_kg / total_kg) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            items.append(
                CarbonActivityItem(
                    activity_type=act_name,
                    category=data["category"],
                    scope=data["scope"],
                    co2e_kg=float(val_kg),
                    co2e_t=float(val_t),
                    percentage_of_total=pct,
                    entry_count=data["count"],
                )
            )

        return CarbonActivityBreakdown(items=items)

    def get_document_contributions(
        self,
        db: Session,
        reporting_year: Optional[int] = None,
        reporting_period: Optional[str] = None,
        scope: Optional[str] = None,
        category: Optional[str] = None,
        document_id: Optional[int] = None,
    ) -> CarbonDocumentContribution:
        """
        Aggregate posted emissions by document and sort descending.
        """
        query = self._get_base_query(
            db, reporting_year, reporting_period, scope, category, document_id
        ).filter(CarbonLedgerEntry.accounting_status == "POSTED")
        entries = query.all()

        doc_map: Dict[int, Dict[str, Any]] = {}
        total_kg = Decimal("0.0")

        for e in entries:
            if e.document_id and e.calculated_co2e is not None:
                did = e.document_id
                val = Decimal(str(e.calculated_co2e))
                total_kg += val

                if did not in doc_map:
                    doc_map[did] = {
                        "reporting_period": e.reporting_period,
                        "reporting_year": e.reporting_year,
                        "total_kg": Decimal("0.0"),
                        "scope_1_kg": Decimal("0.0"),
                        "scope_2_kg": Decimal("0.0"),
                        "scope_3_kg": Decimal("0.0"),
                        "has_s1": False,
                        "has_s2": False,
                        "has_s3": False,
                        "count": 0,
                    }
                doc_map[did]["total_kg"] += val
                doc_map[did]["count"] += 1
                if e.scope == "SCOPE_1":
                    doc_map[did]["scope_1_kg"] += val
                    doc_map[did]["has_s1"] = True
                elif e.scope == "SCOPE_2":
                    doc_map[did]["scope_2_kg"] += val
                    doc_map[did]["has_s2"] = True
                elif e.scope == "SCOPE_3":
                    doc_map[did]["scope_3_kg"] += val
                    doc_map[did]["has_s3"] = True

        # Resolve document filenames / company names
        doc_ids = list(doc_map.keys())
        doc_records = db.query(Document).filter(Document.id.in_(doc_ids)).all() if doc_ids else []
        name_lookup = {d.id: (d.company_name or d.original_filename or d.filename or f"Document #{d.id}") for d in doc_records}

        items: List[CarbonDocumentContributionItem] = []
        for did, data in sorted(doc_map.items(), key=lambda x: x[1]["total_kg"], reverse=True):
            tot_kg = data["total_kg"]
            tot_t = (tot_kg / Decimal("1000")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            s1_t = (data["scope_1_kg"] / Decimal("1000")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP) if data["has_s1"] else None
            s2_t = (data["scope_2_kg"] / Decimal("1000")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP) if data["has_s2"] else None
            s3_t = (data["scope_3_kg"] / Decimal("1000")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP) if data["has_s3"] else None

            pct = None
            if total_kg > Decimal("0.0"):
                pct = float(((tot_kg / total_kg) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

            items.append(
                CarbonDocumentContributionItem(
                    document_id=did,
                    document_name=name_lookup.get(did, f"Document #{did}"),
                    reporting_period=data["reporting_period"],
                    reporting_year=data["reporting_year"],
                    total_co2e_kg=float(tot_kg),
                    total_co2e_t=float(tot_t),
                    scope_1_t=float(s1_t) if s1_t is not None else None,
                    scope_2_t=float(s2_t) if s2_t is not None else None,
                    scope_3_t=float(s3_t) if s3_t is not None else None,
                    percentage_of_total=pct,
                    posted_records=data["count"],
                )
            )

        return CarbonDocumentContribution(
            total_documents=len(items),
            items=items,
        )

    def get_trends(
        self,
        db: Session,
        reporting_year: Optional[int] = None,
        reporting_period: Optional[str] = None,
        scope: Optional[str] = None,
        category: Optional[str] = None,
        document_id: Optional[int] = None,
    ) -> CarbonTrendsResponse:
        """
        Historical trend analytics by reporting period and reporting year.
        Strictly plots only actual periods from database; never fabricates missing periods.
        """
        query = self._get_base_query(
            db, reporting_year, reporting_period, scope, category, document_id
        ).filter(CarbonLedgerEntry.accounting_status == "POSTED")
        entries = query.all()

        period_map: Dict[str, Dict[str, Any]] = {}
        year_map: Dict[int, Dict[str, Any]] = {}

        for e in entries:
            if e.calculated_co2e is not None:
                val = Decimal(str(e.calculated_co2e))

                # Period aggregation
                if e.reporting_period:
                    p = e.reporting_period
                    if p not in period_map:
                        period_map[p] = {
                            "total_kg": Decimal("0.0"),
                            "scope_1_kg": Decimal("0.0"),
                            "scope_2_kg": Decimal("0.0"),
                            "scope_3_kg": Decimal("0.0"),
                            "has_s1": False,
                            "has_s2": False,
                            "has_s3": False,
                            "count": 0,
                        }
                    period_map[p]["total_kg"] += val
                    period_map[p]["count"] += 1
                    if e.scope == "SCOPE_1":
                        period_map[p]["scope_1_kg"] += val
                        period_map[p]["has_s1"] = True
                    elif e.scope == "SCOPE_2":
                        period_map[p]["scope_2_kg"] += val
                        period_map[p]["has_s2"] = True
                    elif e.scope == "SCOPE_3":
                        period_map[p]["scope_3_kg"] += val
                        period_map[p]["has_s3"] = True

                # Year aggregation
                if e.reporting_year is not None:
                    y = e.reporting_year
                    if y not in year_map:
                        year_map[y] = {
                            "total_kg": Decimal("0.0"),
                            "scope_1_kg": Decimal("0.0"),
                            "scope_2_kg": Decimal("0.0"),
                            "scope_3_kg": Decimal("0.0"),
                            "has_s1": False,
                            "has_s2": False,
                            "has_s3": False,
                            "count": 0,
                        }
                    year_map[y]["total_kg"] += val
                    year_map[y]["count"] += 1
                    if e.scope == "SCOPE_1":
                        year_map[y]["scope_1_kg"] += val
                        year_map[y]["has_s1"] = True
                    elif e.scope == "SCOPE_2":
                        year_map[y]["scope_2_kg"] += val
                        year_map[y]["has_s2"] = True
                    elif e.scope == "SCOPE_3":
                        year_map[y]["scope_3_kg"] += val
                        year_map[y]["has_s3"] = True

        # Build chronological period points
        periods: List[CarbonHistoricalPoint] = []
        for p_name in sorted(period_map.keys()):
            data = period_map[p_name]
            tot_kg = data["total_kg"]
            tot_t = (tot_kg / Decimal("1000")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            s1_t = (data["scope_1_kg"] / Decimal("1000")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP) if data["has_s1"] else None
            s2_t = (data["scope_2_kg"] / Decimal("1000")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP) if data["has_s2"] else None
            s3_t = (data["scope_3_kg"] / Decimal("1000")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP) if data["has_s3"] else None

            periods.append(
                CarbonHistoricalPoint(
                    reporting_period=p_name,
                    total_co2e_kg=float(tot_kg),
                    total_co2e_t=float(tot_t),
                    scope_1_kg=float(data["scope_1_kg"]) if data["has_s1"] else None,
                    scope_1_t=float(s1_t) if s1_t is not None else None,
                    scope_2_kg=float(data["scope_2_kg"]) if data["has_s2"] else None,
                    scope_2_t=float(s2_t) if s2_t is not None else None,
                    scope_3_kg=float(data["scope_3_kg"]) if data["has_s3"] else None,
                    scope_3_t=float(s3_t) if s3_t is not None else None,
                    entry_count=data["count"],
                )
            )

        # Build chronological year points
        years: List[CarbonYearPoint] = []
        for y_num in sorted(year_map.keys()):
            data = year_map[y_num]
            tot_kg = data["total_kg"]
            tot_t = (tot_kg / Decimal("1000")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            s1_t = (data["scope_1_kg"] / Decimal("1000")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP) if data["has_s1"] else None
            s2_t = (data["scope_2_kg"] / Decimal("1000")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP) if data["has_s2"] else None
            s3_t = (data["scope_3_kg"] / Decimal("1000")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP) if data["has_s3"] else None

            years.append(
                CarbonYearPoint(
                    year=y_num,
                    total_co2e_kg=float(tot_kg),
                    total_co2e_t=float(tot_t),
                    scope_1_t=float(s1_t) if s1_t is not None else None,
                    scope_2_t=float(s2_t) if s2_t is not None else None,
                    scope_3_t=float(s3_t) if s3_t is not None else None,
                    entry_count=data["count"],
                )
            )

        # Period Comparison Logic
        comparison: CarbonPeriodComparison
        if len(periods) >= 2:
            curr = periods[-1]
            prev = periods[-2]

            curr_t = Decimal(str(curr.total_co2e_t))
            prev_t = Decimal(str(prev.total_co2e_t))
            abs_diff = (curr_t - prev_t).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

            pct_diff = None
            if prev_t > Decimal("0.0"):
                pct_diff = float(((abs_diff / prev_t) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

            msg = f"{abs_diff:+f} tCO2e change from {prev.reporting_period} to {curr.reporting_period}"
            comparison = CarbonPeriodComparison(
                comparison_available=True,
                current_period=curr.reporting_period,
                previous_period=prev.reporting_period,
                current_co2e_t=float(curr_t),
                previous_co2e_t=float(prev_t),
                absolute_change_t=float(abs_diff),
                percentage_change=pct_diff,
                message=msg,
            )
        elif len(periods) == 1:
            comparison = CarbonPeriodComparison(
                comparison_available=False,
                current_period=periods[0].reporting_period,
                current_co2e_t=periods[0].total_co2e_t,
                message="More reporting periods are needed to show a trend.",
            )
        else:
            comparison = CarbonPeriodComparison(
                comparison_available=False,
                message="No posted reporting periods available for trend analysis.",
            )

        return CarbonTrendsResponse(
            periods=periods,
            years=years,
            comparison=comparison,
        )

    def get_data_coverage(
        self,
        db: Session,
        document_id: Optional[int] = None,
    ) -> CarbonDataCoverage:
        """
        Data coverage and calculation audit quality indicators.
        """
        # ActivityData count
        act_query = db.query(ActivityData)
        if document_id is not None:
            act_query = act_query.filter(ActivityData.document_id == document_id)
        total_acts = act_query.count()

        # CarbonCalculation query
        calc_query = db.query(CarbonCalculation)
        if document_id is not None:
            calc_query = calc_query.filter(CarbonCalculation.document_id == document_id)
        all_calcs = calc_query.all()

        calc_count = sum(1 for c in all_calcs if c.status == "CALCULATED")
        no_factor_count = sum(1 for c in all_calcs if c.status == "NO_FACTOR")
        ineligible_count = sum(1 for c in all_calcs if c.status == "INELIGIBLE")
        mult_factors_count = sum(1 for c in all_calcs if c.status == "MULTIPLE_FACTORS")
        invalid_count = sum(1 for c in all_calcs if c.status in ["INVALID_ACTIVITY", "UNSUPPORTED_UNIT", "ERROR"])
        missing_geo_count = sum(1 for c in all_calcs if c.status == "MISSING_GEOGRAPHY")
        missing_yr_count = sum(1 for c in all_calcs if c.status == "MISSING_YEAR")

        # CarbonLedgerEntry query
        led_query = db.query(CarbonLedgerEntry)
        if document_id is not None:
            led_query = led_query.filter(CarbonLedgerEntry.document_id == document_id)
        all_ledgers = led_query.all()

        active_ledgers = [e for e in all_ledgers if e.accounting_status != "SUPERSEDED"]
        posted_count = sum(1 for e in active_ledgers if e.accounting_status == "POSTED")
        excluded_count = sum(1 for e in active_ledgers if e.accounting_status == "EXCLUDED")
        superseded_count = sum(1 for e in all_ledgers if e.accounting_status == "SUPERSEDED")

        # Build detailed unresolved items list for UI transparency
        unresolved_items: List[Dict[str, Any]] = []
        for c in all_calcs:
            if c.status != "CALCULATED":
                unresolved_items.append({
                    "calculation_id": c.id,
                    "activity_data_id": c.activity_data_id,
                    "activity_type": c.activity_type,
                    "quantity": float(c.quantity) if c.quantity is not None else None,
                    "unit": c.activity_unit,
                    "status": c.status,
                    "reason": c.calculation_reason,
                    "source_field": c.source_field,
                })

        return CarbonDataCoverage(
            total_activity_records=total_acts,
            calculated_records=calc_count,
            posted_ledger_records=posted_count,
            excluded_records=excluded_count,
            superseded_records=superseded_count,
            no_factor_records=no_factor_count,
            ineligible_records=ineligible_count,
            multiple_factor_records=mult_factors_count,
            invalid_records=invalid_count,
            missing_geography_records=missing_geo_count,
            missing_year_records=missing_yr_count,
            unresolved_items=unresolved_items,
            notice="Excluded records are not treated as zero emissions.",
        )

    def get_top_sources(
        self,
        db: Session,
        limit: int = 5,
        reporting_year: Optional[int] = None,
        reporting_period: Optional[str] = None,
        scope: Optional[str] = None,
        category: Optional[str] = None,
        document_id: Optional[int] = None,
    ) -> CarbonTopSourcesResponse:
        """
        Rank top emission sources from POSTED ledger entries.
        """
        query = self._get_base_query(
            db, reporting_year, reporting_period, scope, category, document_id
        ).filter(
            CarbonLedgerEntry.accounting_status == "POSTED",
            CarbonLedgerEntry.calculated_co2e.isnot(None)
        )
        entries = query.order_by(desc(CarbonLedgerEntry.calculated_co2e)).all()

        total_kg = sum((Decimal(str(e.calculated_co2e)) for e in entries), Decimal("0.0"))

        doc_ids = list({e.document_id for e in entries if e.document_id})
        doc_records = db.query(Document).filter(Document.id.in_(doc_ids)).all() if doc_ids else []
        name_lookup = {d.id: (d.company_name or d.original_filename or d.filename or f"Doc #{d.id}") for d in doc_records}

        top_slice = entries[:limit]
        items: List[CarbonTopSourceItem] = []

        for idx, e in enumerate(top_slice, 1):
            val_kg = Decimal(str(e.calculated_co2e))
            val_t = (val_kg / Decimal("1000")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            pct = None
            if total_kg > Decimal("0.0"):
                pct = float(((val_kg / total_kg) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

            items.append(
                CarbonTopSourceItem(
                    rank=idx,
                    activity_type=e.activity_type,
                    category=(e.category or "OTHER").upper(),
                    scope=e.scope,
                    co2e_kg=float(val_kg),
                    co2e_t=float(val_t),
                    percentage_of_total=pct,
                    document_id=e.document_id,
                    document_name=name_lookup.get(e.document_id) if e.document_id else None,
                )
            )

        return CarbonTopSourcesResponse(items=items)

    def get_reconciliation(
        self,
        db: Session,
        document_id: Optional[int] = None,
    ) -> CarbonDashboardReconciliation:
        """
        High-level dashboard reconciliation between extracted emissions and calculated/posted ledger footprint.
        """
        # Extracted metrics from SustainabilityMetric
        metric_query = db.query(SustainabilityMetric)
        if document_id is not None:
            metric_query = metric_query.filter(SustainabilityMetric.document_id == document_id)
        metrics = metric_query.all()

        ext_s1_t = None
        ext_s2_t = None
        ext_tot_t = None

        for m in metrics:
            if m.metric_type == "scope_1_emissions" and m.value is not None:
                ext_s1_t = (ext_s1_t or Decimal("0.0")) + Decimal(str(m.value))
            elif m.metric_type == "scope_2_emissions" and m.value is not None:
                ext_s2_t = (ext_s2_t or Decimal("0.0")) + Decimal(str(m.value))
            elif m.metric_type == "total_ghg_emissions" and m.value is not None:
                ext_tot_t = (ext_tot_t or Decimal("0.0")) + Decimal(str(m.value))

        # Fallback to Document total_emissions_tco2e if no total metric found
        if ext_tot_t is None and document_id is not None:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc and doc.total_emissions_tco2e is not None:
                ext_tot_t = Decimal(str(doc.total_emissions_tco2e))

        # Calculated & Posted metrics from CarbonLedgerEntry
        summary = self.get_dashboard_summary(db, document_id=document_id)

        calc_s1_t = Decimal(str(summary.scope_1_co2e_t)) if summary.scope_1_co2e_t is not None else None
        calc_s2_t = Decimal(str(summary.scope_2_co2e_t)) if summary.scope_2_co2e_t is not None else None
        calc_tot_t = Decimal(str(summary.total_calculated_co2e_t)) if summary.total_calculated_co2e_t is not None else None

        items: List[DashboardReconciliationItem] = []

        # Scope 1 comparison item
        items.append(self._build_recon_item("Scope 1 (Direct Fuel)", ext_s1_t, calc_s1_t))
        # Scope 2 comparison item
        items.append(self._build_recon_item("Scope 2 (Electricity)", ext_s2_t, calc_s2_t))
        # Total comparison item
        items.append(self._build_recon_item("Total GHG Footprint", ext_tot_t, calc_tot_t))

        # Overall difference
        diff_tot_t = None
        overall_status = "NO_DATA"
        if ext_tot_t is not None and calc_tot_t is not None:
            diff_tot_t = (calc_tot_t - ext_tot_t).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            overall_status = "MATCH" if abs(diff_tot_t) <= Decimal("0.0001") else "DIFFERENCE"
        elif ext_tot_t is not None:
            overall_status = "EXTRACTED_ONLY"
        elif calc_tot_t is not None:
            overall_status = "CALCULATED_ONLY"

        return CarbonDashboardReconciliation(
            total_extracted_t=float(ext_tot_t) if ext_tot_t is not None else None,
            total_calculated_t=float(calc_tot_t) if calc_tot_t is not None else None,
            difference_t=float(diff_tot_t) if diff_tot_t is not None else None,
            overall_status=overall_status,
            items=items,
        )

    def _build_recon_item(
        self,
        label: str,
        ext_t: Optional[Decimal],
        calc_t: Optional[Decimal]
    ) -> DashboardReconciliationItem:
        """Helper to construct a DashboardReconciliationItem."""
        if ext_t is None and calc_t is None:
            return DashboardReconciliationItem(
                scope_or_metric=label,
                extracted_value_t=None,
                calculated_value_t=None,
                difference_t=None,
                status="NO_DATA",
                notes="Neither extracted nor calculated emission data is available.",
            )
        if ext_t is not None and calc_t is None:
            return DashboardReconciliationItem(
                scope_or_metric=label,
                extracted_value_t=float(ext_t),
                calculated_value_t=None,
                difference_t=None,
                status="EXTRACTED_ONLY",
                notes="Present in document extraction; no calculated ledger entry posted.",
            )
        if ext_t is None and calc_t is not None:
            return DashboardReconciliationItem(
                scope_or_metric=label,
                extracted_value_t=None,
                calculated_value_t=float(calc_t),
                difference_t=None,
                status="CALCULATED_ONLY",
                notes="Calculated and posted from activity data; not reported in document metadata.",
            )

        diff = (calc_t - ext_t).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        status = "MATCH" if abs(diff) <= Decimal("0.0001") else "DIFFERENCE"
        notes = "Values match within precision tolerance." if status == "MATCH" else f"Variance of {diff:+f} tCO2e."

        return DashboardReconciliationItem(
            scope_or_metric=label,
            extracted_value_t=float(ext_t),
            calculated_value_t=float(calc_t),
            difference_t=float(diff),
            status=status,
            notes=notes,
        )

    def get_full_dashboard(
        self,
        db: Session,
        reporting_year: Optional[int] = None,
        reporting_period: Optional[str] = None,
        scope: Optional[str] = None,
        category: Optional[str] = None,
        document_id: Optional[int] = None,
    ) -> CarbonDashboardResponse:
        """
        Assemble the complete carbon footprint dashboard payload.
        """
        summary = self.get_dashboard_summary(
            db, reporting_year, reporting_period, scope, category, document_id
        )
        scopes = self.get_scope_breakdown(
            db, reporting_year, reporting_period, scope, category, document_id
        )
        categories = self.get_category_breakdown(
            db, reporting_year, reporting_period, scope, category, document_id
        )
        activities = self.get_activity_breakdown(
            db, reporting_year, reporting_period, scope, category, document_id
        )
        documents = self.get_document_contributions(
            db, reporting_year, reporting_period, scope, category, document_id
        )
        trends = self.get_trends(
            db, reporting_year, reporting_period, scope, category, document_id
        )
        coverage = self.get_data_coverage(db, document_id)
        top_sources = self.get_top_sources(
            db, limit=5, reporting_year=reporting_year, reporting_period=reporting_period,
            scope=scope, category=category, document_id=document_id
        )
        reconciliation = self.get_reconciliation(db, document_id)

        return CarbonDashboardResponse(
            summary=summary,
            scopes=scopes,
            categories=categories,
            activities=activities,
            documents=documents,
            trends=trends,
            coverage=coverage,
            top_sources=top_sources,
            reconciliation=reconciliation,
            dashboard_version=self.dashboard_version,
        )


carbon_dashboard_service = CarbonDashboardService()
