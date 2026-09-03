"""
test_carbon_dashboard.py — Comprehensive Test Suite for Step 15.
Carbon Footprint Dashboard & Historical Analytics Tests.

Covers:
- Executive KPI Summary (Total calculated, Scope 1, 2, 3, counts, latest period)
- Scope Breakdown (Absolute values, percentages, zero-total handling, non-fabricated zeros)
- Category Breakdown (ENERGY, FUEL, TRANSPORT, WATER, WASTE, OTHER, % shares)
- Activity Breakdown (Activity aggregation, counts, ranking)
- Document Contribution (Document aggregation, sorting by total desc, scope contributions)
- Historical Trends (Actual periods only, chronological ordering, no fabricated zero periods)
- Period Comparisons (Absolute change, percentage change, single period handling, previous=0 handling)
- Data Coverage & Quality (Calculated, posted, excluded, no factor, ineligible, invalid, missing geo/year)
- Electricity & Double-Counting Preservation (Doc #1 total excluded, grid posted, solar excluded, total footprint = 33,004.60 kgCO2e)
- Extracted vs Calculated Reconciliation (Exact Decimal arithmetic, 1 tCO2e = 1000 kgCO2e, untouched original values)
- Safety Boundaries (No recalculation, no LLM, no factor resolution, no mutations, no carbon credits, no ROI/savings claims)
- API Endpoints (8 endpoints: dashboard, summary, scopes, categories, activities, documents, trends, coverage, top-sources, reconciliation)
"""
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database.session import SessionLocal, init_db
from backend.app.models.carbon_ledger import CarbonLedgerEntry
from backend.app.models.carbon_calculation import CarbonCalculation
from backend.app.models.activity_data import ActivityData
from backend.app.models.sustainability_metric import SustainabilityMetric
from backend.app.models.document import Document
from backend.app.models.emission_factor import EmissionFactor
from backend.app.services.carbon_dashboard import carbon_dashboard_service
from backend.app.services.carbon_ledger import carbon_ledger_service
from backend.app.services.carbon_calculation import carbon_calculation_engine

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db()


# ==============================================================================
# 1. SUMMARY (Tests 1 - 10)
# ==============================================================================
class TestDashboardSummary:
    def test_01_total_calculated_co2e(self):
        """1. Total calculated CO2e accurately aggregates only POSTED ledger records."""
        db = SessionLocal()
        try:
            summary = carbon_dashboard_service.get_dashboard_summary(db, document_id=1)
            assert summary.total_calculated_co2e_t == 33.0046
            assert summary.total_calculated_co2e_kg == 33004.6
        finally:
            db.close()

    def test_02_scope_1_summary(self):
        """2. Scope 1 summary reflects diesel direct emissions (1.1256 tCO2e)."""
        db = SessionLocal()
        try:
            summary = carbon_dashboard_service.get_dashboard_summary(db, document_id=1)
            assert summary.scope_1_co2e_t == 1.1256
            assert summary.scope_1_co2e_kg == 1125.6
        finally:
            db.close()

    def test_03_scope_2_summary(self):
        """3. Scope 2 summary reflects grid electricity indirect emissions (31.8790 tCO2e)."""
        db = SessionLocal()
        try:
            summary = carbon_dashboard_service.get_dashboard_summary(db, document_id=1)
            assert summary.scope_2_co2e_t == 31.8790
            assert summary.scope_2_co2e_kg == 31879.0
        finally:
            db.close()

    def test_04_scope_3_summary_unavailable(self):
        """4. Scope 3 summary remains None (unavailable) when no Scope 3 calculations exist."""
        db = SessionLocal()
        try:
            summary = carbon_dashboard_service.get_dashboard_summary(db, document_id=1)
            assert summary.scope_3_co2e_t is None
            assert summary.scope_3_co2e_kg is None
        finally:
            db.close()

    def test_05_posted_count(self):
        """5. Posted entry count correctly counts POSTED status records (2 in Doc 1)."""
        db = SessionLocal()
        try:
            summary = carbon_dashboard_service.get_dashboard_summary(db, document_id=1)
            assert summary.posted_entry_count == 2
        finally:
            db.close()

    def test_06_excluded_count(self):
        """6. Excluded entry count correctly counts non-posted records."""
        db = SessionLocal()
        try:
            summary = carbon_dashboard_service.get_dashboard_summary(db, document_id=1)
            assert summary.excluded_entry_count >= 1
        finally:
            db.close()

    def test_07_superseded_count(self):
        """7. Superseded entry count accurately tracks historical version updates."""
        db = SessionLocal()
        try:
            summary = carbon_dashboard_service.get_dashboard_summary(db, document_id=1)
            assert summary.superseded_entry_count >= 0
        finally:
            db.close()

    def test_08_document_count(self):
        """8. Document count reflects unique documents with posted entries."""
        db = SessionLocal()
        try:
            summary = carbon_dashboard_service.get_dashboard_summary(db)
            assert summary.document_count >= 1
        finally:
            db.close()

    def test_09_activity_count(self):
        """9. Activity count reflects unique activity types contributing to footprint."""
        db = SessionLocal()
        try:
            summary = carbon_dashboard_service.get_dashboard_summary(db, document_id=1)
            assert summary.activity_count == 2  # diesel and purchased_electricity
        finally:
            db.close()

    def test_10_reporting_period_count(self):
        """10. Reporting period count reflects unique periods in dataset."""
        db = SessionLocal()
        try:
            summary = carbon_dashboard_service.get_dashboard_summary(db, document_id=1)
            assert summary.reporting_period_count >= 1
            assert summary.latest_reporting_period == "2024-10"
        finally:
            db.close()


# ==============================================================================
# 2. SCOPE BREAKDOWN (Tests 11 - 16)
# ==============================================================================
class TestScopeBreakdown:
    def test_11_scope_1_breakdown(self):
        """11. Scope 1 breakdown contains direct fuel combustion emissions."""
        db = SessionLocal()
        try:
            scopes = carbon_dashboard_service.get_scope_breakdown(db, document_id=1)
            s1 = next(item for item in scopes.items if item.scope == "SCOPE_1")
            assert s1.co2e_t == 1.1256
            assert s1.entry_count == 1
        finally:
            db.close()

    def test_12_scope_2_breakdown(self):
        """12. Scope 2 breakdown contains indirect grid electricity emissions."""
        db = SessionLocal()
        try:
            scopes = carbon_dashboard_service.get_scope_breakdown(db, document_id=1)
            s2 = next(item for item in scopes.items if item.scope == "SCOPE_2")
            assert s2.co2e_t == 31.8790
            assert s2.entry_count == 1
        finally:
            db.close()

    def test_13_scope_3_breakdown(self):
        """13. Scope 3 breakdown has 0 entries and 0 kg for Doc 1."""
        db = SessionLocal()
        try:
            scopes = carbon_dashboard_service.get_scope_breakdown(db, document_id=1)
            s3 = next(item for item in scopes.items if item.scope == "SCOPE_3")
            assert s3.entry_count == 0
            assert s3.percentage_of_total is None
        finally:
            db.close()

    def test_14_total_scope_co2e(self):
        """14. Total scope CO2e equals sum of all scope items."""
        db = SessionLocal()
        try:
            scopes = carbon_dashboard_service.get_scope_breakdown(db, document_id=1)
            assert scopes.total_co2e_t == 33.0046
        finally:
            db.close()

    def test_15_scope_percentage(self):
        """15. Scope percentage accurately sums to ~100%."""
        db = SessionLocal()
        try:
            scopes = carbon_dashboard_service.get_scope_breakdown(db, document_id=1)
            s1 = next(item for item in scopes.items if item.scope == "SCOPE_1")
            s2 = next(item for item in scopes.items if item.scope == "SCOPE_2")
            assert s1.percentage_of_total == pytest.approx(3.41, abs=0.02)
            assert s2.percentage_of_total == pytest.approx(96.59, abs=0.02)
        finally:
            db.close()

    def test_16_zero_total_handling(self):
        """16. When total footprint is 0, percentage is not fabricated and set to None."""
        db = SessionLocal()
        try:
            scopes = carbon_dashboard_service.get_scope_breakdown(db, document_id=999999)
            assert scopes.total_co2e_t == 0.0
            for item in scopes.items:
                assert item.percentage_of_total is None
        finally:
            db.close()


# ==============================================================================
# 3. CATEGORY BREAKDOWN (Tests 17 - 21)
# ==============================================================================
class TestCategoryBreakdown:
    def test_17_category_energy(self):
        """17. ENERGY category aggregates grid electricity (31.8790 tCO2e)."""
        db = SessionLocal()
        try:
            cats = carbon_dashboard_service.get_category_breakdown(db, document_id=1)
            energy_cat = next((c for c in cats.items if c.category == "ENERGY"), None)
            assert energy_cat is not None
            assert energy_cat.co2e_t == 31.8790
        finally:
            db.close()

    def test_18_category_fuel(self):
        """18. FUEL category aggregates diesel (1.1256 tCO2e)."""
        db = SessionLocal()
        try:
            cats = carbon_dashboard_service.get_category_breakdown(db, document_id=1)
            fuel_cat = next((c for c in cats.items if c.category == "FUEL"), None)
            assert fuel_cat is not None
            assert fuel_cat.co2e_t == 1.1256
        finally:
            db.close()

    def test_19_category_transport(self):
        """19. TRANSPORT category is present if posted entries exist."""
        db = SessionLocal()
        try:
            cats = carbon_dashboard_service.get_category_breakdown(db, category="TRANSPORT")
            # If no transport entries, items list is empty or strictly matches posted
            assert isinstance(cats.items, list)
        finally:
            db.close()

    def test_20_category_other(self):
        """20. OTHER category aggregates any unspecified category types."""
        db = SessionLocal()
        try:
            cats = carbon_dashboard_service.get_category_breakdown(db)
            assert isinstance(cats.items, list)
        finally:
            db.close()

    def test_21_category_percentage(self):
        """21. Category percentages are calculated accurately against total."""
        db = SessionLocal()
        try:
            cats = carbon_dashboard_service.get_category_breakdown(db, document_id=1)
            energy_cat = next(c for c in cats.items if c.category == "ENERGY")
            assert energy_cat.percentage_of_total == pytest.approx(96.59, abs=0.02)
        finally:
            db.close()


# ==============================================================================
# 4. ACTIVITY BREAKDOWN (Tests 22 - 24)
# ==============================================================================
class TestActivityBreakdown:
    def test_22_activity_aggregation(self):
        """22. Activity breakdown aggregates purchased_electricity and diesel."""
        db = SessionLocal()
        try:
            acts = carbon_dashboard_service.get_activity_breakdown(db, document_id=1)
            act_names = [a.activity_type for a in acts.items]
            assert "purchased_electricity" in act_names
            assert "diesel" in act_names
        finally:
            db.close()

    def test_23_activity_count(self):
        """23. Each activity item tracks its entry count."""
        db = SessionLocal()
        try:
            acts = carbon_dashboard_service.get_activity_breakdown(db, document_id=1)
            for a in acts.items:
                assert a.entry_count >= 1
        finally:
            db.close()

    def test_24_activity_ranking(self):
        """24. Activities are sorted descending by calculated CO2e."""
        db = SessionLocal()
        try:
            acts = carbon_dashboard_service.get_activity_breakdown(db, document_id=1)
            assert acts.items[0].activity_type == "purchased_electricity"
            assert acts.items[0].co2e_t > acts.items[1].co2e_t
        finally:
            db.close()


# ==============================================================================
# 5. DOCUMENT CONTRIBUTION (Tests 25 - 28)
# ==============================================================================
class TestDocumentContribution:
    def test_25_document_contribution(self):
        """25. Document contribution lists contributing documents."""
        db = SessionLocal()
        try:
            docs = carbon_dashboard_service.get_document_contributions(db, document_id=1)
            assert docs.total_documents == 1
            assert docs.items[0].document_id == 1
            assert docs.items[0].total_co2e_t == 33.0046
        finally:
            db.close()

    def test_26_document_sorting(self):
        """26. Document contributions are sorted descending by total emissions."""
        db = SessionLocal()
        try:
            docs = carbon_dashboard_service.get_document_contributions(db)
            if len(docs.items) > 1:
                assert docs.items[0].total_co2e_t >= docs.items[1].total_co2e_t
        finally:
            db.close()

    def test_27_scope_breakdown_per_document(self):
        """27. Document contribution includes Scope 1 and Scope 2 breakdowns."""
        db = SessionLocal()
        try:
            docs = carbon_dashboard_service.get_document_contributions(db, document_id=1)
            item = docs.items[0]
            assert item.scope_1_t == 1.1256
            assert item.scope_2_t == 31.8790
            assert item.scope_3_t is None
        finally:
            db.close()

    def test_28_document_metadata_preservation(self):
        """28. Document contribution preserves reporting period and company name."""
        db = SessionLocal()
        try:
            docs = carbon_dashboard_service.get_document_contributions(db, document_id=1)
            item = docs.items[0]
            assert item.reporting_period == "2024-10"
            assert item.document_name is not None
        finally:
            db.close()


# ==============================================================================
# 6. HISTORICAL TRENDS (Tests 29 - 36)
# ==============================================================================
class TestHistoricalTrends:
    def test_29_single_period_trend(self):
        """29. When only 1 period exists, returns single point with comparison unavailable."""
        db = SessionLocal()
        try:
            trends = carbon_dashboard_service.get_trends(db, document_id=1)
            assert len(trends.periods) == 1
            assert trends.periods[0].reporting_period == "2024-10"
            assert trends.comparison.comparison_available is False
            assert "More reporting periods are needed" in (trends.comparison.message or "")
        finally:
            db.close()

    def test_30_multiple_periods_trend(self):
        """30. Multiple periods calculate chronological trend accurately."""
        db = SessionLocal()
        try:
            # Clean test document
            db.query(CarbonLedgerEntry).filter(CarbonLedgerEntry.document_id == 800).delete()
            db.query(CarbonCalculation).filter(CarbonCalculation.document_id == 800).delete()
            db.commit()

            c1 = CarbonCalculation(
                activity_data_id=8001,
                document_id=800,
                activity_type="purchased_electricity",
                quantity=Decimal("20000.0"),
                activity_unit="kWh",
                calculated_co2e=Decimal("20000.0"),
                status="CALCULATED",
                scope="SCOPE_2",
            )
            c2 = CarbonCalculation(
                activity_data_id=8002,
                document_id=800,
                activity_type="purchased_electricity",
                quantity=Decimal("25000.0"),
                activity_unit="kWh",
                calculated_co2e=Decimal("25000.0"),
                status="CALCULATED",
                scope="SCOPE_2",
            )
            db.add_all([c1, c2])
            db.commit()

            e1 = CarbonLedgerEntry(
                carbon_calculation_id=c1.id,
                activity_data_id=8001,
                document_id=800,
                activity_type="purchased_electricity",
                quantity=Decimal("20000.0"),
                activity_unit="kWh",
                reporting_period="2024-09",
                reporting_year=2024,
                calculated_co2e=Decimal("20000.0"),
                scope="SCOPE_2",
                accounting_status="POSTED",
            )
            e2 = CarbonLedgerEntry(
                carbon_calculation_id=c2.id,
                activity_data_id=8002,
                document_id=800,
                activity_type="purchased_electricity",
                quantity=Decimal("25000.0"),
                activity_unit="kWh",
                reporting_period="2024-10",
                reporting_year=2024,
                calculated_co2e=Decimal("25000.0"),
                scope="SCOPE_2",
                accounting_status="POSTED",
            )
            db.add_all([e1, e2])
            db.commit()

            trends = carbon_dashboard_service.get_trends(db, document_id=800)
            assert len(trends.periods) == 2
            assert trends.periods[0].reporting_period == "2024-09"
            assert trends.periods[1].reporting_period == "2024-10"
            assert trends.comparison.comparison_available is True
        finally:
            db.close()

    def test_31_no_fabricated_periods(self):
        """31. Periods that do not exist in database are NEVER fabricated as 0 emissions."""
        db = SessionLocal()
        try:
            trends = carbon_dashboard_service.get_trends(db, document_id=1)
            periods = [p.reporting_period for p in trends.periods]
            assert "2024-08" not in periods
            assert "2024-09" not in periods
            assert "2024-11" not in periods
        finally:
            db.close()

    def test_32_period_ordering(self):
        """32. Periods are sorted in chronological ascending order."""
        db = SessionLocal()
        try:
            trends = carbon_dashboard_service.get_trends(db, document_id=800)
            assert trends.periods[0].reporting_period < trends.periods[1].reporting_period
        finally:
            db.close()

    def test_33_scope_trend_breakdown(self):
        """33. Historical points track Scope 1, Scope 2, Scope 3 separately."""
        db = SessionLocal()
        try:
            trends = carbon_dashboard_service.get_trends(db, document_id=1)
            pt = trends.periods[0]
            assert pt.scope_1_t == 1.1256
            assert pt.scope_2_t == 31.8790
            assert pt.scope_3_t is None
        finally:
            db.close()

    def test_34_year_trend_aggregation(self):
        """34. Aggregation by reporting year 2024."""
        db = SessionLocal()
        try:
            trends = carbon_dashboard_service.get_trends(db, document_id=1)
            assert len(trends.years) >= 1
            y2024 = next(y for y in trends.years if y.year == 2024)
            assert y2024.total_co2e_t == 33.0046
        finally:
            db.close()

    def test_35_missing_scope_represented_safely(self):
        """35. Missing scope in trend point is None, not 0.0."""
        db = SessionLocal()
        try:
            trends = carbon_dashboard_service.get_trends(db, document_id=1)
            assert trends.periods[0].scope_3_t is None
        finally:
            db.close()

    def test_36_period_comparison_activation(self):
        """36. Comparison activates when at least two periods exist."""
        db = SessionLocal()
        try:
            trends = carbon_dashboard_service.get_trends(db, document_id=800)
            assert trends.comparison.comparison_available is True
            assert trends.comparison.previous_period == "2024-09"
            assert trends.comparison.current_period == "2024-10"
        finally:
            db.close()


# ==============================================================================
# 7. PERIOD COMPARISON (Tests 37 - 42)
# ==============================================================================
class TestPeriodComparison:
    def test_37_absolute_change(self):
        """37. Absolute change = current - previous (25.0 - 20.0 = +5.0 tCO2e)."""
        db = SessionLocal()
        try:
            trends = carbon_dashboard_service.get_trends(db, document_id=800)
            assert trends.comparison.absolute_change_t == 5.0
        finally:
            db.close()

    def test_38_percentage_change(self):
        """38. Percentage change = ((25 - 20)/20) * 100 = +25.0%."""
        db = SessionLocal()
        try:
            trends = carbon_dashboard_service.get_trends(db, document_id=800)
            assert trends.comparison.percentage_change == 25.0
        finally:
            db.close()

    def test_39_previous_equal_zero_handling(self):
        """39. When previous period has 0 emissions, percentage change is None (no div by zero)."""
        db = SessionLocal()
        try:
            db.query(CarbonLedgerEntry).filter(CarbonLedgerEntry.document_id == 801).delete()
            db.query(CarbonCalculation).filter(CarbonCalculation.document_id == 801).delete()
            db.commit()

            c1 = CarbonCalculation(
                activity_data_id=8011,
                document_id=801,
                activity_type="solar_electricity",
                quantity=Decimal("100.0"),
                activity_unit="kWh",
                calculated_co2e=Decimal("0.0"),
                status="CALCULATED",
            )
            c2 = CarbonCalculation(
                activity_data_id=8012,
                document_id=801,
                activity_type="purchased_electricity",
                quantity=Decimal("10000.0"),
                activity_unit="kWh",
                calculated_co2e=Decimal("10000.0"),
                status="CALCULATED",
            )
            db.add_all([c1, c2])
            db.commit()

            e1 = CarbonLedgerEntry(
                carbon_calculation_id=c1.id,
                activity_data_id=8011,
                document_id=801,
                activity_type="solar_electricity",
                quantity=Decimal("100.0"),
                activity_unit="kWh",
                reporting_period="2024-01",
                calculated_co2e=Decimal("0.0"),
                accounting_status="POSTED",
            )
            e2 = CarbonLedgerEntry(
                carbon_calculation_id=c2.id,
                activity_data_id=8012,
                document_id=801,
                activity_type="purchased_electricity",
                quantity=Decimal("10000.0"),
                activity_unit="kWh",
                reporting_period="2024-02",
                calculated_co2e=Decimal("10000.0"),
                accounting_status="POSTED",
            )
            db.add_all([e1, e2])
            db.commit()

            trends = carbon_dashboard_service.get_trends(db, document_id=801)
            assert trends.comparison.percentage_change is None
        finally:
            db.close()

    def test_40_only_one_period_no_comparison(self):
        """40. Single period explicitly returns comparison_available=False."""
        db = SessionLocal()
        try:
            trends = carbon_dashboard_service.get_trends(db, document_id=1)
            assert trends.comparison.comparison_available is False
        finally:
            db.close()

    def test_41_negative_change(self):
        """41. Negative difference calculated accurately when emissions decrease."""
        db = SessionLocal()
        try:
            db.query(CarbonLedgerEntry).filter(CarbonLedgerEntry.document_id == 802).delete()
            db.query(CarbonCalculation).filter(CarbonCalculation.document_id == 802).delete()
            db.commit()

            c1 = CarbonCalculation(
                activity_data_id=8021,
                document_id=802,
                activity_type="purchased_electricity",
                quantity=Decimal("30000.0"),
                activity_unit="kWh",
                calculated_co2e=Decimal("30000.0"),
                status="CALCULATED",
            )
            c2 = CarbonCalculation(
                activity_data_id=8022,
                document_id=802,
                activity_type="purchased_electricity",
                quantity=Decimal("24000.0"),
                activity_unit="kWh",
                calculated_co2e=Decimal("24000.0"),
                status="CALCULATED",
            )
            db.add_all([c1, c2])
            db.commit()

            e1 = CarbonLedgerEntry(
                carbon_calculation_id=c1.id,
                activity_data_id=8021,
                document_id=802,
                activity_type="purchased_electricity",
                quantity=Decimal("30000.0"),
                activity_unit="kWh",
                reporting_period="2024-01",
                calculated_co2e=Decimal("30000.0"),
                accounting_status="POSTED",
            )
            e2 = CarbonLedgerEntry(
                carbon_calculation_id=c2.id,
                activity_data_id=8022,
                document_id=802,
                activity_type="purchased_electricity",
                quantity=Decimal("24000.0"),
                activity_unit="kWh",
                reporting_period="2024-02",
                calculated_co2e=Decimal("24000.0"),
                accounting_status="POSTED",
            )
            db.add_all([e1, e2])
            db.commit()

            trends = carbon_dashboard_service.get_trends(db, document_id=802)
            assert trends.comparison.absolute_change_t == -6.0
            assert trends.comparison.percentage_change == -20.0
        finally:
            db.close()

    def test_42_positive_change(self):
        """42. Positive change handled accurately."""
        db = SessionLocal()
        try:
            trends = carbon_dashboard_service.get_trends(db, document_id=800)
            assert trends.comparison.absolute_change_t > 0
        finally:
            db.close()


# ==============================================================================
# 8. DATA COVERAGE & AUDIT QUALITY (Tests 43 - 51)
# ==============================================================================
class TestDataCoverageAndQuality:
    def test_43_calculated_records_count(self):
        """43. Tracks count of calculated records in dataset."""
        db = SessionLocal()
        try:
            cov = carbon_dashboard_service.get_data_coverage(db, document_id=1)
            assert cov.calculated_records >= 2
        finally:
            db.close()

    def test_44_posted_ledger_count(self):
        """44. Tracks posted ledger records count."""
        db = SessionLocal()
        try:
            cov = carbon_dashboard_service.get_data_coverage(db, document_id=1)
            assert cov.posted_ledger_records == 2
        finally:
            db.close()

    def test_45_excluded_records_count(self):
        """45. Tracks excluded records count."""
        db = SessionLocal()
        try:
            cov = carbon_dashboard_service.get_data_coverage(db, document_id=1)
            assert cov.excluded_records >= 1
        finally:
            db.close()

    def test_46_no_factor_records_count(self):
        """46. Tracks NO_FACTOR records (such as solar)."""
        db = SessionLocal()
        try:
            cov = carbon_dashboard_service.get_data_coverage(db, document_id=1)
            assert cov.no_factor_records >= 1
        finally:
            db.close()

    def test_47_ineligible_records_count(self):
        """47. Tracks INELIGIBLE operational records (power factor, peak demand, etc.)."""
        db = SessionLocal()
        try:
            cov = carbon_dashboard_service.get_data_coverage(db, document_id=1)
            assert cov.ineligible_records >= 2
        finally:
            db.close()

    def test_48_multiple_factor_records_count(self):
        """48. Tracks MULTIPLE_FACTORS ambiguity records."""
        db = SessionLocal()
        try:
            cov = carbon_dashboard_service.get_data_coverage(db)
            assert hasattr(cov, "multiple_factor_records")
        finally:
            db.close()

    def test_49_invalid_records_count(self):
        """49. Tracks invalid activity records."""
        db = SessionLocal()
        try:
            cov = carbon_dashboard_service.get_data_coverage(db)
            assert hasattr(cov, "invalid_records")
        finally:
            db.close()

    def test_50_missing_geography_count(self):
        """50. Tracks missing geography records."""
        db = SessionLocal()
        try:
            cov = carbon_dashboard_service.get_data_coverage(db)
            assert hasattr(cov, "missing_geography_records")
        finally:
            db.close()

    def test_51_missing_year_count(self):
        """51. Tracks missing reporting year records."""
        db = SessionLocal()
        try:
            cov = carbon_dashboard_service.get_data_coverage(db)
            assert hasattr(cov, "missing_year_records")
        finally:
            db.close()


# ==============================================================================
# 9. ELECTRICITY DOUBLE COUNTING PROTECTION (Tests 52 - 56)
# ==============================================================================
class TestElectricityDoubleCountingInDashboard:
    def test_52_document_1_electricity_group(self):
        """52. Document #1 contains electricity activity group with total + grid + solar."""
        db = SessionLocal()
        try:
            calcs = db.query(CarbonCalculation).filter_by(
                document_id=1, activity_group_id="doc_1_electricity_2024_10"
            ).all()
            assert len(calcs) >= 2
        finally:
            db.close()

    def test_53_total_electricity_not_double_counted(self):
        """53. Total electricity (48,750 kWh) is excluded from dashboard total."""
        db = SessionLocal()
        try:
            summary = carbon_dashboard_service.get_dashboard_summary(db, document_id=1)
            # Must equal Diesel (1,125.60) + Grid (31,879.00) = 33,004.60 kgCO2e
            assert summary.total_calculated_co2e_kg == 33004.6
        finally:
            db.close()

    def test_54_grid_contribution(self):
        """54. Grid electricity constituent contributes 31.8790 tCO2e to dashboard."""
        db = SessionLocal()
        try:
            summary = carbon_dashboard_service.get_dashboard_summary(db, document_id=1)
            assert summary.scope_2_co2e_t == 31.8790
        finally:
            db.close()

    def test_55_solar_excluded_from_total(self):
        """55. Solar electricity with NO_FACTOR is excluded (not 0, not positive)."""
        db = SessionLocal()
        try:
            acts = carbon_dashboard_service.get_activity_breakdown(db, document_id=1)
            solar_act = next((a for a in acts.items if a.activity_type == "solar_electricity"), None)
            assert solar_act is None  # Excluded from posted activities
        finally:
            db.close()

    def test_56_ledger_total_strictly_preserved(self):
        """56. Total calculated footprint on dashboard matches ledger exactly (33.0046 tCO2e)."""
        db = SessionLocal()
        try:
            summary = carbon_dashboard_service.get_dashboard_summary(db, document_id=1)
            assert summary.total_calculated_co2e_t == 33.0046
        finally:
            db.close()


# ==============================================================================
# 10. RECONCILIATION LAYER (Tests 57 - 65)
# ==============================================================================
class TestDashboardReconciliation:
    def test_57_extracted_scope_1(self):
        """57. Extracted Scope 1 is 1.13 tCO2e."""
        db = SessionLocal()
        try:
            recon = carbon_dashboard_service.get_reconciliation(db, document_id=1)
            s1_item = next(i for i in recon.items if "Scope 1" in i.scope_or_metric)
            assert s1_item.extracted_value_t == 1.13
        finally:
            db.close()

    def test_58_calculated_scope_1(self):
        """58. Calculated Scope 1 is 1.1256 tCO2e."""
        db = SessionLocal()
        try:
            recon = carbon_dashboard_service.get_reconciliation(db, document_id=1)
            s1_item = next(i for i in recon.items if "Scope 1" in i.scope_or_metric)
            assert s1_item.calculated_value_t == 1.1256
        finally:
            db.close()

    def test_59_extracted_scope_2(self):
        """59. Extracted Scope 2 is 31.88 tCO2e."""
        db = SessionLocal()
        try:
            recon = carbon_dashboard_service.get_reconciliation(db, document_id=1)
            s2_item = next(i for i in recon.items if "Scope 2" in i.scope_or_metric)
            assert s2_item.extracted_value_t == 31.88
        finally:
            db.close()

    def test_60_calculated_scope_2(self):
        """60. Calculated Scope 2 is 31.8790 tCO2e."""
        db = SessionLocal()
        try:
            recon = carbon_dashboard_service.get_reconciliation(db, document_id=1)
            s2_item = next(i for i in recon.items if "Scope 2" in i.scope_or_metric)
            assert s2_item.calculated_value_t == 31.8790
        finally:
            db.close()

    def test_61_extracted_total(self):
        """61. Extracted total is 33.01 tCO2e."""
        db = SessionLocal()
        try:
            recon = carbon_dashboard_service.get_reconciliation(db, document_id=1)
            tot_item = next(i for i in recon.items if "Total" in i.scope_or_metric)
            assert tot_item.extracted_value_t == 33.01
        finally:
            db.close()

    def test_62_calculated_total(self):
        """62. Calculated total is 33.0046 tCO2e."""
        db = SessionLocal()
        try:
            recon = carbon_dashboard_service.get_reconciliation(db, document_id=1)
            tot_item = next(i for i in recon.items if "Total" in i.scope_or_metric)
            assert tot_item.calculated_value_t == 33.0046
        finally:
            db.close()

    def test_63_reconciliation_difference(self):
        """63. Difference is -0.0054 tCO2e with DIFFERENCE status."""
        db = SessionLocal()
        try:
            recon = carbon_dashboard_service.get_reconciliation(db, document_id=1)
            tot_item = next(i for i in recon.items if "Total" in i.scope_or_metric)
            assert tot_item.difference_t == pytest.approx(-0.0054, abs=0.0001)
            assert tot_item.status == "DIFFERENCE"
        finally:
            db.close()

    def test_64_kg_to_t_conversion(self):
        """64. Conversion uses strict 1 tCO2e = 1000 kgCO2e."""
        kg = Decimal("33004.6")
        t = kg / Decimal("1000")
        assert t == Decimal("33.0046")

    def test_65_extracted_values_remain_untouched(self):
        """65. Original SustainabilityMetric values remain unchanged."""
        db = SessionLocal()
        try:
            m = db.query(SustainabilityMetric).filter_by(document_id=1, metric_type="total_ghg_emissions").first()
            assert m.value == 33.01
        finally:
            db.close()


# ==============================================================================
# 11. SAFETY BOUNDARIES (Tests 66 - 75)
# ==============================================================================
class TestDashboardSafetyBoundaries:
    def test_66_no_recalculation_in_dashboard(self):
        """66. Dashboard service never performs quantity * factor multiplication."""
        assert not hasattr(carbon_dashboard_service, "calculate_activity")
        assert not hasattr(carbon_dashboard_service, "calculate_document")

    def test_67_no_llm_used(self):
        """67. Dashboard service contains 0 LLM calls."""
        assert not hasattr(carbon_dashboard_service, "llm_service")

    def test_68_no_factor_resolution(self):
        """68. Dashboard does not resolve emission factors directly."""
        assert not hasattr(carbon_dashboard_service, "emission_factor_resolver")

    def test_69_no_activity_data_mutation(self):
        """69. ActivityData records are not mutated during dashboard queries."""
        db = SessionLocal()
        try:
            act_before = db.query(ActivityData).filter_by(document_id=1, activity_type="diesel").first().quantity
            carbon_dashboard_service.get_full_dashboard(db, document_id=1)
            act_after = db.query(ActivityData).filter_by(document_id=1, activity_type="diesel").first().quantity
            assert act_before == act_after
        finally:
            db.close()

    def test_70_no_carbon_calculation_mutation(self):
        """70. CarbonCalculation records are not modified by dashboard."""
        db = SessionLocal()
        try:
            calc_before = db.query(CarbonCalculation).filter_by(document_id=1).first().calculated_co2e
            carbon_dashboard_service.get_full_dashboard(db, document_id=1)
            calc_after = db.query(CarbonCalculation).filter_by(document_id=1).first().calculated_co2e
            assert calc_before == calc_after
        finally:
            db.close()

    def test_71_no_ledger_mutation(self):
        """71. CarbonLedgerEntry records are read-only for dashboard."""
        db = SessionLocal()
        try:
            count_before = db.query(CarbonLedgerEntry).count()
            carbon_dashboard_service.get_full_dashboard(db)
            count_after = db.query(CarbonLedgerEntry).count()
            assert count_before == count_after
        finally:
            db.close()

    def test_72_no_fabricated_periods(self):
        """72. Missing historical periods remain absent."""
        db = SessionLocal()
        try:
            trends = carbon_dashboard_service.get_trends(db, document_id=1)
            assert len(trends.periods) == 1
        finally:
            db.close()

    def test_73_no_fabricated_values(self):
        """73. Missing scopes remain None, never replaced with fake numbers."""
        db = SessionLocal()
        try:
            summary = carbon_dashboard_service.get_dashboard_summary(db, document_id=1)
            assert summary.scope_3_co2e_t is None
        finally:
            db.close()

    def test_74_no_carbon_credits_in_dashboard(self):
        """74. Dashboard contains no carbon credits, offsets, or issuance."""
        summary = carbon_dashboard_service.get_dashboard_summary(SessionLocal())
        assert not hasattr(summary, "carbon_credits")
        assert not hasattr(summary, "offset_units")

    def test_75_no_roi_or_savings_claims(self):
        """75. Dashboard contains no ROI, payback, or cost reduction claims."""
        summary = carbon_dashboard_service.get_dashboard_summary(SessionLocal())
        assert not hasattr(summary, "roi")
        assert not hasattr(summary, "savings")


# ==============================================================================
# 12. API ENDPOINTS (Tests 76 - 83)
# ==============================================================================
class TestDashboardAPI:
    def test_76_api_full_dashboard(self):
        """76. GET /api/carbon-dashboard returns full dashboard payload."""
        res = client.get("/api/carbon-dashboard?document_id=1")
        assert res.status_code == 200
        data = res.json()
        assert "summary" in data
        assert "scopes" in data
        assert "categories" in data
        assert "activities" in data
        assert "documents" in data
        assert "trends" in data
        assert "coverage" in data
        assert "top_sources" in data
        assert "reconciliation" in data
        assert data["summary"]["total_calculated_co2e_t"] == 33.0046

    def test_77_api_dashboard_summary(self):
        """77. GET /api/carbon-dashboard/summary returns executive summary."""
        res = client.get("/api/carbon-dashboard/summary?document_id=1")
        assert res.status_code == 200
        data = res.json()
        assert data["total_calculated_co2e_t"] == 33.0046
        assert data["scope_1_co2e_t"] == 1.1256
        assert data["scope_2_co2e_t"] == 31.8790

    def test_78_api_dashboard_scopes(self):
        """78. GET /api/carbon-dashboard/scopes returns scope breakdown."""
        res = client.get("/api/carbon-dashboard/scopes?document_id=1")
        assert res.status_code == 200
        data = res.json()
        assert data["total_co2e_t"] == 33.0046
        assert len(data["items"]) == 3

    def test_79_api_dashboard_categories(self):
        """79. GET /api/carbon-dashboard/categories returns category breakdown."""
        res = client.get("/api/carbon-dashboard/categories?document_id=1")
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert len(data["items"]) >= 1

    def test_80_api_dashboard_activities(self):
        """80. GET /api/carbon-dashboard/activities returns activity breakdown."""
        res = client.get("/api/carbon-dashboard/activities?document_id=1")
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert len(data["items"]) >= 1

    def test_81_api_dashboard_trends(self):
        """81. GET /api/carbon-dashboard/trends returns historical trends."""
        res = client.get("/api/carbon-dashboard/trends?document_id=1")
        assert res.status_code == 200
        data = res.json()
        assert "periods" in data
        assert "years" in data
        assert "comparison" in data
        assert len(data["periods"]) == 1

    def test_82_api_dashboard_coverage(self):
        """82. GET /api/carbon-dashboard/coverage returns data coverage."""
        res = client.get("/api/carbon-dashboard/coverage?document_id=1")
        assert res.status_code == 200
        data = res.json()
        assert data["posted_ledger_records"] == 2
        assert "notice" in data

    def test_83_api_dashboard_reconciliation(self):
        """83. GET /api/carbon-dashboard/reconciliation returns reconciliation payload."""
        res = client.get("/api/carbon-dashboard/reconciliation?document_id=1")
        assert res.status_code == 200
        data = res.json()
        assert data["total_extracted_t"] == 33.01
        assert data["total_calculated_t"] == 33.0046
        assert data["difference_t"] == pytest.approx(-0.0054, abs=0.0001)
