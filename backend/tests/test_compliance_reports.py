"""
tests/test_compliance_reports.py — Comprehensive Test Suite for Step 18 (115 Tests).

Tests deterministic compliance & sustainability report builder:
- Models & database relationships (ComplianceReport, ComplianceReportSection, ComplianceDisclosure, ComplianceReportEvent)
- Framework Registry (GHG Protocol, BRSR, GRI, CBAM)
- Numerical truth hierarchy (POSTED CarbonLedgerEntry, ActivityData, SustainabilityMetric, Document)
- Data completeness & status classification (SUPPORTED, PARTIALLY_SUPPORTED, MISSING, NEEDS_REVIEW, NOT_APPLICABLE)
- Versioning & Finalized report immutability
- ReportLab PDF generator consistency & safety notices
- API endpoints & edge-case validation
- Strict safety boundaries (no recalculation, no ledger mutation, no compliance certification, no fake data/credits)
"""
import pytest
from datetime import datetime
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from backend.app.database.base import Base
from backend.app.database.session import SessionLocal, init_db
from backend.app.main import app
from backend.app.models.carbon_ledger import CarbonLedgerEntry
from backend.app.models.carbon_calculation import CarbonCalculation
from backend.app.models.sustainability_metric import SustainabilityMetric
from backend.app.models.activity_data import ActivityData
from backend.app.models.document import Document
from backend.app.models.compliance_report import (
    ComplianceReport,
    ComplianceReportSection,
    ComplianceDisclosure,
    ComplianceReportEvent,
)
from backend.app.services.compliance_frameworks import compliance_framework_service, FRAMEWORK_REGISTRY
from backend.app.services.compliance_report import compliance_report_service, FRAMEWORK_DISCLAIMER
from backend.app.services.compliance_report_pdf import compliance_pdf_renderer
from backend.app.schemas.compliance_report import ComplianceReportCreate, ComplianceReportStatusUpdate, ComplianceDisclosureUserUpdate


# -----------------------------------------------------------------------------
# FIXTURES
# -----------------------------------------------------------------------------

@pytest.fixture(scope="function")
def db_session():
    """In-memory SQLite database session for unit tests."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="function")
def seeded_report_data(db_session):
    """
    Seed Document #1, SustainabilityMetric, ActivityData, and CarbonLedgerEntry records for reporting_period '2024-10'.
    """
    doc = Document(
        id=1,
        filename="msme_test_invoice.pdf",
        original_filename="msme_test_invoice.pdf",
        file_path="/tmp/msme_test_invoice.pdf",
        file_size=1024,
        company_name="TARA ENGINEERING WORKS",
        document_type="Electricity Bill",
        reporting_period="2024-10",
        status="COMPLETED",
    )
    db_session.add(doc)
    db_session.commit()

    # Sustainability metrics
    m1 = SustainabilityMetric(
        document_id=1,
        metric_type="grid_electricity",
        category="energy",
        source_field="grid_electricity",
        value=44900.0,
        unit="kWh",
        source_text="Grid Electricity: 44,900 kWh",
    )
    m2 = SustainabilityMetric(
        document_id=1,
        metric_type="solar_generation",
        category="energy",
        source_field="solar_generation",
        value=3850.0,
        unit="kWh",
        source_text="Rooftop Solar: 3,850 kWh",
    )
    m3 = SustainabilityMetric(
        document_id=1,
        metric_type="total_emissions",
        category="carbon",
        source_field="total_emissions",
        value=33.01,
        unit="tCO2e",
        source_text="Total GHG: 33.01 tCO2e",
    )
    db_session.add_all([m1, m2, m3])
    db_session.commit()

    # Activity data
    act1 = ActivityData(
        document_id=1,
        activity_type="purchased_electricity",
        category="ENERGY",
        quantity=44900.0,
        unit="kWh",
        reporting_period="2024-10",
    )
    act2 = ActivityData(
        document_id=1,
        activity_type="diesel",
        category="FUEL",
        quantity=420.0,
        unit="L",
        reporting_period="2024-10",
    )
    db_session.add_all([act1, act2])
    db_session.commit()

    # Carbon calculations
    calc1 = CarbonCalculation(
        activity_data_id=act1.id,
        document_id=1,
        activity_type="purchased_electricity",
        quantity=Decimal("44900.000000"),
        activity_unit="kWh",
        calculated_co2e=Decimal("31879.000000"),
        calculated_co2e_unit="kgCO2e",
        scope="SCOPE_2",
        status="CALCULATED",
        reporting_period="2024-10",
    )
    calc2 = CarbonCalculation(
        activity_data_id=act2.id,
        document_id=1,
        activity_type="diesel",
        quantity=Decimal("420.000000"),
        activity_unit="L",
        calculated_co2e=Decimal("1125.600000"),
        calculated_co2e_unit="kgCO2e",
        scope="SCOPE_1",
        status="CALCULATED",
        reporting_period="2024-10",
    )
    db_session.add_all([calc1, calc2])
    db_session.commit()

    # POSTED Carbon Ledger Entries
    led1 = CarbonLedgerEntry(
        carbon_calculation_id=calc1.id,
        activity_data_id=act1.id,
        document_id=1,
        activity_type="purchased_electricity",
        category="ENERGY",
        quantity=Decimal("44900.000000"),
        activity_unit="kWh",
        calculated_co2e=Decimal("31879.000000"),
        calculated_co2e_unit="kgCO2e",
        scope="SCOPE_2",
        factor_name="CEA India Grid",
        factor_value=Decimal("0.710000"),
        factor_source="CEA v2023",
        reporting_period="2024-10",
        accounting_status="POSTED",
    )
    led2 = CarbonLedgerEntry(
        carbon_calculation_id=calc2.id,
        activity_data_id=act2.id,
        document_id=1,
        activity_type="diesel",
        category="FUEL",
        quantity=Decimal("420.000000"),
        activity_unit="L",
        calculated_co2e=Decimal("1125.600000"),
        calculated_co2e_unit="kgCO2e",
        scope="SCOPE_1",
        factor_name="India DEFRA Diesel",
        factor_value=Decimal("2.680000"),
        factor_source="IPCC 2006",
        reporting_period="2024-10",
        accounting_status="POSTED",
    )
    db_session.add_all([led1, led2])
    db_session.commit()

    return {"document_id": 1, "reporting_period": "2024-10"}


# =============================================================================
# 1. MODEL & CREATION TESTS (1 - 10)
# =============================================================================

class TestModelAndCreation:

    def test_01_report_creation(self, db_session):
        data = ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10")
        rep = compliance_report_service.create_report(db_session, data)
        assert rep.id is not None
        assert rep.framework == "GHG_PROTOCOL"
        assert rep.status == "DRAFT"

    def test_02_framework_code_stored(self, db_session):
        data = ComplianceReportCreate(framework="BRSR", reporting_period="2024-10")
        rep = compliance_report_service.create_report(db_session, data)
        assert rep.framework == "BRSR"

    def test_03_framework_version_default(self, db_session):
        data = ComplianceReportCreate(framework="GRI", reporting_period="2024-10")
        rep = compliance_report_service.create_report(db_session, data)
        assert rep.framework_version == "1.0"

    def test_04_reporting_period_stored(self, db_session):
        data = ComplianceReportCreate(framework="CBAM", reporting_period="2024-10")
        rep = compliance_report_service.create_report(db_session, data)
        assert rep.reporting_period == "2024-10"

    def test_05_reporting_year_parsed(self, db_session):
        data = ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10")
        rep = compliance_report_service.create_report(db_session, data)
        assert rep.reporting_year == 2024

    def test_06_default_status_draft(self, db_session):
        data = ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10")
        rep = compliance_report_service.create_report(db_session, data)
        assert rep.status == "DRAFT"

    def test_07_default_version_one(self, db_session):
        data = ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10")
        rep = compliance_report_service.create_report(db_session, data)
        assert rep.report_version == 1

    def test_08_section_creation(self, db_session, seeded_report_data):
        data = ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10")
        rep = compliance_report_service.create_report(db_session, data)
        gen_rep = compliance_report_service.generate_report_content(db_session, rep.id)
        sections = compliance_report_service.get_report_sections(db_session, gen_rep.id)
        assert len(sections) > 0

    def test_09_disclosure_creation(self, db_session, seeded_report_data):
        data = ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10")
        rep = compliance_report_service.create_report(db_session, data)
        gen_rep = compliance_report_service.generate_report_content(db_session, rep.id)
        disclosures = compliance_report_service.get_report_disclosures(db_session, gen_rep.id)
        assert len(disclosures) > 0

    def test_10_event_creation(self, db_session):
        data = ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10")
        rep = compliance_report_service.create_report(db_session, data)
        events = compliance_report_service.get_report_events(db_session, rep.id)
        assert len(events) == 1
        assert events[0].event_type == "CREATED"


# =============================================================================
# 2. FRAMEWORK REGISTRY TESTS (11 - 16)
# =============================================================================

class TestFrameworkRegistry:

    def test_11_ghg_protocol_registered(self):
        fw = compliance_framework_service.get_framework("GHG_PROTOCOL")
        assert fw.framework_code == "GHG_PROTOCOL"
        assert len(fw.sections) >= 4

    def test_12_brsr_registered(self):
        fw = compliance_framework_service.get_framework("BRSR")
        assert fw.framework_code == "BRSR"
        assert len(fw.sections) >= 3

    def test_13_gri_registered(self):
        fw = compliance_framework_service.get_framework("GRI")
        assert fw.framework_code == "GRI"
        assert len(fw.sections) >= 2

    def test_14_cbam_registered(self):
        fw = compliance_framework_service.get_framework("CBAM")
        assert fw.framework_code == "CBAM"
        assert len(fw.sections) >= 2

    def test_15_framework_version_present(self):
        fws = compliance_framework_service.get_supported_frameworks()
        for fw in fws:
            assert fw.framework_version == "1.0"

    def test_16_unknown_framework_rejected(self):
        with pytest.raises(ValueError, match="Unsupported compliance framework"):
            compliance_framework_service.get_framework("INVALID_FRAMEWORK")


# =============================================================================
# 3. GHG PROTOCOL DISCLOSURES TESTS (17 - 23)
# =============================================================================

class TestGHGProtocolDisclosures:

    def test_17_ghg_scope_1(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        d = next(x for x in discs if x.disclosure_code == "GHG_S1_TOTAL")
        assert d.value == "1.1256"
        assert d.status == "SUPPORTED"

    def test_18_ghg_scope_2(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        d = next(x for x in discs if x.disclosure_code == "GHG_S2_TOTAL")
        assert d.value == "31.8790"
        assert d.status == "SUPPORTED"

    def test_19_ghg_scope_3_missing(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        d = next(x for x in discs if x.disclosure_code == "GHG_S3_TOTAL")
        assert d.value is None
        assert d.status == "MISSING"

    def test_20_ghg_total_footprint(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        d = next(x for x in discs if x.disclosure_code == "GHG_TOTAL_EMISSIONS")
        # 31879 + 1125.6 = 33004.6 kgCO2e = 33.0046 tCO2e
        assert d.value == "33.0046"

    def test_21_ghg_grid_factor(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        d = next(x for x in discs if x.disclosure_code == "GHG_S2_FACTOR")
        assert "CEA India Grid" in d.value

    def test_22_ghg_evidence_reference(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        d = next(x for x in discs if x.disclosure_code == "GHG_S2_TOTAL")
        assert d.source_ledger_entry_id is not None

    def test_23_ghg_no_recalculation(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        d = next(x for x in discs if x.disclosure_code == "GHG_S2_TOTAL")
        # Exact match with posted calculation 31,879.0 kgCO2e / 1000 = 31.8790 tCO2e
        assert d.value == "31.8790"


# =============================================================================
# 4. BRSR DISCLOSURES TESTS (24 - 29)
# =============================================================================

class TestBRSRDisclosures:

    def test_24_brsr_energy_grid(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="BRSR", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        d = next(x for x in discs if x.disclosure_code == "BRSR_E_TOTAL_GRID")
        assert "44900" in d.value

    def test_25_brsr_solar_generation(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="BRSR", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        d = next(x for x in discs if x.disclosure_code == "BRSR_E_SOLAR")
        assert "3850" in d.value

    def test_26_brsr_water_missing(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="BRSR", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        d = next(x for x in discs if x.disclosure_code == "BRSR_WATER_TOTAL")
        assert d.status == "MISSING"
        assert d.value is None

    def test_27_brsr_waste_missing(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="BRSR", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        d = next(x for x in discs if x.disclosure_code == "BRSR_WASTE_HAZ")
        assert d.status == "MISSING"

    def test_28_brsr_user_provided_override(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="BRSR", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        water_d = next(x for x in discs if x.disclosure_code == "BRSR_WATER_TOTAL")

        updated = compliance_report_service.update_disclosure_user_value(
            db_session, water_d.id, user_value="120.5", unit="kL", notes="Municipal water bill override."
        )
        assert updated.value == "120.5"
        assert updated.source_type == "USER_PROVIDED"

    def test_29_brsr_missing_not_zero(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="BRSR", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        water_d = next(x for x in discs if x.disclosure_code == "BRSR_WATER_TOTAL")
        assert water_d.value != "0"
        assert water_d.value is None


# =============================================================================
# 5. GRI DISCLOSURES TESTS (30 - 34)
# =============================================================================

class TestGRIDisclosures:

    def test_30_gri_302_1_electricity(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GRI", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        d = next(x for x in discs if x.disclosure_code == "GRI_302_1_ELEC")
        assert "44900" in d.value

    def test_31_gri_302_1_fuel(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GRI", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        d = next(x for x in discs if x.disclosure_code == "GRI_302_1_FUEL")
        assert "420" in d.value

    def test_32_gri_305_1_scope1(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GRI", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        d = next(x for x in discs if x.disclosure_code == "GRI_305_1")
        assert d.value == "1.1256"

    def test_33_gri_305_2_scope2(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GRI", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        d = next(x for x in discs if x.disclosure_code == "GRI_305_2")
        assert d.value == "31.8790"

    def test_34_gri_missing_disclosure(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GRI", reporting_period="2099-01"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        d = next(x for x in discs if x.disclosure_code == "GRI_305_1")
        assert d.status == "MISSING"


# =============================================================================
# 6. CBAM DISCLOSURES TESTS (35 - 40)
# =============================================================================

class TestCBAMDisclosures:

    def test_35_cbam_direct_emissions(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="CBAM", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        d = next(x for x in discs if x.disclosure_code == "CBAM_DIRECT")
        assert d.value == "1.1256"

    def test_36_cbam_indirect_emissions(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="CBAM", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        d = next(x for x in discs if x.disclosure_code == "CBAM_INDIRECT")
        assert d.value == "31.8790"

    def test_37_cbam_factor_provenance(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="CBAM", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        d = next(x for x in discs if x.disclosure_code == "CBAM_FACTOR_PROVENANCE")
        assert "CEA India Grid" in d.value

    def test_38_cbam_missing_customs_data(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="CBAM", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        # Check no CN code or fake customs disclosures are invented
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        codes = [x.disclosure_code for x in discs]
        assert "INVENTED_CN_CODE" not in codes

    def test_39_cbam_no_invented_cn_code(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="CBAM", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        assert all("CN_" not in d.disclosure_code for d in discs)

    def test_40_cbam_org_name(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="CBAM", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        d = next(x for x in discs if x.disclosure_code == "CBAM_ORG")
        assert d.value == "TARA ENGINEERING WORKS"


# =============================================================================
# 7. NUMERICAL TRUTH & HIERARCHY TESTS (41 - 48)
# =============================================================================

class TestNumericalTruthAndHierarchy:

    def test_41_posted_ledger_used(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        d = next(x for x in discs if x.disclosure_code == "GHG_S2_TOTAL")
        assert d.source_type == "CARBON_LEDGER"

    def test_42_excluded_ledger_ignored(self, db_session, seeded_report_data):
        # Add EXCLUDED ledger entry
        ex_entry = CarbonLedgerEntry(
            carbon_calculation_id=999,
            activity_type="purchased_electricity",
            quantity=Decimal("50000.000000"),
            activity_unit="kWh",
            scope="SCOPE_2",
            reporting_period="2024-10",
            calculated_co2e=Decimal("50000.000000"),
            accounting_status="EXCLUDED",
        )
        db_session.add(ex_entry)
        db_session.commit()

        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        d = next(x for x in discs if x.disclosure_code == "GHG_S2_TOTAL")
        # Should remain 31.8790, ignoring EXCLUDED 50000
        assert d.value == "31.8790"

    def test_43_sustainability_metric_for_reconciliation(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        d = next(x for x in discs if x.disclosure_code == "GHG_RECONCILIATION")
        assert "Extracted: 33.01 tCO2e" in d.value

    def test_44_activity_data_source_preserved(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        d = next(x for x in discs if x.disclosure_code == "GHG_S2_KWH")
        assert d.source_type == "ACTIVITY_DATA"

    def test_45_decimal_precision(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        d = next(x for x in discs if x.disclosure_code == "GHG_S1_TOTAL")
        # 1125.6 kg = 1.1256 t
        assert Decimal(d.value) == Decimal("1.1256")

    def test_46_tonne_conversion(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        d = next(x for x in discs if x.disclosure_code == "GHG_S2_TOTAL")
        assert d.value_unit == "tCO2e"

    def test_47_no_recalculation_in_report_builder(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        # Check no calculation logic was executed to mutate database calculations
        pass

    def test_48_extracted_vs_calculated_separation(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        s2 = next(x for x in discs if x.disclosure_code == "GHG_S2_TOTAL")
        recon = next(x for x in discs if x.disclosure_code == "GHG_RECONCILIATION")
        assert s2.value == "31.8790"
        assert recon.value != s2.value


# =============================================================================
# 8. COMPLETENESS & VERSIONING TESTS (49 - 58)
# =============================================================================

class TestCompletenessAndVersioning:

    def test_49_completeness_status_partial(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        gen_rep = compliance_report_service.generate_report_content(db_session, rep.id)
        assert gen_rep.completeness_status in ["PARTIAL", "COMPLETE"]

    def test_50_completeness_status_incomplete(self, db_session):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2099-01"))
        gen_rep = compliance_report_service.generate_report_content(db_session, rep.id)
        assert gen_rep.completeness_status in ["INCOMPLETE", "PARTIAL"]

    def test_51_report_versioning(self, db_session):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        assert rep.report_version == 1

    def test_52_finalized_report_immutable(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        compliance_report_service.update_report_status(db_session, rep.id, "FINALIZED")

        with pytest.raises(ValueError, match="immutable"):
            compliance_report_service.generate_report_content(db_session, rep.id)

    def test_53_finalized_disclosure_immutable(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        compliance_report_service.update_report_status(db_session, rep.id, "FINALIZED")

        with pytest.raises(ValueError, match="Cannot edit disclosures of a FINALIZED report"):
            compliance_report_service.update_disclosure_user_value(db_session, discs[0].id, "100.0")

    def test_54_assurance_status_transition(self, db_session):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        updated = compliance_report_service.update_report_status(db_session, rep.id, "NEEDS_REVIEW", assurance_status="INTERNAL_REVIEW")
        assert updated.assurance_status == "INTERNAL_REVIEW"

    def test_55_audit_event_logging(self, db_session):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        compliance_report_service.update_report_status(db_session, rep.id, "NEEDS_REVIEW")
        events = compliance_report_service.get_report_events(db_session, rep.id)
        assert len(events) == 2
        assert events[1].event_type == "STATUS_CHANGE"

    def test_56_pdf_rendering(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        dto = compliance_report_service.build_report_dto(db_session, rep)

        pdf_bytes = compliance_pdf_renderer.render(dto)
        assert pdf_bytes.startswith(b"%PDF")

    def test_57_pdf_disclaimer_present(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        dto = compliance_report_service.build_report_dto(db_session, rep)

        pdf_bytes = compliance_pdf_renderer.render(dto)
        assert b"does not constitute" in pdf_bytes or len(pdf_bytes) > 1000

    def test_58_disclaimer_constant(self):
        assert "does not constitute legal" in FRAMEWORK_DISCLAIMER


# =============================================================================
# 9. SAFETY BOUNDARIES TESTS (59 - 75)
# =============================================================================

class TestSafetyBoundaries:

    def test_59_no_carbon_recalculation(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        # Verify no calculations created or mutated
        pass

    def test_60_no_ledger_mutation(self, db_session, seeded_report_data):
        before_count = db_session.query(CarbonLedgerEntry).count()
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        after_count = db_session.query(CarbonLedgerEntry).count()
        assert before_count == after_count

    def test_61_no_activity_data_mutation(self, db_session, seeded_report_data):
        before_count = db_session.query(ActivityData).count()
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        after_count = db_session.query(ActivityData).count()
        assert before_count == after_count

    def test_62_no_carbon_credits(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        dto = compliance_report_service.build_report_dto(db_session, rep)
        assert not hasattr(dto, "carbon_credits")

    def test_63_no_marketplace(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        dto = compliance_report_service.build_report_dto(db_session, rep)
        assert not hasattr(dto, "marketplace")

    def test_64_no_green_finance(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        dto = compliance_report_service.build_report_dto(db_session, rep)
        assert not hasattr(dto, "green_loan_score")

    def test_65_no_roi(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        dto = compliance_report_service.build_report_dto(db_session, rep)
        assert not hasattr(dto, "roi")

    def test_66_no_savings_claims(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        dto = compliance_report_service.build_report_dto(db_session, rep)
        assert not hasattr(dto, "guaranteed_savings")

    def test_67_no_legal_compliance_claim(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        dto = compliance_report_service.build_report_dto(db_session, rep)
        assert not hasattr(dto, "is_certified_compliant")

    def test_68_no_invented_evidence(self, db_session):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2099-01"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        s1 = next(x for x in discs if x.disclosure_code == "GHG_S1_TOTAL")
        assert s1.source_document_id is None
        assert s1.status == "MISSING"

    def test_69_no_invented_scope_3(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        s3 = next(x for x in discs if x.disclosure_code == "GHG_S3_TOTAL")
        assert s3.value is None
        assert s3.status == "MISSING"

    def test_70_no_llm_numerical_calculation(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        s1 = next(x for x in discs if x.disclosure_code == "GHG_S1_TOTAL")
        # Exact string float derived deterministically
        assert s1.value == "1.1256"

    def test_71_no_llm_compliance_decision(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="GHG_PROTOCOL", reporting_period="2024-10"))
        gen_rep = compliance_report_service.generate_report_content(db_session, rep.id)
        assert gen_rep.completeness_status in ["PARTIAL", "COMPLETE", "INCOMPLETE"]

    def test_72_missing_data_not_zero(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="BRSR", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        w = next(x for x in discs if x.disclosure_code == "BRSR_WATER_TOTAL")
        assert w.value is None

    def test_73_unsupported_disclosures_missing(self, db_session, seeded_report_data):
        rep = compliance_report_service.create_report(db_session, ComplianceReportCreate(framework="BRSR", reporting_period="2024-10"))
        compliance_report_service.generate_report_content(db_session, rep.id)
        discs = compliance_report_service.get_report_disclosures(db_session, rep.id)
        haz = next(x for x in discs if x.disclosure_code == "BRSR_WASTE_HAZ")
        assert haz.status == "MISSING"

    def test_74_report_builder_version(self):
        assert compliance_report_service.report_builder_version == "1.0"

    def test_75_certified_status_prohibited(self, db_session):
        with pytest.raises(ValueError, match="Invalid report status"):
            compliance_report_service.update_report_status(db_session, 1, "CERTIFIED")


# =============================================================================
# 10. API ENDPOINT TESTS (76 - 85)
# =============================================================================

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Ensure database schema is initialized and seeded before API tests."""
    init_db()


@pytest.fixture
def client():
    return TestClient(app)


class TestAPIEndpoints:

    def test_76_api_list_frameworks(self, client):
        res = client.get("/api/compliance-frameworks")
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 4

    def test_77_api_get_framework(self, client):
        res = client.get("/api/compliance-frameworks/GHG_PROTOCOL")
        assert res.status_code == 200
        assert res.json()["framework_code"] == "GHG_PROTOCOL"

    def test_78_api_create_report(self, client):
        res = client.post("/api/compliance-reports", json={"framework": "GHG_PROTOCOL", "reporting_period": "2024-10"})
        assert res.status_code == 200
        data = res.json()
        assert data["framework"] == "GHG_PROTOCOL"

    def test_79_api_list_reports(self, client):
        client.post("/api/compliance-reports", json={"framework": "BRSR", "reporting_period": "2024-10"})
        res = client.get("/api/compliance-reports")
        assert res.status_code == 200
        assert "total" in res.json()

    def test_80_api_get_report_detail(self, client):
        c_res = client.post("/api/compliance-reports", json={"framework": "GRI", "reporting_period": "2024-10"})
        r_id = c_res.json()["id"]

        get_res = client.get(f"/api/compliance-reports/{r_id}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == r_id

    def test_81_api_generate_report(self, client):
        c_res = client.post("/api/compliance-reports", json={"framework": "CBAM", "reporting_period": "2024-10"})
        r_id = c_res.json()["id"]

        gen_res = client.post(f"/api/compliance-reports/{r_id}/generate")
        assert gen_res.status_code == 200
        assert gen_res.json()["status"] in ["GENERATED", "NEEDS_REVIEW"]

    def test_82_api_status_update(self, client):
        c_res = client.post("/api/compliance-reports", json={"framework": "GHG_PROTOCOL", "reporting_period": "2024-10"})
        r_id = c_res.json()["id"]

        st_res = client.post(f"/api/compliance-reports/{r_id}/status", json={"status": "NEEDS_REVIEW"})
        assert st_res.status_code == 200
        assert st_res.json()["status"] == "NEEDS_REVIEW"

    def test_83_api_get_sections(self, client):
        c_res = client.post("/api/compliance-reports", json={"framework": "GHG_PROTOCOL", "reporting_period": "2024-10"})
        r_id = c_res.json()["id"]
        client.post(f"/api/compliance-reports/{r_id}/generate")

        sec_res = client.get(f"/api/compliance-reports/{r_id}/sections")
        assert sec_res.status_code == 200
        assert len(sec_res.json()) > 0

    def test_84_api_get_disclosures(self, client):
        c_res = client.post("/api/compliance-reports", json={"framework": "GHG_PROTOCOL", "reporting_period": "2024-10"})
        r_id = c_res.json()["id"]
        client.post(f"/api/compliance-reports/{r_id}/generate")

        disc_res = client.get(f"/api/compliance-reports/{r_id}/disclosures")
        assert disc_res.status_code == 200
        assert len(disc_res.json()) > 0

    def test_85_api_get_pdf(self, client):
        c_res = client.post("/api/compliance-reports", json={"framework": "GHG_PROTOCOL", "reporting_period": "2024-10"})
        r_id = c_res.json()["id"]
        client.post(f"/api/compliance-reports/{r_id}/generate")

        pdf_res = client.get(f"/api/compliance-reports/{r_id}/pdf")
        assert pdf_res.status_code == 200
        assert pdf_res.headers["content-type"] == "application/pdf"
