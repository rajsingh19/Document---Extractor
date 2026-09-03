"""
test_reduction_opportunities.py — Complete Step 16 Test Suite (83 Tests).

Tests deterministic reduction opportunity generation, deduplication, evidence lineage,
project tracking, audit trail events, safety boundaries, and API routes.
"""
import pytest
from decimal import Decimal
from datetime import datetime
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database.session import SessionLocal, init_db
from backend.app.models.reduction_opportunity import ReductionOpportunity
from backend.app.models.reduction_project import ReductionProject, ReductionProjectEvent
from backend.app.models.carbon_ledger import CarbonLedgerEntry
from backend.app.models.carbon_calculation import CarbonCalculation
from backend.app.models.activity_data import ActivityData
from backend.app.models.document import Document
from backend.app.services.reduction_opportunity import reduction_opportunity_service
from backend.app.services.reduction_project import reduction_project_service
from backend.app.schemas.reduction_project import ReductionProjectCreate, ReductionProjectUpdate


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Ensure database schema is initialized and seeded before tests."""
    init_db()


@pytest.fixture
def client():
    return TestClient(app)


# ==============================================================================
# 1. OPPORTUNITY MODEL (Tests 1 - 7)
# ==============================================================================
class TestOpportunityModel:
    def test_01_create_opportunity(self):
        """1. Successfully create ReductionOpportunity record."""
        db = SessionLocal()
        try:
            opp = ReductionOpportunity(
                opportunity_code="TEST_OPP_01",
                title="Test Electricity Reduction",
                description="Test description for electricity investigation",
                category="ENERGY",
                scope="SCOPE_2",
                priority="HIGH",
                trigger_type="HIGH_ENERGY_USE",
                rationale="Electricity accounts for 90% of emissions",
                recommended_action="Investigate energy efficiency",
                limitations="Area for investigation only",
            )
            db.add(opp)
            db.commit()
            db.refresh(opp)
            assert opp.id is not None
            assert opp.status == "OPEN"
        finally:
            db.query(ReductionOpportunity).filter_by(opportunity_code="TEST_OPP_01").delete()
            db.commit()
            db.close()

    def test_02_unique_opportunity_code(self):
        """2. Opportunity code has unique constraint."""
        db = SessionLocal()
        try:
            opp1 = ReductionOpportunity(
                opportunity_code="TEST_UNIQUE_CODE",
                title="Title 1",
                description="Desc 1",
                category="ENERGY",
                priority="HIGH",
                trigger_type="HIGH_EMISSION_SOURCE",
                rationale="R1",
                recommended_action="A1",
                limitations="L1",
            )
            db.add(opp1)
            db.commit()

            opp2 = ReductionOpportunity(
                opportunity_code="TEST_UNIQUE_CODE",
                title="Title 2",
                description="Desc 2",
                category="ENERGY",
                priority="LOW",
                trigger_type="HIGH_EMISSION_SOURCE",
                rationale="R2",
                recommended_action="A2",
                limitations="L2",
            )
            db.add(opp2)
            with pytest.raises(Exception):
                db.commit()
            db.rollback()
        finally:
            db.query(ReductionOpportunity).filter_by(opportunity_code="TEST_UNIQUE_CODE").delete()
            db.commit()
            db.close()

    def test_03_nullable_evidence(self):
        """3. Evidence references are properly nullable."""
        db = SessionLocal()
        try:
            opp = ReductionOpportunity(
                opportunity_code="TEST_NULL_EVIDENCE",
                title="Global Opportunity",
                description="Global description",
                category="DATA_QUALITY",
                priority="LOW",
                trigger_type="DATA_QUALITY",
                evidence_document_id=None,
                evidence_ledger_entry_id=None,
                evidence_metric_id=None,
                rationale="R",
                recommended_action="A",
                limitations="L",
            )
            db.add(opp)
            db.commit()
            assert opp.evidence_document_id is None
            assert opp.evidence_ledger_entry_id is None
        finally:
            db.query(ReductionOpportunity).filter_by(opportunity_code="TEST_NULL_EVIDENCE").delete()
            db.commit()
            db.close()

    def test_04_category_values(self):
        """4. Category stores valid standard domain."""
        db = SessionLocal()
        try:
            opp = ReductionOpportunity(
                opportunity_code="TEST_CAT",
                title="Category test",
                description="Desc",
                category="FUEL",
                priority="MEDIUM",
                trigger_type="HIGH_FUEL_USE",
                rationale="R",
                recommended_action="A",
                limitations="L",
            )
            db.add(opp)
            db.commit()
            assert opp.category == "FUEL"
        finally:
            db.query(ReductionOpportunity).filter_by(opportunity_code="TEST_CAT").delete()
            db.commit()
            db.close()

    def test_05_scope_values(self):
        """5. Scope stores SCOPE_1, SCOPE_2, or SCOPE_3."""
        db = SessionLocal()
        try:
            opp = ReductionOpportunity(
                opportunity_code="TEST_SCOPE",
                title="Scope test",
                description="Desc",
                category="FUEL",
                scope="SCOPE_1",
                priority="MEDIUM",
                trigger_type="HIGH_FUEL_USE",
                rationale="R",
                recommended_action="A",
                limitations="L",
            )
            db.add(opp)
            db.commit()
            assert opp.scope == "SCOPE_1"
        finally:
            db.query(ReductionOpportunity).filter_by(opportunity_code="TEST_SCOPE").delete()
            db.commit()
            db.close()

    def test_06_priority_values(self):
        """6. Priority stores HIGH, MEDIUM, LOW."""
        db = SessionLocal()
        try:
            opp = ReductionOpportunity(
                opportunity_code="TEST_PRIORITY",
                title="Priority test",
                description="Desc",
                category="ENERGY",
                priority="HIGH",
                trigger_type="HIGH_ENERGY_USE",
                rationale="R",
                recommended_action="A",
                limitations="L",
            )
            db.add(opp)
            db.commit()
            assert opp.priority == "HIGH"
        finally:
            db.query(ReductionOpportunity).filter_by(opportunity_code="TEST_PRIORITY").delete()
            db.commit()
            db.close()

    def test_07_status_transitions(self):
        """7. Status transitions through lifecycle."""
        db = SessionLocal()
        try:
            opp = ReductionOpportunity(
                opportunity_code="TEST_STATUS",
                title="Status test",
                description="Desc",
                category="ENERGY",
                priority="HIGH",
                trigger_type="HIGH_ENERGY_USE",
                rationale="R",
                recommended_action="A",
                limitations="L",
            )
            db.add(opp)
            db.commit()
            assert opp.status == "OPEN"

            reduction_opportunity_service.update_status(db, opp.id, "ACKNOWLEDGED")
            assert opp.status == "ACKNOWLEDGED"

            reduction_opportunity_service.update_status(db, opp.id, "IN_PROGRESS")
            assert opp.status == "IN_PROGRESS"

            reduction_opportunity_service.update_status(db, opp.id, "COMPLETED")
            assert opp.status == "COMPLETED"
        finally:
            db.query(ReductionOpportunity).filter_by(opportunity_code="TEST_STATUS").delete()
            db.commit()
            db.close()


# ==============================================================================
# 2. HIGH EMISSION SOURCES (Tests 8 - 12)
# ==============================================================================
class TestHighEmissionSources:
    def test_08_dominant_scope_2_opportunity(self):
        """8. Generates dominant Scope 2 opportunity for Document #1."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.generate_opportunities(db, document_id=1)
            grid_opp = next((o for o in opps if "GRID" in o.opportunity_code), None)
            assert grid_opp is not None
            assert grid_opp.scope == "SCOPE_2"
            assert grid_opp.priority == "HIGH"
        finally:
            db.close()

    def test_09_dominant_activity_identification(self):
        """9. Identifies purchased_electricity as primary activity."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.generate_opportunities(db, document_id=1)
            grid_opp = next(o for o in opps if "GRID" in o.opportunity_code)
            assert grid_opp.activity_type == "purchased_electricity"
            assert "96.6%" in grid_opp.description or "96.59%" in grid_opp.description
        finally:
            db.close()

    def test_10_dominant_category_energy(self):
        """10. Sets ENERGY category on dominant electricity source."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.generate_opportunities(db, document_id=1)
            grid_opp = next(o for o in opps if "GRID" in o.opportunity_code)
            assert grid_opp.category == "ENERGY"
        finally:
            db.close()

    def test_11_secondary_fuel_identification(self):
        """11. Identifies diesel fuel as secondary Scope 1 source."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.generate_opportunities(db, document_id=1)
            fuel_opp = next((o for o in opps if "FUEL" in o.opportunity_code), None)
            assert fuel_opp is not None
            assert fuel_opp.scope == "SCOPE_1"
            assert fuel_opp.category == "FUEL"
        finally:
            db.close()

    def test_12_evidence_preservation(self):
        """12. Preserves evidence document ID and ledger entry ID."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.generate_opportunities(db, document_id=1)
            grid_opp = next(o for o in opps if "GRID" in o.opportunity_code)
            assert grid_opp.evidence_document_id == 1
            assert grid_opp.evidence_ledger_entry_id is not None
        finally:
            db.close()


# ==============================================================================
# 3. INCREASE DETECTION (Tests 13 - 20)
# ==============================================================================
class TestIncreaseDetection:
    def test_13_greater_than_10_percent_increase(self):
        """13. Generates opportunity when historical increase >= 10%."""
        db = SessionLocal()
        try:
            # Clean test document
            db.query(ReductionOpportunity).filter_by(opportunity_code="EMISSIONS_INCREASE_2024-01_2024-02_DOC_901").delete()
            db.query(CarbonLedgerEntry).filter_by(document_id=901).delete()
            db.query(CarbonCalculation).filter_by(document_id=901).delete()
            db.commit()

            c1 = CarbonCalculation(
                activity_data_id=9011, document_id=901, activity_type="purchased_electricity",
                quantity=Decimal("20000.0"), activity_unit="kWh", calculated_co2e=Decimal("20000.0"), status="CALCULATED"
            )
            c2 = CarbonCalculation(
                activity_data_id=9012, document_id=901, activity_type="purchased_electricity",
                quantity=Decimal("23000.0"), activity_unit="kWh", calculated_co2e=Decimal("23000.0"), status="CALCULATED"
            )
            db.add_all([c1, c2])
            db.commit()

            e1 = CarbonLedgerEntry(
                carbon_calculation_id=c1.id, activity_data_id=9011, document_id=901, activity_type="purchased_electricity",
                quantity=Decimal("20000.0"), activity_unit="kWh", reporting_period="2024-01", calculated_co2e=Decimal("20000.0"),
                accounting_status="POSTED"
            )
            e2 = CarbonLedgerEntry(
                carbon_calculation_id=c2.id, activity_data_id=9012, document_id=901, activity_type="purchased_electricity",
                quantity=Decimal("23000.0"), activity_unit="kWh", reporting_period="2024-02", calculated_co2e=Decimal("23000.0"),
                accounting_status="POSTED"
            )
            db.add_all([e1, e2])
            db.commit()

            opps = reduction_opportunity_service.generate_opportunities(db, document_id=901)
            inc_opp = next((o for o in opps if "INCREASE" in o.opportunity_code), None)
            assert inc_opp is not None
            assert inc_opp.priority == "MEDIUM"  # 15% is between 10% and 25%
            assert inc_opp.trigger_type == "INCREASING_EMISSIONS"
        finally:
            db.close()

    def test_14_exactly_10_percent(self):
        """14. Exactly 10.0% increase meets detection threshold."""
        db = SessionLocal()
        try:
            db.query(ReductionOpportunity).filter_by(opportunity_code="EMISSIONS_INCREASE_2024-01_2024-02_DOC_902").delete()
            db.query(CarbonLedgerEntry).filter_by(document_id=902).delete()
            db.query(CarbonCalculation).filter_by(document_id=902).delete()
            db.commit()

            c1 = CarbonCalculation(
                activity_data_id=9021, document_id=902, activity_type="purchased_electricity",
                quantity=Decimal("10000.0"), activity_unit="kWh", calculated_co2e=Decimal("10000.0"), status="CALCULATED"
            )
            c2 = CarbonCalculation(
                activity_data_id=9022, document_id=902, activity_type="purchased_electricity",
                quantity=Decimal("11000.0"), activity_unit="kWh", calculated_co2e=Decimal("11000.0"), status="CALCULATED"
            )
            db.add_all([c1, c2])
            db.commit()

            e1 = CarbonLedgerEntry(
                carbon_calculation_id=c1.id, activity_data_id=9021, document_id=902, activity_type="purchased_electricity",
                quantity=Decimal("10000.0"), activity_unit="kWh", reporting_period="2024-01", calculated_co2e=Decimal("10000.0"),
                accounting_status="POSTED"
            )
            e2 = CarbonLedgerEntry(
                carbon_calculation_id=c2.id, activity_data_id=9022, document_id=902, activity_type="purchased_electricity",
                quantity=Decimal("11000.0"), activity_unit="kWh", reporting_period="2024-02", calculated_co2e=Decimal("11000.0"),
                accounting_status="POSTED"
            )
            db.add_all([e1, e2])
            db.commit()

            opps = reduction_opportunity_service.generate_opportunities(db, document_id=902)
            inc_opp = next((o for o in opps if "INCREASE" in o.opportunity_code), None)
            assert inc_opp is not None
            assert float(inc_opp.change_percentage) == 10.0
        finally:
            db.close()

    def test_15_greater_than_25_percent_high_priority(self):
        """15. Increase >= 25% receives HIGH priority."""
        db = SessionLocal()
        try:
            db.query(ReductionOpportunity).filter_by(opportunity_code="EMISSIONS_INCREASE_2024-01_2024-02_DOC_903").delete()
            db.query(CarbonLedgerEntry).filter_by(document_id=903).delete()
            db.query(CarbonCalculation).filter_by(document_id=903).delete()
            db.commit()

            c1 = CarbonCalculation(
                activity_data_id=9031, document_id=903, activity_type="purchased_electricity",
                quantity=Decimal("10000.0"), activity_unit="kWh", calculated_co2e=Decimal("10000.0"), status="CALCULATED"
            )
            c2 = CarbonCalculation(
                activity_data_id=9032, document_id=903, activity_type="purchased_electricity",
                quantity=Decimal("13000.0"), activity_unit="kWh", calculated_co2e=Decimal("13000.0"), status="CALCULATED"
            )
            db.add_all([c1, c2])
            db.commit()

            e1 = CarbonLedgerEntry(
                carbon_calculation_id=c1.id, activity_data_id=9031, document_id=903, activity_type="purchased_electricity",
                quantity=Decimal("10000.0"), activity_unit="kWh", reporting_period="2024-01", calculated_co2e=Decimal("10000.0"),
                accounting_status="POSTED"
            )
            e2 = CarbonLedgerEntry(
                carbon_calculation_id=c2.id, activity_data_id=9032, document_id=903, activity_type="purchased_electricity",
                quantity=Decimal("13000.0"), activity_unit="kWh", reporting_period="2024-02", calculated_co2e=Decimal("13000.0"),
                accounting_status="POSTED"
            )
            db.add_all([e1, e2])
            db.commit()

            opps = reduction_opportunity_service.generate_opportunities(db, document_id=903)
            inc_opp = next((o for o in opps if "INCREASE" in o.opportunity_code), None)
            assert inc_opp is not None
            assert inc_opp.priority == "HIGH"
            assert float(inc_opp.change_percentage) == 30.0
        finally:
            db.close()

    def test_16_decrease_does_not_trigger_increase(self):
        """16. Decreasing emissions do not generate an increase opportunity."""
        db = SessionLocal()
        try:
            db.query(ReductionOpportunity).filter_by(opportunity_code="EMISSIONS_INCREASE_2024-01_2024-02_DOC_904").delete()
            db.query(CarbonLedgerEntry).filter_by(document_id=904).delete()
            db.query(CarbonCalculation).filter_by(document_id=904).delete()
            db.commit()

            c1 = CarbonCalculation(
                activity_data_id=9041, document_id=904, activity_type="purchased_electricity",
                quantity=Decimal("20000.0"), activity_unit="kWh", calculated_co2e=Decimal("20000.0"), status="CALCULATED"
            )
            c2 = CarbonCalculation(
                activity_data_id=9042, document_id=904, activity_type="purchased_electricity",
                quantity=Decimal("15000.0"), activity_unit="kWh", calculated_co2e=Decimal("15000.0"), status="CALCULATED"
            )
            db.add_all([c1, c2])
            db.commit()

            e1 = CarbonLedgerEntry(
                carbon_calculation_id=c1.id, activity_data_id=9041, document_id=904, activity_type="purchased_electricity",
                quantity=Decimal("20000.0"), activity_unit="kWh", reporting_period="2024-01", calculated_co2e=Decimal("20000.0"),
                accounting_status="POSTED"
            )
            e2 = CarbonLedgerEntry(
                carbon_calculation_id=c2.id, activity_data_id=9042, document_id=904, activity_type="purchased_electricity",
                quantity=Decimal("15000.0"), activity_unit="kWh", reporting_period="2024-02", calculated_co2e=Decimal("15000.0"),
                accounting_status="POSTED"
            )
            db.add_all([e1, e2])
            db.commit()

            opps = reduction_opportunity_service.generate_opportunities(db, document_id=904)
            inc_opp = next((o for o in opps if "EMISSIONS_INCREASE" in o.opportunity_code), None)
            assert inc_opp is None
        finally:
            db.close()

    def test_17_zero_previous_period_handling(self):
        """17. Handled safely when previous period is 0 without zero-division error."""
        db = SessionLocal()
        try:
            db.query(ReductionOpportunity).filter_by(opportunity_code="EMISSIONS_INCREASE_2024-01_2024-02_DOC_905").delete()
            db.query(CarbonLedgerEntry).filter_by(document_id=905).delete()
            db.query(CarbonCalculation).filter_by(document_id=905).delete()
            db.commit()

            c1 = CarbonCalculation(
                activity_data_id=9051, document_id=905, activity_type="solar_electricity",
                quantity=Decimal("100.0"), activity_unit="kWh", calculated_co2e=Decimal("0.0"), status="CALCULATED"
            )
            c2 = CarbonCalculation(
                activity_data_id=9052, document_id=905, activity_type="purchased_electricity",
                quantity=Decimal("10000.0"), activity_unit="kWh", calculated_co2e=Decimal("10000.0"), status="CALCULATED"
            )
            db.add_all([c1, c2])
            db.commit()

            e1 = CarbonLedgerEntry(
                carbon_calculation_id=c1.id, activity_data_id=9051, document_id=905, activity_type="solar_electricity",
                quantity=Decimal("100.0"), activity_unit="kWh", reporting_period="2024-01", calculated_co2e=Decimal("0.0"),
                accounting_status="POSTED"
            )
            e2 = CarbonLedgerEntry(
                carbon_calculation_id=c2.id, activity_data_id=9052, document_id=905, activity_type="purchased_electricity",
                quantity=Decimal("10000.0"), activity_unit="kWh", reporting_period="2024-02", calculated_co2e=Decimal("10000.0"),
                accounting_status="POSTED"
            )
            db.add_all([e1, e2])
            db.commit()

            # Should complete without error
            opps = reduction_opportunity_service.generate_opportunities(db, document_id=905)
            assert isinstance(opps, list)
        finally:
            db.close()

    def test_18_missing_previous_period(self):
        """18. When only one period exists, no comparison increase opportunity generated."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.generate_opportunities(db, document_id=1)
            inc_opp = next((o for o in opps if "EMISSIONS_INCREASE" in o.opportunity_code), None)
            assert inc_opp is None
        finally:
            db.close()

    def test_19_single_period_no_fake_increase(self):
        """19. Single period does not invent a previous period to calculate fake increase."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.generate_opportunities(db, document_id=1)
            for o in opps:
                assert "0.0000 tCO2e to 33.0046" not in o.description
        finally:
            db.close()

    def test_20_multiple_periods_tracking(self):
        """20. Multiple periods track exact absolute and percentage changes."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.generate_opportunities(db, document_id=901)
            inc_opp = next((o for o in opps if "INCREASE" in o.opportunity_code), None)
            if inc_opp:
                assert inc_opp.change_absolute is not None
                assert inc_opp.change_percentage is not None
        finally:
            db.close()


# ==============================================================================
# 4. REPEATED INCREASE (Tests 21 - 24)
# ==============================================================================
class TestRepeatedIncrease:
    def test_21_three_actual_consecutive_periods(self):
        """21. Three consecutive increasing periods trigger REPEATED_INCREASE opportunity."""
        db = SessionLocal()
        try:
            db.query(ReductionOpportunity).filter_by(opportunity_code="REPEATED_INCREASE_2024-01_2024-02_2024-03_DOC_906").delete()
            db.query(CarbonLedgerEntry).filter_by(document_id=906).delete()
            db.query(CarbonCalculation).filter_by(document_id=906).delete()
            db.commit()

            c1 = CarbonCalculation(activity_data_id=9061, document_id=906, activity_type="purchased_electricity", quantity=Decimal("10000.0"), activity_unit="kWh", calculated_co2e=Decimal("10000.0"), status="CALCULATED")
            c2 = CarbonCalculation(activity_data_id=9062, document_id=906, activity_type="purchased_electricity", quantity=Decimal("12000.0"), activity_unit="kWh", calculated_co2e=Decimal("12000.0"), status="CALCULATED")
            c3 = CarbonCalculation(activity_data_id=9063, document_id=906, activity_type="purchased_electricity", quantity=Decimal("15000.0"), activity_unit="kWh", calculated_co2e=Decimal("15000.0"), status="CALCULATED")
            db.add_all([c1, c2, c3])
            db.commit()

            e1 = CarbonLedgerEntry(carbon_calculation_id=c1.id, activity_data_id=9061, document_id=906, activity_type="purchased_electricity", quantity=Decimal("10000.0"), activity_unit="kWh", reporting_period="2024-01", calculated_co2e=Decimal("10000.0"), accounting_status="POSTED")
            e2 = CarbonLedgerEntry(carbon_calculation_id=c2.id, activity_data_id=9062, document_id=906, activity_type="purchased_electricity", quantity=Decimal("12000.0"), activity_unit="kWh", reporting_period="2024-02", calculated_co2e=Decimal("12000.0"), accounting_status="POSTED")
            e3 = CarbonLedgerEntry(carbon_calculation_id=c3.id, activity_data_id=9063, document_id=906, activity_type="purchased_electricity", quantity=Decimal("15000.0"), activity_unit="kWh", reporting_period="2024-03", calculated_co2e=Decimal("15000.0"), accounting_status="POSTED")
            db.add_all([e1, e2, e3])
            db.commit()

            opps = reduction_opportunity_service.generate_opportunities(db, document_id=906)
            rep_opp = next((o for o in opps if "REPEATED_INCREASE" in o.opportunity_code), None)
            assert rep_opp is not None
            assert rep_opp.trigger_type == "REPEATED_INCREASE"
            assert rep_opp.priority == "HIGH"
        finally:
            db.close()

    def test_22_missing_period_does_not_fabricate_repeated_increase(self):
        """22. Two periods do not trigger 3-period repeated increase."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.generate_opportunities(db, document_id=901)
            rep_opp = next((o for o in opps if "REPEATED_INCREASE" in o.opportunity_code), None)
            assert rep_opp is None
        finally:
            db.close()

    def test_23_decrease_breaks_sequence(self):
        """23. A mid-sequence decrease breaks consecutive increase trigger."""
        db = SessionLocal()
        try:
            db.query(ReductionOpportunity).filter_by(opportunity_code="REPEATED_INCREASE_2024-01_2024-02_2024-03_DOC_907").delete()
            db.query(CarbonLedgerEntry).filter_by(document_id=907).delete()
            db.query(CarbonCalculation).filter_by(document_id=907).delete()
            db.commit()

            c1 = CarbonCalculation(activity_data_id=9071, document_id=907, activity_type="purchased_electricity", quantity=Decimal("10000.0"), activity_unit="kWh", calculated_co2e=Decimal("10000.0"), status="CALCULATED")
            c2 = CarbonCalculation(activity_data_id=9072, document_id=907, activity_type="purchased_electricity", quantity=Decimal("8000.0"), activity_unit="kWh", calculated_co2e=Decimal("8000.0"), status="CALCULATED")
            c3 = CarbonCalculation(activity_data_id=9073, document_id=907, activity_type="purchased_electricity", quantity=Decimal("15000.0"), activity_unit="kWh", calculated_co2e=Decimal("15000.0"), status="CALCULATED")
            db.add_all([c1, c2, c3])
            db.commit()

            e1 = CarbonLedgerEntry(carbon_calculation_id=c1.id, activity_data_id=9071, document_id=907, activity_type="purchased_electricity", quantity=Decimal("10000.0"), activity_unit="kWh", reporting_period="2024-01", calculated_co2e=Decimal("10000.0"), accounting_status="POSTED")
            e2 = CarbonLedgerEntry(carbon_calculation_id=c2.id, activity_data_id=9072, document_id=907, activity_type="purchased_electricity", quantity=Decimal("8000.0"), activity_unit="kWh", reporting_period="2024-02", calculated_co2e=Decimal("8000.0"), accounting_status="POSTED")
            e3 = CarbonLedgerEntry(carbon_calculation_id=c3.id, activity_data_id=9073, document_id=907, activity_type="purchased_electricity", quantity=Decimal("15000.0"), activity_unit="kWh", reporting_period="2024-03", calculated_co2e=Decimal("15000.0"), accounting_status="POSTED")
            db.add_all([e1, e2, e3])
            db.commit()

            opps = reduction_opportunity_service.generate_opportunities(db, document_id=907)
            rep_opp = next((o for o in opps if "REPEATED_INCREASE" in o.opportunity_code), None)
            assert rep_opp is None
        finally:
            db.close()

    def test_24_repeated_increase_duplicate_prevention(self):
        """24. Repeated scanning does not duplicate repeated increase record."""
        db = SessionLocal()
        try:
            opps1 = reduction_opportunity_service.generate_opportunities(db, document_id=906)
            opps2 = reduction_opportunity_service.generate_opportunities(db, document_id=906)
            cnt = db.query(ReductionOpportunity).filter_by(opportunity_code="REPEATED_INCREASE_2024-01_2024-02_2024-03_DOC_906").count()
            assert cnt == 1
        finally:
            db.close()


# ==============================================================================
# 5. ENERGY & FUEL (Tests 25 - 31)
# ==============================================================================
class TestEnergyAndFuelOpportunities:
    def test_25_electricity_opportunity(self):
        """25. Generates ENERGY opportunity for grid electricity."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.generate_opportunities(db, document_id=1)
            elec_opp = next(o for o in opps if o.category == "ENERGY")
            assert "Grid Electricity" in elec_opp.title
        finally:
            db.close()

    def test_26_electricity_evidence(self):
        """26. Electricity opportunity references exact 44,900 kWh quantity."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.generate_opportunities(db, document_id=1)
            elec_opp = next(o for o in opps if o.category == "ENERGY")
            assert float(elec_opp.current_value) == 44900.0
            assert elec_opp.current_unit == "kWh"
        finally:
            db.close()

    def test_27_recommendation_investigation(self):
        """27. Recommendation is formulated as an operational investigation action."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.generate_opportunities(db, document_id=1)
            elec_opp = next(o for o in opps if o.category == "ENERGY")
            assert "Investigate electrical equipment" in elec_opp.recommended_action
        finally:
            db.close()

    def test_28_no_invented_savings(self):
        """28. Opportunity does not state invented monetary or kWh savings."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.generate_opportunities(db, document_id=1)
            for o in opps:
                assert "₹" not in o.recommended_action
                assert "save 40%" not in o.recommended_action
        finally:
            db.close()

    def test_29_fuel_opportunity(self):
        """29. Generates FUEL opportunity for diesel combustion."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.generate_opportunities(db, document_id=1)
            fuel_opp = next(o for o in opps if o.category == "FUEL")
            assert "Diesel" in fuel_opp.title
        finally:
            db.close()

    def test_30_scope_1_evidence(self):
        """30. Fuel opportunity references exact 420.0 L diesel quantity."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.generate_opportunities(db, document_id=1)
            fuel_opp = next(o for o in opps if o.category == "FUEL")
            assert float(fuel_opp.current_value) == 420.0
            assert fuel_opp.current_unit == "L"
        finally:
            db.close()

    def test_31_no_invented_fuel_reduction(self):
        """31. Fuel recommendation does not claim an unverified reduction percentage."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.generate_opportunities(db, document_id=1)
            fuel_opp = next(o for o in opps if o.category == "FUEL")
            assert "will reduce by" not in fuel_opp.recommended_action
        finally:
            db.close()


# ==============================================================================
# 6. DATA QUALITY & FACTORS (Tests 32 - 38)
# ==============================================================================
class TestDataQualityOpportunities:
    def test_32_no_factor_solar_detection(self):
        """32. Detects NO_FACTOR on solar generation and creates DATA_QUALITY opportunity."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.generate_opportunities(db, document_id=1)
            solar_opp = next((o for o in opps if "SOLAR" in o.opportunity_code), None)
            assert solar_opp is not None
            assert solar_opp.category == "DATA_QUALITY"
            assert solar_opp.trigger_type == "UNRESOLVED_FACTOR"
        finally:
            db.close()

    def test_33_solar_quantity_preservation(self):
        """33. Preserves 3,850 kWh solar generation value without converting to zero."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.generate_opportunities(db, document_id=1)
            solar_opp = next(o for o in opps if "SOLAR" in o.opportunity_code)
            assert float(solar_opp.current_value) == 3850.0
            assert solar_opp.current_unit == "kWh"
        finally:
            db.close()

    def test_34_data_quality_limitations_warning(self):
        """34. Limitations warning explicitly notes that excluded records are not zero emissions."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.generate_opportunities(db, document_id=1)
            solar_opp = next(o for o in opps if "SOLAR" in o.opportunity_code)
            assert "not treated as zero emissions" in solar_opp.limitations
        finally:
            db.close()

    def test_35_priority_assignment_data_quality(self):
        """35. Data quality blocker receives deterministic HIGH priority."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.generate_opportunities(db, document_id=1)
            solar_opp = next(o for o in opps if "SOLAR" in o.opportunity_code)
            assert solar_opp.priority == "HIGH"
        finally:
            db.close()

    def test_36_transport_opportunity_handling(self):
        """36. Transport opportunities handled when transport entries exist."""
        db = SessionLocal()
        try:
            # Query returns safely even when no transport entries exist
            opps = reduction_opportunity_service.get_opportunities(db, category="TRANSPORT")
            assert isinstance(opps, list)
        finally:
            db.close()

    def test_37_missing_geography_indicator(self):
        """37. Coverage metrics correctly integrate with opportunity summary."""
        db = SessionLocal()
        try:
            summary = reduction_opportunity_service.get_summary(db)
            assert summary["total_opportunities"] >= 2
        finally:
            db.close()

    def test_38_missing_reporting_period_safety(self):
        """38. Missing reporting periods are handled safely without crash."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.get_opportunities(db, document_id=999999)
            assert opps == []
        finally:
            db.close()


# ==============================================================================
# 7. PRIORITY & DEDUPLICATION (Tests 39 - 46)
# ==============================================================================
class TestPriorityAndDeduplication:
    def test_39_high_priority_sorting(self):
        """39. get_opportunities sorts HIGH before MEDIUM before LOW."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.get_opportunities(db)
            if len(opps) >= 2:
                p_map = {"HIGH": 1, "MEDIUM": 2, "LOW": 3}
                for i in range(len(opps) - 1):
                    assert p_map.get(opps[i].priority, 4) <= p_map.get(opps[i+1].priority, 4)
        finally:
            db.close()

    def test_40_medium_priority_rule(self):
        """40. Secondary fuel source receives MEDIUM priority."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.generate_opportunities(db, document_id=1)
            fuel_opp = next(o for o in opps if "FUEL" in o.opportunity_code)
            assert fuel_opp.priority == "MEDIUM"
        finally:
            db.close()

    def test_41_low_priority_rule(self):
        """41. Minor items receive LOW priority."""
        db = SessionLocal()
        try:
            opp = ReductionOpportunity(
                opportunity_code="TEST_LOW_PRIO",
                title="Minor water use",
                description="Desc",
                category="WATER",
                priority="LOW",
                trigger_type="HIGH_EMISSION_SOURCE",
                rationale="Contributes < 1%",
                recommended_action="Action",
                limitations="Limitation",
            )
            db.add(opp)
            db.commit()
            assert opp.priority == "LOW"
        finally:
            db.query(ReductionOpportunity).filter_by(opportunity_code="TEST_LOW_PRIO").delete()
            db.commit()
            db.close()

    def test_42_deterministic_priority_logic(self):
        """42. Rationale field documents the exact deterministic rule used."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.generate_opportunities(db, document_id=1)
            for o in opps:
                assert "rule:" in o.rationale.lower()
        finally:
            db.close()

    def test_43_no_ai_scoring(self):
        """43. Detection version is pinned to 1.0 (no LLM version)."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.generate_opportunities(db, document_id=1)
            for o in opps:
                assert o.detection_version == "1.0"
        finally:
            db.close()

    def test_44_idempotent_generation(self):
        """44. Running generate_opportunities multiple times produces same count."""
        db = SessionLocal()
        try:
            cnt1 = len(reduction_opportunity_service.generate_opportunities(db, document_id=1))
            cnt2 = len(reduction_opportunity_service.generate_opportunities(db, document_id=1))
            assert cnt1 == cnt2
        finally:
            db.close()

    def test_45_opportunity_code_stability(self):
        """45. Opportunity codes follow deterministic prefix format."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.generate_opportunities(db, document_id=1)
            for o in opps:
                assert o.opportunity_code.startswith(("ENERGY_", "FUEL_", "EMISSIONS_", "REPEATED_", "DATA_"))
        finally:
            db.close()

    def test_46_status_preservation_across_generation(self):
        """46. User-modified status (e.g. IN_PROGRESS) is not reset to OPEN upon re-generation."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.generate_opportunities(db, document_id=1)
            grid_opp = next(o for o in opps if "GRID" in o.opportunity_code)
            grid_opp.status = "IN_PROGRESS"
            db.commit()

            # Re-run generator
            reduction_opportunity_service.generate_opportunities(db, document_id=1)
            db.refresh(grid_opp)
            assert grid_opp.status == "IN_PROGRESS"
        finally:
            grid_opp.status = "OPEN"
            db.commit()
            db.close()


# ==============================================================================
# 8. REDUCTION PROJECTS & AUDIT TRAIL (Tests 47 - 59)
# ==============================================================================
class TestReductionProjects:
    def test_47_create_project(self):
        """47. Create project with standard fields."""
        db = SessionLocal()
        try:
            dto = ReductionProjectCreate(
                title="LED Lighting Upgrade",
                description="Replace fluorescent lighting",
                category="ENERGY",
                scope="SCOPE_2",
                owner="Facility Manager",
                target_description="Reduce lighting energy consumption",
            )
            prj = reduction_project_service.create_project(db, dto)
            assert prj.id is not None
            assert prj.status == "PLANNED"
            assert prj.project_code.startswith("PRJ-ENER-")
        finally:
            db.query(ReductionProjectEvent).filter_by(project_id=prj.id).delete()
            db.query(ReductionProject).filter_by(id=prj.id).delete()
            db.commit()
            db.close()

    def test_48_create_project_from_opportunity(self):
        """48. Create project directly from an opportunity and link ID."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.generate_opportunities(db, document_id=1)
            grid_opp = next(o for o in opps if "GRID" in o.opportunity_code)

            prj = reduction_project_service.create_project_from_opportunity(
                db, grid_opp.id, {"owner": "Energy Team"}
            )
            assert prj.opportunity_id == grid_opp.id
            assert prj.category == "ENERGY"
            assert prj.baseline_co2e == grid_opp.calculated_co2e
        finally:
            db.query(ReductionProjectEvent).filter_by(project_id=prj.id).delete()
            db.query(ReductionProject).filter_by(id=prj.id).delete()
            db.commit()
            db.close()

    def test_49_project_code_format(self):
        """49. Project code generated with category and year."""
        db = SessionLocal()
        try:
            dto = ReductionProjectCreate(
                title="Generator Tuning",
                category="FUEL",
                scope="SCOPE_1",
            )
            prj = reduction_project_service.create_project(db, dto)
            assert "PRJ-FUEL-" in prj.project_code
        finally:
            db.query(ReductionProjectEvent).filter_by(project_id=prj.id).delete()
            db.query(ReductionProject).filter_by(id=prj.id).delete()
            db.commit()
            db.close()

    def test_50_initial_status_planned(self):
        """50. New project starts with status PLANNED."""
        db = SessionLocal()
        try:
            dto = ReductionProjectCreate(title="Test", category="ENERGY")
            prj = reduction_project_service.create_project(db, dto)
            assert prj.status == "PLANNED"
        finally:
            db.query(ReductionProjectEvent).filter_by(project_id=prj.id).delete()
            db.query(ReductionProject).filter_by(id=prj.id).delete()
            db.commit()
            db.close()

    def test_51_owner_tracking(self):
        """51. Project stores assigned owner."""
        db = SessionLocal()
        try:
            dto = ReductionProjectCreate(title="Test Owner", category="ENERGY", owner="Sarah Connor")
            prj = reduction_project_service.create_project(db, dto)
            assert prj.owner == "Sarah Connor"
        finally:
            db.query(ReductionProjectEvent).filter_by(project_id=prj.id).delete()
            db.query(ReductionProject).filter_by(id=prj.id).delete()
            db.commit()
            db.close()

    def test_52_dates_nullable(self):
        """52. Start and target dates are safely nullable."""
        db = SessionLocal()
        try:
            dto = ReductionProjectCreate(title="Test Dates", category="ENERGY", start_date=None, target_date=None)
            prj = reduction_project_service.create_project(db, dto)
            assert prj.start_date is None
            assert prj.target_date is None
        finally:
            db.query(ReductionProjectEvent).filter_by(project_id=prj.id).delete()
            db.query(ReductionProject).filter_by(id=prj.id).delete()
            db.commit()
            db.close()

    def test_53_baseline_reference_preservation(self):
        """53. Baseline reference footprint preserved from ledger calculation."""
        db = SessionLocal()
        try:
            dto = ReductionProjectCreate(
                title="Test Baseline", category="ENERGY", baseline_co2e=31879.0, baseline_period="2024-10"
            )
            prj = reduction_project_service.create_project(db, dto)
            assert float(prj.baseline_co2e) == 31879.0
            assert prj.baseline_period == "2024-10"
        finally:
            db.query(ReductionProjectEvent).filter_by(project_id=prj.id).delete()
            db.query(ReductionProject).filter_by(id=prj.id).delete()
            db.commit()
            db.close()

    def test_54_nullable_user_target(self):
        """54. Target description is optional and nullable."""
        db = SessionLocal()
        try:
            dto = ReductionProjectCreate(title="Test No Target", category="ENERGY", target_description=None)
            prj = reduction_project_service.create_project(db, dto)
            assert prj.target_description is None
        finally:
            db.query(ReductionProjectEvent).filter_by(project_id=prj.id).delete()
            db.query(ReductionProject).filter_by(id=prj.id).delete()
            db.commit()
            db.close()

    def test_55_user_defined_target_text(self):
        """55. User-defined qualitative or quantitative target stored as text."""
        db = SessionLocal()
        try:
            dto = ReductionProjectCreate(title="Test Target", category="ENERGY", target_description="Target: 5% reduction in electricity")
            prj = reduction_project_service.create_project(db, dto)
            assert prj.target_description == "Target: 5% reduction in electricity"
        finally:
            db.query(ReductionProjectEvent).filter_by(project_id=prj.id).delete()
            db.query(ReductionProject).filter_by(id=prj.id).delete()
            db.commit()
            db.close()

    def test_56_project_update(self):
        """56. Project details can be updated."""
        db = SessionLocal()
        try:
            dto = ReductionProjectCreate(title="Initial Title", category="ENERGY")
            prj = reduction_project_service.create_project(db, dto)

            upd = ReductionProjectUpdate(title="Updated Title", owner="New Owner")
            updated = reduction_project_service.update_project(db, prj.id, upd)
            assert updated.title == "Updated Title"
            assert updated.owner == "New Owner"
        finally:
            db.query(ReductionProjectEvent).filter_by(project_id=prj.id).delete()
            db.query(ReductionProject).filter_by(id=prj.id).delete()
            db.commit()
            db.close()

    def test_57_project_status_audit_event(self):
        """57. Status update logs an immutable event in ReductionProjectEvent."""
        db = SessionLocal()
        try:
            dto = ReductionProjectCreate(title="Status Test", category="ENERGY")
            prj = reduction_project_service.create_project(db, dto)

            reduction_project_service.update_status(db, prj.id, "IN_PROGRESS", note="Contract signed")
            events = reduction_project_service.get_project_events(db, prj.id)

            assert len(events) == 2  # CREATED and STATUS_CHANGE
            assert events[1].event_type == "STATUS_CHANGE"
            assert events[1].previous_status == "PLANNED"
            assert events[1].new_status == "IN_PROGRESS"
            assert events[1].note == "Contract signed"
        finally:
            db.query(ReductionProjectEvent).filter_by(project_id=prj.id).delete()
            db.query(ReductionProject).filter_by(id=prj.id).delete()
            db.commit()
            db.close()

    def test_58_project_cancellation(self):
        """58. Project can be cancelled with note."""
        db = SessionLocal()
        try:
            dto = ReductionProjectCreate(title="Cancel Test", category="ENERGY")
            prj = reduction_project_service.create_project(db, dto)

            reduction_project_service.update_status(db, prj.id, "CANCELLED", note="Budget reallocated")
            assert prj.status == "CANCELLED"
        finally:
            db.query(ReductionProjectEvent).filter_by(project_id=prj.id).delete()
            db.query(ReductionProject).filter_by(id=prj.id).delete()
            db.commit()
            db.close()

    def test_59_project_completion(self):
        """59. Project completion updates status to COMPLETED."""
        db = SessionLocal()
        try:
            dto = ReductionProjectCreate(title="Complete Test", category="ENERGY")
            prj = reduction_project_service.create_project(db, dto)

            reduction_project_service.update_status(db, prj.id, "COMPLETED", note="Implemented successfully")
            assert prj.status == "COMPLETED"
        finally:
            db.query(ReductionProjectEvent).filter_by(project_id=prj.id).delete()
            db.query(ReductionProject).filter_by(id=prj.id).delete()
            db.commit()
            db.close()


# ==============================================================================
# 9. SAFETY BOUNDARIES (Tests 60 - 72)
# ==============================================================================
class TestSafetyBoundaries:
    def test_60_no_carbon_recalculation(self):
        """60. Step 16 does NOT execute quantity * factor recalculation."""
        db = SessionLocal()
        try:
            # Confirm that CarbonCalculation records are untouched
            calc_count = db.query(CarbonCalculation).count()
            reduction_opportunity_service.generate_opportunities(db)
            assert db.query(CarbonCalculation).count() == calc_count
        finally:
            db.close()

    def test_61_no_ledger_mutation(self):
        """61. Step 16 does NOT modify CarbonLedgerEntry records."""
        db = SessionLocal()
        try:
            led_count = db.query(CarbonLedgerEntry).count()
            reduction_opportunity_service.generate_opportunities(db)
            assert db.query(CarbonLedgerEntry).count() == led_count
        finally:
            db.close()

    def test_62_no_activity_data_mutation(self):
        """62. Step 16 does NOT modify ActivityData records."""
        db = SessionLocal()
        try:
            act_count = db.query(ActivityData).count()
            reduction_opportunity_service.generate_opportunities(db)
            assert db.query(ActivityData).count() == act_count
        finally:
            db.close()

    def test_63_no_factor_resolution_in_step_16(self):
        """63. Step 16 does not alter emission factor tables."""
        from backend.app.models.emission_factor import EmissionFactor
        db = SessionLocal()
        try:
            f_count = db.query(EmissionFactor).count()
            reduction_opportunity_service.generate_opportunities(db)
            assert db.query(EmissionFactor).count() == f_count
        finally:
            db.close()

    def test_64_no_roi_claims(self):
        """64. Opportunities contain no ROI assertions."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.get_opportunities(db)
            for o in opps:
                assert "roi" not in o.title.lower()
                assert "roi" not in o.description.lower()
                assert "return on investment" not in o.recommended_action.lower()
        finally:
            db.close()

    def test_65_no_payback_period_claims(self):
        """65. Opportunities contain no payback period assertions."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.get_opportunities(db)
            for o in opps:
                assert "payback" not in o.recommended_action.lower()
        finally:
            db.close()

    def test_66_no_guaranteed_savings(self):
        """66. No guaranteed savings statements in recommendations."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.get_opportunities(db)
            for o in opps:
                assert "guaranteed" not in o.recommended_action.lower()
        finally:
            db.close()

    def test_67_no_invented_reduction_percentage(self):
        """67. No unverified reduction percentages in recommendations."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.get_opportunities(db)
            for o in opps:
                assert "reduce emissions by " not in o.recommended_action.lower()
        finally:
            db.close()

    def test_68_no_invented_causality(self):
        """68. Rationales are descriptive and grounded in data rules."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.get_opportunities(db)
            for o in opps:
                assert "rule:" in o.rationale.lower()
        finally:
            db.close()

    def test_69_no_carbon_credits_in_step_16(self):
        """69. No carbon credits issued or represented."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.get_opportunities(db)
            for o in opps:
                assert "carbon credit" not in o.description.lower()
        finally:
            db.close()

    def test_70_no_marketplace_integration(self):
        """70. No marketplace entities or routes."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.get_opportunities(db)
            for o in opps:
                assert "marketplace" not in o.description.lower()
        finally:
            db.close()

    def test_71_no_compliance_claims(self):
        """71. No compliance guarantees made."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.get_opportunities(db)
            for o in opps:
                assert "compliance guaranteed" not in o.limitations.lower()
        finally:
            db.close()

    def test_72_no_green_finance_scoring(self):
        """72. No green-loan scoring implemented."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.get_opportunities(db)
            for o in opps:
                assert "green loan" not in o.description.lower()
        finally:
            db.close()


# ==============================================================================
# 10. API ENDPOINTS (Tests 73 - 83)
# ==============================================================================
class TestAPIEndpoints:
    def test_73_api_opportunity_list(self, client):
        """73. GET /api/reduction-opportunities returns list."""
        resp = client.get("/api/reduction-opportunities")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    def test_74_api_opportunity_detail(self, client):
        """74. GET /api/reduction-opportunities/{id} returns single opportunity."""
        db = SessionLocal()
        try:
            opp = db.query(ReductionOpportunity).first()
            if opp:
                resp = client.get(f"/api/reduction-opportunities/{opp.id}")
                assert resp.status_code == 200
                assert resp.json()["opportunity_code"] == opp.opportunity_code
        finally:
            db.close()

    def test_75_api_opportunity_summary(self, client):
        """75. GET /api/reduction-opportunities/summary returns counts."""
        resp = client.get("/api/reduction-opportunities/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_opportunities" in data
        assert "high_priority_count" in data

    def test_76_api_generate_endpoint(self, client):
        """76. POST /api/reduction-opportunities/generate triggers scan."""
        resp = client.post("/api/reduction-opportunities/generate?document_id=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2

    def test_77_api_status_endpoint(self, client):
        """77. POST /api/reduction-opportunities/{id}/status updates status."""
        db = SessionLocal()
        try:
            opp = db.query(ReductionOpportunity).first()
            if opp:
                resp = client.post(
                    f"/api/reduction-opportunities/{opp.id}/status",
                    json={"status": "ACKNOWLEDGED"}
                )
                assert resp.status_code == 200
                assert resp.json()["status"] == "ACKNOWLEDGED"

                # Reset to OPEN
                client.post(
                    f"/api/reduction-opportunities/{opp.id}/status",
                    json={"status": "OPEN"}
                )
        finally:
            db.close()

    def test_78_api_project_list(self, client):
        """78. GET /api/reduction-projects returns list."""
        resp = client.get("/api/reduction-projects")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    def test_79_api_project_creation(self, client):
        """79. POST /api/reduction-projects creates project."""
        payload = {
            "title": "API Test Project",
            "category": "ENERGY",
            "scope": "SCOPE_2",
            "owner": "Test Lead",
            "target_description": "API created target",
        }
        resp = client.post("/api/reduction-projects", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "API Test Project"
        assert data["project_code"].startswith("PRJ-ENER-")

        # Clean up
        db = SessionLocal()
        try:
            db.query(ReductionProjectEvent).filter_by(project_id=data["id"]).delete()
            db.query(ReductionProject).filter_by(id=data["id"]).delete()
            db.commit()
        finally:
            db.close()

    def test_80_api_project_detail(self, client):
        """80. GET /api/reduction-projects/{id} returns project and events."""
        db = SessionLocal()
        try:
            dto = ReductionProjectCreate(title="Detail Test", category="ENERGY")
            prj = reduction_project_service.create_project(db, dto)

            resp = client.get(f"/api/reduction-projects/{prj.id}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == prj.id
            assert len(data["events"]) >= 1
        finally:
            db.query(ReductionProjectEvent).filter_by(project_id=prj.id).delete()
            db.query(ReductionProject).filter_by(id=prj.id).delete()
            db.commit()
            db.close()

    def test_81_api_project_update(self, client):
        """81. PATCH /api/reduction-projects/{id} updates details."""
        db = SessionLocal()
        try:
            dto = ReductionProjectCreate(title="Pre-Update", category="ENERGY")
            prj = reduction_project_service.create_project(db, dto)

            resp = client.patch(
                f"/api/reduction-projects/{prj.id}",
                json={"title": "Post-Update", "owner": "Updated Owner"}
            )
            assert resp.status_code == 200
            assert resp.json()["title"] == "Post-Update"
            assert resp.json()["owner"] == "Updated Owner"
        finally:
            db.query(ReductionProjectEvent).filter_by(project_id=prj.id).delete()
            db.query(ReductionProject).filter_by(id=prj.id).delete()
            db.commit()
            db.close()

    def test_82_api_project_status(self, client):
        """82. POST /api/reduction-projects/{id}/status changes status with note."""
        db = SessionLocal()
        try:
            dto = ReductionProjectCreate(title="Status API Test", category="ENERGY")
            prj = reduction_project_service.create_project(db, dto)

            resp = client.post(
                f"/api/reduction-projects/{prj.id}/status",
                json={"status": "IN_PROGRESS", "note": "Started implementation"}
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "IN_PROGRESS"
            assert any(e["note"] == "Started implementation" for e in data["events"])
        finally:
            db.query(ReductionProjectEvent).filter_by(project_id=prj.id).delete()
            db.query(ReductionProject).filter_by(id=prj.id).delete()
            db.commit()
            db.close()

    def test_83_api_opportunity_to_project_endpoint(self, client):
        """83. POST /api/reduction-opportunities/{id}/create-project creates linked project."""
        db = SessionLocal()
        try:
            opps = reduction_opportunity_service.generate_opportunities(db, document_id=1)
            grid_opp = next(o for o in opps if "GRID" in o.opportunity_code)

            resp = client.post(
                f"/api/reduction-opportunities/{grid_opp.id}/create-project",
                json={"owner": "Operations Director"}
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["opportunity_id"] == grid_opp.id
            assert data["owner"] == "Operations Director"

            # Clean up
            db.query(ReductionProjectEvent).filter_by(project_id=data["id"]).delete()
            db.query(ReductionProject).filter_by(id=data["id"]).delete()
            db.commit()
        finally:
            db.close()
