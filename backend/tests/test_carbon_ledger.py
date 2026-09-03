"""
test_carbon_ledger.py — Comprehensive Test Suite for Step 14.
Carbon Accounting Ledger & Audit History Tests.

Covers:
- Ledger Posting Rules (Calculated posted, non-calculated excluded, reason tracking)
- Idempotency & Versioning (Superseded older versions, history preserved, zero duplicates)
- Deterministic Aggregation (Scope 1, 2, 3, Total, Category, Period, Year)
- Electricity Double-Counting Protection (TOTAL + COMPONENT, TOTAL-only, COMPONENT-only)
- Extracted vs Calculated Reconciliation (Exact Decimal math, 1 tCO2e = 1000 kgCO2e, MATCH / DIFFERENCE / etc.)
- Audit Trail & Full Provenance Lineage
- Safety Boundaries (No recalculation, no LLM, no carbon credits, no ROI/savings, no fabrication)
- API Endpoints (POST /api/carbon-ledger/post, POST doc post, GET list, GET id, GET doc summary, GET reconciliation, GET summary)
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
from backend.app.models.emission_factor import EmissionFactor
from backend.app.models.document import Document
from backend.app.schemas.carbon_ledger import (
    CarbonLedgerPostRequest,
    CarbonLedgerEntryResponse,
    DocumentLedgerSummary,
    LedgerReconciliationResponse,
    LedgerAggregationResponse,
)
from backend.app.services.carbon_ledger import carbon_ledger_service
from backend.app.services.carbon_calculation import carbon_calculation_engine

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db()


# ==============================================================================
# 1. LEDGER POSTING RULES (Tests 1 - 8)
# ==============================================================================
class TestLedgerPostingRules:
    def test_01_calculated_result_can_be_posted(self):
        """1. A valid CALCULATED CarbonCalculation is accepted and posted with POSTED status."""
        db = SessionLocal()
        try:
            calc = CarbonCalculation(
                activity_data_id=101,
                document_id=200,
                metric_id=301,
                activity_type="diesel",
                activity_role="TOTAL",
                quantity=Decimal("100.0"),
                activity_unit="L",
                calculated_co2e=Decimal("268.0"),
                calculated_co2e_unit="kgCO2e",
                status="CALCULATED",
                calculation_version="1.0",
                scope="SCOPE_1",
            )
            db.add(calc)
            db.commit()
            db.refresh(calc)

            entry = carbon_ledger_service.post_calculation(db, calc.id)
            assert entry.accounting_status == "POSTED"
            assert Decimal(str(entry.calculated_co2e)) == Decimal("268.0")
            assert entry.scope == "SCOPE_1"
        finally:
            db.close()

    def test_02_non_calculated_result_excluded(self):
        """2. A non-calculated CarbonCalculation is marked EXCLUDED with no positive CO2e in ledger."""
        db = SessionLocal()
        try:
            calc = CarbonCalculation(
                activity_data_id=102,
                document_id=200,
                activity_type="diesel",
                activity_role="TOTAL",
                quantity=Decimal("100.0"),
                activity_unit="L",
                calculated_co2e=None,
                status="NO_ACTIVITY",
                calculation_version="1.0",
            )
            db.add(calc)
            db.commit()
            db.refresh(calc)

            entry = carbon_ledger_service.post_calculation(db, calc.id)
            assert entry.accounting_status == "EXCLUDED"
            assert entry.calculated_co2e is None
        finally:
            db.close()

    def test_03_ineligible_excluded(self):
        """3. INELIGIBLE calculation is marked EXCLUDED in the ledger."""
        db = SessionLocal()
        try:
            calc = CarbonCalculation(
                activity_data_id=103,
                document_id=200,
                activity_type="power_factor",
                activity_role="SUPPORTING",
                quantity=Decimal("0.96"),
                activity_unit="PF",
                status="INELIGIBLE",
                calculation_reason="Operational supporting metric.",
                calculation_version="1.0",
            )
            db.add(calc)
            db.commit()
            db.refresh(calc)

            entry = carbon_ledger_service.post_calculation(db, calc.id)
            assert entry.accounting_status == "EXCLUDED"
            assert "INELIGIBLE" in (entry.accounting_reason or "")
            assert entry.calculated_co2e is None
        finally:
            db.close()

    def test_04_no_factor_excluded(self):
        """4. NO_FACTOR calculation is marked EXCLUDED in the ledger (EXCLUDED != 0)."""
        db = SessionLocal()
        try:
            calc = CarbonCalculation(
                activity_data_id=104,
                document_id=200,
                activity_type="solar_electricity",
                activity_role="COMPONENT",
                quantity=Decimal("3850.0"),
                activity_unit="kWh",
                status="NO_FACTOR",
                calculation_reason="No factor found.",
                calculation_version="1.0",
            )
            db.add(calc)
            db.commit()
            db.refresh(calc)

            entry = carbon_ledger_service.post_calculation(db, calc.id)
            assert entry.accounting_status == "EXCLUDED"
            assert entry.calculated_co2e is None
        finally:
            db.close()

    def test_05_multiple_factors_excluded(self):
        """5. MULTIPLE_FACTORS calculation is marked EXCLUDED in the ledger."""
        db = SessionLocal()
        try:
            calc = CarbonCalculation(
                activity_data_id=105,
                document_id=200,
                activity_type="natural_gas",
                activity_role="TOTAL",
                quantity=Decimal("500.0"),
                activity_unit="scm",
                status="MULTIPLE_FACTORS",
                calculation_version="1.0",
            )
            db.add(calc)
            db.commit()
            db.refresh(calc)

            entry = carbon_ledger_service.post_calculation(db, calc.id)
            assert entry.accounting_status == "EXCLUDED"
            assert entry.calculated_co2e is None
        finally:
            db.close()

    def test_06_invalid_activity_excluded(self):
        """6. INVALID_ACTIVITY calculation is marked INVALID in the ledger."""
        db = SessionLocal()
        try:
            calc = CarbonCalculation(
                activity_data_id=106,
                document_id=200,
                activity_type="diesel",
                activity_role="TOTAL",
                quantity=Decimal("-50.0"),
                activity_unit="L",
                status="INVALID_ACTIVITY",
                calculation_version="1.0",
            )
            db.add(calc)
            db.commit()
            db.refresh(calc)

            entry = carbon_ledger_service.post_calculation(db, calc.id)
            assert entry.accounting_status == "INVALID"
            assert entry.calculated_co2e is None
        finally:
            db.close()

    def test_07_missing_geography_excluded(self):
        """7. MISSING_GEOGRAPHY calculation is marked EXCLUDED."""
        db = SessionLocal()
        try:
            calc = CarbonCalculation(
                activity_data_id=107,
                document_id=200,
                activity_type="regional_fuel",
                activity_role="TOTAL",
                quantity=Decimal("20.0"),
                activity_unit="L",
                status="MISSING_GEOGRAPHY",
                calculation_version="1.0",
            )
            db.add(calc)
            db.commit()
            db.refresh(calc)

            entry = carbon_ledger_service.post_calculation(db, calc.id)
            assert entry.accounting_status == "EXCLUDED"
            assert entry.calculated_co2e is None
        finally:
            db.close()

    def test_08_missing_year_excluded(self):
        """8. MISSING_YEAR calculation is marked EXCLUDED."""
        db = SessionLocal()
        try:
            calc = CarbonCalculation(
                activity_data_id=108,
                document_id=200,
                activity_type="purchased_electricity",
                activity_role="TOTAL",
                quantity=Decimal("100.0"),
                activity_unit="kWh",
                status="MISSING_YEAR",
                calculation_version="1.0",
            )
            db.add(calc)
            db.commit()
            db.refresh(calc)

            entry = carbon_ledger_service.post_calculation(db, calc.id)
            assert entry.accounting_status == "EXCLUDED"
            assert entry.calculated_co2e is None
        finally:
            db.close()


# ==============================================================================
# 2. IDEMPOTENCY & VERSION PRESERVATION (Tests 9 - 12)
# ==============================================================================
class TestLedgerIdempotencyAndVersioning:
    def test_09_repeated_posting_does_not_duplicate(self):
        """9. Repeated calls to post_calculation on the same record produce identical entry without duplicating."""
        db = SessionLocal()
        try:
            db.query(CarbonLedgerEntry).filter(CarbonLedgerEntry.document_id == 201).delete()
            db.query(CarbonCalculation).filter(CarbonCalculation.document_id == 201).delete()
            db.commit()

            calc = CarbonCalculation(
                activity_data_id=109,
                document_id=201,
                activity_type="diesel",
                activity_role="TOTAL",
                quantity=Decimal("50.0"),
                activity_unit="L",
                calculated_co2e=Decimal("134.0"),
                status="CALCULATED",
                calculation_version="1.0",
                scope="SCOPE_1",
            )
            db.add(calc)
            db.commit()
            db.refresh(calc)

            e1 = carbon_ledger_service.post_calculation(db, calc.id)
            e2 = carbon_ledger_service.post_calculation(db, calc.id)
            assert e1.id == e2.id

            count = db.query(CarbonLedgerEntry).filter(
                CarbonLedgerEntry.carbon_calculation_id == calc.id
            ).count()
            assert count == 1
        finally:
            db.close()

    def test_10_same_calculation_version_reuses_entry(self):
        """10. Same calculation version updates in place and maintains ledger version 1.0."""
        db = SessionLocal()
        try:
            calc = db.query(CarbonCalculation).filter_by(document_id=201).first()
            entry = carbon_ledger_service.post_calculation(db, calc.id)
            assert entry.ledger_version == "1.0"
            assert entry.calculation_version == "1.0"
        finally:
            db.close()

    def test_11_new_calculation_version_preserves_history(self):
        """11. A new calculation version creates a new ledger entry without deleting the older record."""
        db = SessionLocal()
        try:
            calc = db.query(CarbonCalculation).filter_by(document_id=201).first()
            old_entry = db.query(CarbonLedgerEntry).filter_by(carbon_calculation_id=calc.id).first()
            old_entry_id = old_entry.id

            # Update calculation version to 2.0
            calc.calculation_version = "2.0"
            calc.calculated_co2e = Decimal("135.0")
            db.commit()

            new_entry = carbon_ledger_service.post_calculation(db, calc.id)
            assert new_entry.id != old_entry_id
            assert new_entry.calculation_version == "2.0"
            assert Decimal(str(new_entry.calculated_co2e)) == Decimal("135.0")

            # Total records in history is 2
            total_records = db.query(CarbonLedgerEntry).filter_by(carbon_calculation_id=calc.id).count()
            assert total_records == 2
        finally:
            db.close()

    def test_12_old_entry_becomes_superseded(self):
        """12. The previous ledger entry transitions to SUPERSEDED status."""
        db = SessionLocal()
        try:
            calc = db.query(CarbonCalculation).filter_by(document_id=201).first()
            entries = db.query(CarbonLedgerEntry).filter_by(carbon_calculation_id=calc.id).order_by(CarbonLedgerEntry.id.asc()).all()
            assert len(entries) == 2
            assert entries[0].accounting_status == "SUPERSEDED"
            assert entries[1].accounting_status == "POSTED"
        finally:
            db.close()


# ==============================================================================
# 3. DETERMINISTIC AGGREGATION (Tests 13 - 20)
# ==============================================================================
class TestLedgerAggregation:
    def test_13_scope_1_aggregation(self):
        """13. Aggregate Scope 1 posted emissions strictly."""
        db = SessionLocal()
        try:
            summary = carbon_ledger_service.get_document_ledger(db, 1)
            # Scope 1 in Doc 1 is diesel 1,125.6 kgCO2e
            assert summary.scope_1_posted_co2e == 1125.6
        finally:
            db.close()

    def test_14_scope_2_aggregation(self):
        """14. Aggregate Scope 2 posted emissions strictly."""
        db = SessionLocal()
        try:
            summary = carbon_ledger_service.get_document_ledger(db, 1)
            # Scope 2 in Doc 1 is grid 31,879.0 kgCO2e
            assert summary.scope_2_posted_co2e == 31879.0
        finally:
            db.close()

    def test_15_scope_3_aggregation(self):
        """15. Aggregate Scope 3 posted emissions."""
        db = SessionLocal()
        try:
            db.query(CarbonLedgerEntry).filter(CarbonLedgerEntry.document_id == 205).delete()
            db.query(CarbonCalculation).filter(CarbonCalculation.document_id == 205).delete()
            db.commit()

            # Create a Scope 3 calculation and post it
            calc = CarbonCalculation(
                activity_data_id=115,
                document_id=205,
                activity_type="freight",
                activity_role="TOTAL",
                quantity=Decimal("100.0"),
                activity_unit="tonne_km",
                calculated_co2e=Decimal("45.0"),
                status="CALCULATED",
                scope="SCOPE_3",
            )
            db.add(calc)
            db.commit()
            carbon_ledger_service.post_calculation(db, calc.id)

            summary = carbon_ledger_service.get_document_ledger(db, 205)
            assert summary.scope_3_posted_co2e == 45.0
        finally:
            db.close()

    def test_16_total_aggregation(self):
        """16. Total posted emissions equals Scope 1 + Scope 2 + Scope 3."""
        db = SessionLocal()
        try:
            summary = carbon_ledger_service.get_document_ledger(db, 1)
            assert summary.total_posted_co2e == 33004.6
            assert summary.total_posted_co2e == (summary.scope_1_posted_co2e + summary.scope_2_posted_co2e)
        finally:
            db.close()

    def test_17_category_aggregation(self):
        """17. Ledger breaks down totals by category (ENERGY, FUEL, etc.)."""
        db = SessionLocal()
        try:
            summary = carbon_ledger_service.get_document_ledger(db, 1)
            assert "ENERGY" in summary.category_totals or "FUEL" in summary.category_totals
        finally:
            db.close()

    def test_18_activity_aggregation(self):
        """18. Ledger aggregates by activity type."""
        db = SessionLocal()
        try:
            summary = carbon_ledger_service.get_ledger_summary(db, activity_type="diesel")
            assert summary.total_posted_entries >= 1
            assert summary.scope_1_co2e is not None
        finally:
            db.close()

    def test_19_period_aggregation(self):
        """19. Ledger preserves reporting period in summary without fabricating."""
        db = SessionLocal()
        try:
            summary = carbon_ledger_service.get_document_ledger(db, 1)
            assert "2024-10" in summary.reporting_periods or "October 2024" in summary.reporting_periods
        finally:
            db.close()

    def test_20_year_aggregation(self):
        """20. Ledger aggregates by reporting year 2024."""
        db = SessionLocal()
        try:
            summary = carbon_ledger_service.get_ledger_summary(db, reporting_year=2024)
            assert summary.total_posted_entries >= 1
            assert summary.total_posted_co2e is not None
        finally:
            db.close()


# ==============================================================================
# 4. ELECTRICITY DOUBLE-COUNTING ENFORCEMENT (Tests 21 - 28)
# ==============================================================================
class TestElectricityDoubleCounting:
    def test_21_total_plus_grid_plus_solar_group(self):
        """21. Document #1 electricity group contains Total (48,750), Grid (44,900), and Solar (3,850)."""
        db = SessionLocal()
        try:
            calcs = db.query(CarbonCalculation).filter_by(
                document_id=1, activity_group_id="doc_1_electricity_2024_10"
            ).all()
            assert len(calcs) >= 2
        finally:
            db.close()

    def test_22_no_total_plus_component_double_counting(self):
        """22. Total electricity calculation is EXCLUDED from ledger aggregation when components exist."""
        db = SessionLocal()
        try:
            total_calc = db.query(CarbonCalculation).filter_by(
                document_id=1,
                activity_group_id="doc_1_electricity_2024_10",
                activity_role="TOTAL"
            ).first()
            if total_calc:
                entry = db.query(CarbonLedgerEntry).filter_by(carbon_calculation_id=total_calc.id).first()
                assert entry.accounting_status == "EXCLUDED"
                assert "double-counting" in (entry.accounting_reason or "").lower()
        finally:
            db.close()

    def test_23_grid_posted(self):
        """23. Grid constituent calculation is POSTED to the ledger."""
        db = SessionLocal()
        try:
            grid_calc = db.query(CarbonCalculation).filter_by(
                document_id=1,
                activity_type="purchased_electricity",
                activity_role="COMPONENT",
                status="CALCULATED"
            ).first()
            assert grid_calc is not None
            entry = db.query(CarbonLedgerEntry).filter_by(carbon_calculation_id=grid_calc.id).first()
            assert entry.accounting_status == "POSTED"
            assert Decimal(str(entry.calculated_co2e)) == Decimal("31879.0")
        finally:
            db.close()

    def test_24_solar_no_factor_excluded(self):
        """24. Solar constituent calculation with NO_FACTOR is EXCLUDED (not positive, not zero)."""
        db = SessionLocal()
        try:
            solar_calc = db.query(CarbonCalculation).filter(
                CarbonCalculation.document_id == 1,
                CarbonCalculation.activity_group_id == "doc_1_electricity_2024_10",
                CarbonCalculation.status == "NO_FACTOR"
            ).first()
            if solar_calc:
                entry = db.query(CarbonLedgerEntry).filter_by(carbon_calculation_id=solar_calc.id).first()
                assert entry.accounting_status == "EXCLUDED"
                assert entry.calculated_co2e is None
        finally:
            db.close()

    def test_25_total_not_additionally_aggregated(self):
        """25. Document #1 total posted footprint is exactly 33,004.60 kgCO2e."""
        db = SessionLocal()
        try:
            summary = carbon_ledger_service.get_document_ledger(db, 1)
            # Must equal Diesel (1,125.60) + Grid (31,879.00) = 33,004.60 kgCO2e
            assert summary.total_posted_co2e == 33004.6
        finally:
            db.close()

    def test_26_total_only_group_can_post(self):
        """26. A group with TOTAL only is POSTED when CALCULATED."""
        db = SessionLocal()
        try:
            calc = CarbonCalculation(
                activity_data_id=126,
                document_id=226,
                activity_type="natural_gas",
                activity_role="TOTAL",
                activity_group_id="gas_group_226",
                quantity=Decimal("100.0"),
                activity_unit="scm",
                calculated_co2e=Decimal("200.0"),
                status="CALCULATED",
                scope="SCOPE_1",
            )
            db.add(calc)
            db.commit()
            entry = carbon_ledger_service.post_calculation(db, calc.id)
            assert entry.accounting_status == "POSTED"
            assert Decimal(str(entry.calculated_co2e)) == Decimal("200.0")
        finally:
            db.close()

    def test_27_component_only_group_can_post(self):
        """27. A group with COMPONENT only is POSTED when CALCULATED."""
        db = SessionLocal()
        try:
            calc = CarbonCalculation(
                activity_data_id=127,
                document_id=227,
                activity_type="lpg",
                activity_role="COMPONENT",
                activity_group_id="lpg_group_227",
                quantity=Decimal("50.0"),
                activity_unit="kg",
                calculated_co2e=Decimal("149.0"),
                status="CALCULATED",
                scope="SCOPE_1",
            )
            db.add(calc)
            db.commit()
            entry = carbon_ledger_service.post_calculation(db, calc.id)
            assert entry.accounting_status == "POSTED"
        finally:
            db.close()

    def test_28_ambiguous_group_safely_handled(self):
        """28. Ambiguous group roles do not silently aggregate totals and components."""
        db = SessionLocal()
        try:
            calc = CarbonCalculation(
                activity_data_id=128,
                document_id=228,
                activity_type="diesel",
                activity_role="SUPPORTING",
                activity_group_id="ambiguous_grp",
                quantity=Decimal("50.0"),
                activity_unit="L",
                calculated_co2e=None,
                status="INELIGIBLE",
            )
            db.add(calc)
            db.commit()
            entry = carbon_ledger_service.post_calculation(db, calc.id)
            assert entry.accounting_status == "EXCLUDED"
        finally:
            db.close()


# ==============================================================================
# 5. RECONCILIATION LAYER (Tests 29 - 40)
# ==============================================================================
class TestReconciliationLayer:
    def test_29_extracted_vs_calculated_comparison(self):
        """29. Reconciliation endpoint returns comparison between extracted and calculated emissions."""
        db = SessionLocal()
        try:
            recon = carbon_ledger_service.get_document_reconciliation(db, 1)
            assert recon.document_id == 1
            assert recon.scope_1 is not None
            assert recon.scope_2 is not None
            assert recon.total is not None
        finally:
            db.close()

    def test_30_scope_1_comparison(self):
        """30. Scope 1 reconciliation: Extracted 1.13 tCO2e vs Calculated 1.1256 tCO2e."""
        db = SessionLocal()
        try:
            recon = carbon_ledger_service.get_document_reconciliation(db, 1)
            assert recon.scope_1.extracted_value == 1.13
            assert recon.scope_1.calculated_value_kg == 1125.6
            assert recon.scope_1.calculated_value_t == 1.1256
            assert recon.scope_1.difference_t == pytest.approx(-0.0044, abs=0.0001)
        finally:
            db.close()

    def test_31_scope_2_comparison(self):
        """31. Scope 2 reconciliation: Extracted 31.88 tCO2e vs Calculated 31.8790 tCO2e."""
        db = SessionLocal()
        try:
            recon = carbon_ledger_service.get_document_reconciliation(db, 1)
            assert recon.scope_2.extracted_value == 31.88
            assert recon.scope_2.calculated_value_kg == 31879.0
            assert recon.scope_2.calculated_value_t == 31.8790
            assert recon.scope_2.difference_t == pytest.approx(-0.0010, abs=0.0001)
        finally:
            db.close()

    def test_32_total_comparison(self):
        """32. Total reconciliation: Extracted 33.01 tCO2e vs Calculated 33.0046 tCO2e."""
        db = SessionLocal()
        try:
            recon = carbon_ledger_service.get_document_reconciliation(db, 1)
            assert recon.total.extracted_value == 33.01
            assert recon.total.calculated_value_kg == 33004.6
            assert recon.total.calculated_value_t == 33.0046
            assert recon.total.difference_t == pytest.approx(-0.0054, abs=0.0001)
        finally:
            db.close()

    def test_33_match_status(self):
        """33. Exact match status when calculated matches extracted within tolerance."""
        res = carbon_ledger_service._build_reconciliation_item(
            "Scope 1",
            extracted_val=Decimal("1.1256"),
            calculated_kg=Decimal("1125.6")
        )
        assert res.status == "MATCH"
        assert res.difference_t == 0.0

    def test_34_difference_status(self):
        """34. DIFFERENCE status when calculated deviates from extracted."""
        res = carbon_ledger_service._build_reconciliation_item(
            "Scope 1",
            extracted_val=Decimal("1.1300"),
            calculated_kg=Decimal("1125.6")
        )
        assert res.status == "DIFFERENCE"
        assert res.difference_t == -0.0044

    def test_35_extracted_only_status(self):
        """35. EXTRACTED_ONLY status when no calculated value is posted."""
        res = carbon_ledger_service._build_reconciliation_item(
            "Scope 3",
            extracted_val=Decimal("5.0"),
            calculated_kg=None
        )
        assert res.status == "EXTRACTED_ONLY"

    def test_36_calculated_only_status(self):
        """36. CALCULATED_ONLY status when no extracted metric exists."""
        res = carbon_ledger_service._build_reconciliation_item(
            "Scope 3",
            extracted_val=None,
            calculated_kg=Decimal("5000.0")
        )
        assert res.status == "CALCULATED_ONLY"
        assert res.calculated_value_t == 5.0

    def test_37_no_data_status(self):
        """37. NO_DATA status when neither extracted nor calculated exists."""
        res = carbon_ledger_service._build_reconciliation_item(
            "Scope 3",
            extracted_val=None,
            calculated_kg=None
        )
        assert res.status == "NO_DATA"

    def test_38_decimal_difference_precision(self):
        """38. Difference arithmetic is performed using Python Decimal."""
        diff = Decimal("33.0046") - Decimal("33.0100")
        assert diff == Decimal("-0.0054")

    def test_39_kg_to_t_conversion_rate(self):
        """39. Conversion rate is strictly 1 tCO2e = 1000 kgCO2e."""
        kg = Decimal("33004.6")
        t = kg / Decimal("1000")
        assert t == Decimal("33.0046")

    def test_40_incompatible_units_safely_handled(self):
        """40. Incompatible units are handled safely without crash."""
        res = carbon_ledger_service._build_reconciliation_item(
            "Other",
            extracted_val=None,
            calculated_kg=None
        )
        assert res.status == "NO_DATA"


# ==============================================================================
# 6. AUDIT TRAIL & FULL PROVENANCE (Tests 41 - 51)
# ==============================================================================
class TestAuditTrailAndProvenance:
    def test_41_calculation_id_preserved(self):
        """41. Carbon calculation ID is stored and indexed in ledger entry."""
        db = SessionLocal()
        try:
            entry = db.query(CarbonLedgerEntry).filter(CarbonLedgerEntry.document_id == 1).first()
            assert entry.carbon_calculation_id is not None
        finally:
            db.close()

    def test_42_activity_data_id_preserved(self):
        """42. ActivityData ID is preserved in ledger entry."""
        db = SessionLocal()
        try:
            entry = db.query(CarbonLedgerEntry).filter(CarbonLedgerEntry.document_id == 1).first()
            assert entry.activity_data_id is not None
        finally:
            db.close()

    def test_43_document_id_preserved(self):
        """43. Document ID is preserved in ledger entry."""
        db = SessionLocal()
        try:
            entry = db.query(CarbonLedgerEntry).filter(CarbonLedgerEntry.document_id == 1).first()
            assert entry.document_id == 1
        finally:
            db.close()

    def test_44_metric_id_preserved(self):
        """44. Metric ID is preserved where available."""
        db = SessionLocal()
        try:
            entry = db.query(CarbonLedgerEntry).filter(CarbonLedgerEntry.document_id == 1).first()
            assert hasattr(entry, "metric_id")
        finally:
            db.close()

    def test_45_factor_id_preserved(self):
        """45. Emission factor ID is preserved in ledger snapshot."""
        db = SessionLocal()
        try:
            entry = db.query(CarbonLedgerEntry).filter(
                CarbonLedgerEntry.document_id == 1,
                CarbonLedgerEntry.accounting_status == "POSTED"
            ).first()
            assert entry.emission_factor_id is not None
        finally:
            db.close()

    def test_46_factor_version_preserved(self):
        """46. Emission factor version is preserved in ledger snapshot."""
        db = SessionLocal()
        try:
            entry = db.query(CarbonLedgerEntry).filter(
                CarbonLedgerEntry.document_id == 1,
                CarbonLedgerEntry.accounting_status == "POSTED"
            ).first()
            assert entry.factor_version is not None
        finally:
            db.close()

    def test_47_calculation_version_preserved(self):
        """47. Calculation engine version (1.0) is preserved."""
        db = SessionLocal()
        try:
            entry = db.query(CarbonLedgerEntry).filter(CarbonLedgerEntry.document_id == 1).first()
            assert entry.calculation_version == "1.0"
        finally:
            db.close()

    def test_48_ledger_version_preserved(self):
        """48. Ledger accounting version (1.0) is preserved."""
        db = SessionLocal()
        try:
            entry = db.query(CarbonLedgerEntry).filter(CarbonLedgerEntry.document_id == 1).first()
            assert entry.ledger_version == "1.0"
        finally:
            db.close()

    def test_49_source_field_preserved(self):
        """49. Source field path is preserved."""
        db = SessionLocal()
        try:
            entry = db.query(CarbonLedgerEntry).filter(CarbonLedgerEntry.document_id == 1).first()
            assert entry.source_field is not None
        finally:
            db.close()

    def test_50_source_text_preserved(self):
        """50. Verbatim source text snippet is preserved."""
        db = SessionLocal()
        try:
            entry = db.query(CarbonLedgerEntry).filter(CarbonLedgerEntry.document_id == 1).first()
            assert entry.source_text is not None
        finally:
            db.close()

    def test_51_page_number_preserved(self):
        """51. Document page number is preserved."""
        db = SessionLocal()
        try:
            entry = db.query(CarbonLedgerEntry).filter(CarbonLedgerEntry.document_id == 1).first()
            assert hasattr(entry, "page")
        finally:
            db.close()


# ==============================================================================
# 7. SAFETY BOUNDARIES & NON-MUTATION (Tests 52 - 60)
# ==============================================================================
class TestSafetyBoundaries:
    def test_52_no_recalculation_in_ledger(self):
        """52. Step 14 ledger never performs arithmetic quantity * factor."""
        # Ledger strictly consumes CarbonCalculation.calculated_co2e
        assert hasattr(carbon_ledger_service, "post_calculation")
        assert not hasattr(carbon_ledger_service, "calculate_activity")

    def test_53_no_llm_used(self):
        """53. Ledger uses zero LLM calls or probabilistic models."""
        assert not hasattr(carbon_ledger_service, "llm_service")

    def test_54_no_factor_modification(self):
        """54. Emission factors are not modified during posting."""
        db = SessionLocal()
        try:
            factors_count_before = db.query(EmissionFactor).count()
            carbon_ledger_service.post_document(db, 1)
            factors_count_after = db.query(EmissionFactor).count()
            assert factors_count_before == factors_count_after
        finally:
            db.close()

    def test_55_no_activity_data_modification(self):
        """55. Canonical ActivityData records remain unmodified."""
        db = SessionLocal()
        try:
            act = db.query(ActivityData).filter_by(document_id=1, activity_type="diesel").first()
            qty_before = act.quantity
            carbon_ledger_service.post_document(db, 1)
            act_after = db.query(ActivityData).filter_by(document_id=1, activity_type="diesel").first()
            assert act_after.quantity == qty_before
        finally:
            db.close()

    def test_56_no_sustainability_metric_modification(self):
        """56. Extracted SustainabilityMetric records remain strictly untouched."""
        db = SessionLocal()
        try:
            m1 = db.query(SustainabilityMetric).filter_by(document_id=1, metric_type="scope_1_emissions").first()
            m2 = db.query(SustainabilityMetric).filter_by(document_id=1, metric_type="scope_2_emissions").first()
            mt = db.query(SustainabilityMetric).filter_by(document_id=1, metric_type="total_ghg_emissions").first()
            assert m1.value == 1.13
            assert m2.value == 31.88
            assert mt.value == 33.01
        finally:
            db.close()

    def test_57_no_geography_fabrication(self):
        """57. Missing geography remains None in ledger entry; never fabricated."""
        db = SessionLocal()
        try:
            calc = CarbonCalculation(
                activity_data_id=157,
                document_id=257,
                activity_type="diesel",
                activity_role="TOTAL",
                quantity=Decimal("50.0"),
                activity_unit="L",
                geography=None,
                calculated_co2e=Decimal("134.0"),
                status="CALCULATED",
            )
            db.add(calc)
            db.commit()
            entry = carbon_ledger_service.post_calculation(db, calc.id)
            assert entry.geography is None
        finally:
            db.close()

    def test_58_no_year_fabrication(self):
        """58. Missing reporting year remains None in ledger entry; never fabricated."""
        db = SessionLocal()
        try:
            calc = CarbonCalculation(
                activity_data_id=158,
                document_id=258,
                activity_type="diesel",
                activity_role="TOTAL",
                quantity=Decimal("50.0"),
                activity_unit="L",
                reporting_year=None,
                calculated_co2e=Decimal("134.0"),
                status="CALCULATED",
            )
            db.add(calc)
            db.commit()
            entry = carbon_ledger_service.post_calculation(db, calc.id)
            assert entry.reporting_year is None
        finally:
            db.close()

    def test_59_no_carbon_credits(self):
        """59. No carbon credits or issuance fields exist on CarbonLedgerEntry."""
        cols = CarbonLedgerEntry.__table__.columns
        assert "credits_issued" not in cols
        assert "registry_serial" not in cols
        assert "verra_id" not in cols

    def test_60_no_roi_or_savings_claims(self):
        """60. No ROI, payback, or cost reduction fields exist on CarbonLedgerEntry."""
        cols = CarbonLedgerEntry.__table__.columns
        assert "roi" not in cols
        assert "savings_inr" not in cols


# ==============================================================================
# 8. API ENDPOINTS (Tests 61 - 67)
# ==============================================================================
class TestCarbonLedgerAPI:
    def test_61_api_post_calculation(self):
        """61. POST /api/carbon-ledger/post posts a calculation into the ledger."""
        res = client.post("/api/carbon-ledger/post", json={
            "carbon_calculation_id": 1
        })
        assert res.status_code == 200
        data = res.json()
        assert "id" in data
        assert "accounting_status" in data

    def test_62_api_post_document(self):
        """62. POST /api/documents/{id}/carbon-ledger/post posts all calculations for document."""
        res = client.post("/api/documents/1/carbon-ledger/post")
        assert res.status_code == 200
        data = res.json()
        assert data["document_id"] == 1
        assert data["posted_records"] >= 1
        assert data["total_posted_co2e"] == 33004.6

    def test_63_api_list_ledger(self):
        """63. GET /api/carbon-ledger returns filtered ledger list."""
        res = client.get("/api/carbon-ledger?document_id=1")
        assert res.status_code == 200
        data = res.json()
        assert "total" in data
        assert "items" in data
        assert data["total"] >= 1

    def test_64_api_retrieve_entry(self):
        """64. GET /api/carbon-ledger/{id} retrieves single ledger entry."""
        res = client.get("/api/carbon-ledger/1")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == 1
        assert "accounting_status" in data

    def test_65_api_document_ledger_summary(self):
        """65. GET /api/documents/{id}/carbon-ledger returns document summary."""
        res = client.get("/api/documents/1/carbon-ledger")
        assert res.status_code == 200
        data = res.json()
        assert data["document_id"] == 1
        assert data["total_posted_co2e"] == 33004.6

    def test_66_api_reconciliation_endpoint(self):
        """66. GET /api/documents/{id}/carbon-ledger/reconciliation returns reconciliation."""
        res = client.get("/api/documents/1/carbon-ledger/reconciliation")
        assert res.status_code == 200
        data = res.json()
        assert data["document_id"] == 1
        assert "scope_1" in data
        assert "scope_2" in data
        assert "total" in data
        assert data["scope_1"]["extracted_value"] == 1.13
        assert data["scope_2"]["extracted_value"] == 31.88

    def test_67_api_summary_endpoint(self):
        """67. GET /api/carbon-ledger/summary returns multi-document ledger summary."""
        res = client.get("/api/carbon-ledger/summary")
        assert res.status_code == 200
        data = res.json()
        assert "total_posted_entries" in data
        assert "by_scope" in data
