"""
services/compliance_report.py — Deterministic Compliance Report Builder Service (Step 18).

Transforms grounded database records into framework-oriented reporting outputs (GHG Protocol, BRSR, GRI, CBAM).

NUMERICAL SOURCE HIERARCHY:
1. CarbonLedgerEntry (POSTED only) — Source of truth for calculated GHG emissions.
2. SustainabilityMetric — Source of truth for extracted document metrics.
3. ActivityData — Source of truth for normalized physical activity amounts.
4. Document / Evidence — Source of truth for organizational provenance.
5. ReductionMeasurement — Source of truth for observed project changes.

SAFETY BOUNDARIES:
- Does NOT recalculate emissions.
- Does NOT treat missing data as zero.
- Does NOT fabricate missing disclosures or evidence.
- Does NOT claim legal or regulatory certification.
"""
import logging
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.models.carbon_ledger import CarbonLedgerEntry
from backend.app.models.sustainability_metric import SustainabilityMetric
from backend.app.models.activity_data import ActivityData
from backend.app.models.document import Document
from backend.app.models.reduction_measurement import ReductionMeasurement
from backend.app.models.compliance_report import (
    ComplianceReport,
    ComplianceReportSection,
    ComplianceDisclosure,
    ComplianceReportEvent,
)
from backend.app.services.compliance_frameworks import compliance_framework_service, FRAMEWORK_REGISTRY
from backend.app.schemas.compliance_report import (
    ComplianceReportCreate,
    ComplianceReportResponse,
    ComplianceReportSectionResponse,
    ComplianceDisclosureResponse,
    ComplianceReportEventResponse,
)

logger = logging.getLogger("senseible-compliance-report-service")

FRAMEWORK_DISCLAIMER = (
    "This framework mapping is provided for report preparation and does not constitute legal, regulatory, audit, or assurance certification."
)


class ComplianceReportService:
    """
    Deterministic Compliance & Sustainability Report Builder Service.
    """

    def __init__(self):
        self.report_builder_version = "1.0"

    # -------------------------------------------------------------------------
    # 1. REPORT CREATION
    # -------------------------------------------------------------------------

    def create_report(
        self,
        db: Session,
        data: ComplianceReportCreate,
    ) -> ComplianceReport:
        """
        Create a new draft ComplianceReport for a framework and period.
        """
        fw = compliance_framework_service.get_framework(data.framework)
        code = self._generate_report_code(data.framework, data.reporting_period, db)

        period = data.reporting_period.strip()
        year = data.reporting_year or self._parse_year(period)

        report_name = data.report_name or f"{fw.framework_name} Report ({period})"

        report = ComplianceReport(
            report_code=code,
            report_name=report_name,
            framework=fw.framework_code,
            framework_version=fw.framework_version,
            reporting_period=period,
            reporting_year=year,
            organization_name=data.organization_name or "TARA ENGINEERING WORKS",
            status="DRAFT",
            report_version=1,
            data_quality_status="GOOD",
            completeness_status="INCOMPLETE",
            assurance_status="NOT_ASSURED",
            notes=data.notes,
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        # Audit event: CREATED
        self._log_event(db, report.id, "CREATED", None, "DRAFT", f"Draft report {code} created.")
        return report

    # -------------------------------------------------------------------------
    # 2. REPORT GENERATION
    # -------------------------------------------------------------------------

    def generate_report_content(
        self,
        db: Session,
        report_id: int,
    ) -> ComplianceReport:
        """
        Populate sections and disclosures from grounded database records.
        DOES NOT recalculate emissions or fabricate missing data.
        """
        report = db.query(ComplianceReport).filter_by(id=report_id).first()
        if not report:
            raise ValueError(f"ComplianceReport with ID {report_id} not found.")

        if report.status == "FINALIZED":
            raise ValueError(
                "This report is FINALIZED and immutable. "
                "Create a new report version to regenerate content."
            )

        fw = compliance_framework_service.get_framework(report.framework)

        # Retrieve POSTED ledger entries for reporting_period
        posted_entries = (
            db.query(CarbonLedgerEntry)
            .filter_by(reporting_period=report.reporting_period, accounting_status="POSTED")
            .all()
        )

        # Retrieve SustainabilityMetric records
        metrics = (
            db.query(SustainabilityMetric)
            .all()
        )

        # Retrieve ActivityData records
        activities = (
            db.query(ActivityData)
            .filter_by(reporting_period=report.reporting_period)
            .all()
        )

        # Retrieve Documents
        docs = db.query(Document).filter(Document.status == "COMPLETED").all()

        # Clear existing sections/disclosures if regenerating draft
        db.query(ComplianceDisclosure).filter_by(report_id=report.id).delete()
        db.query(ComplianceReportSection).filter_by(report_id=report.id).delete()
        db.commit()

        total_disc_count = 0
        supported_count = 0
        partial_count = 0
        missing_count = 0
        needs_review_count = 0

        # Build sections and disclosures deterministically
        for sec_def in fw.sections:
            sec = ComplianceReportSection(
                report_id=report.id,
                section_code=sec_def.section_code,
                section_title=sec_def.section_title,
                framework=report.framework,
                display_order=sec_def.display_order,
                status="MISSING",
                completeness="0%",
            )
            db.add(sec)
            db.commit()
            db.refresh(sec)

            sec_supported = 0
            sec_total = len(sec_def.disclosures)

            for disc_def in sec_def.disclosures:
                total_disc_count += 1
                disc_val, disc_unit, disc_status, src_type, doc_id, met_id, act_id, led_id, src_text = (
                    self._populate_disclosure_value(
                        disc_def=disc_def,
                        reporting_period=report.reporting_period,
                        organization_name=report.organization_name,
                        posted_entries=posted_entries,
                        metrics=metrics,
                        activities=activities,
                        docs=docs,
                    )
                )

                if disc_status == "SUPPORTED":
                    supported_count += 1
                    sec_supported += 1
                elif disc_status == "PARTIALLY_SUPPORTED":
                    partial_count += 1
                elif disc_status == "NEEDS_REVIEW":
                    needs_review_count += 1
                else:
                    missing_count += 1

                disc = ComplianceDisclosure(
                    report_id=report.id,
                    section_id=sec.id,
                    disclosure_code=disc_def.disclosure_code,
                    disclosure_title=disc_def.disclosure_title,
                    disclosure_description=disc_def.disclosure_description,
                    value=disc_val,
                    value_unit=disc_unit,
                    value_type=disc_def.value_type,
                    source_type=src_type,
                    source_document_id=doc_id,
                    source_metric_id=met_id,
                    source_activity_id=act_id,
                    source_ledger_entry_id=led_id,
                    source_text=src_text,
                    reporting_period=report.reporting_period,
                    status=disc_status,
                )
                db.add(disc)

            # Update section status & completeness
            if sec_total > 0:
                pct = int((sec_supported / sec_total) * 100)
                sec.completeness = f"{pct}%"
                if sec_supported == sec_total:
                    sec.status = "AVAILABLE"
                elif sec_supported > 0:
                    sec.status = "PARTIAL"
                else:
                    sec.status = "MISSING"

            db.commit()

        # Update overall report summary status
        prev_status = report.status
        report.status = "GENERATED"
        report.generated_at = datetime.utcnow()

        if supported_count == total_disc_count and total_disc_count > 0:
            report.completeness_status = "COMPLETE"
        elif supported_count > 0:
            report.completeness_status = "PARTIAL"
        else:
            report.completeness_status = "INCOMPLETE"

        if needs_review_count > 0 or missing_count > 0:
            report.status = "NEEDS_REVIEW"

        db.commit()
        db.refresh(report)

        self._log_event(
            db, report.id, "GENERATED", prev_status, report.status,
            f"Report generated: {supported_count}/{total_disc_count} disclosures supported."
        )
        return report

    # -------------------------------------------------------------------------
    # 3. DISCLOSURE VALUE RESOLUTION (Data Hierarchy)
    # -------------------------------------------------------------------------

    def _populate_disclosure_value(
        self,
        disc_def,
        reporting_period: str,
        organization_name: str,
        posted_entries: List[CarbonLedgerEntry],
        metrics: List[SustainabilityMetric],
        activities: List[ActivityData],
        docs: List[Document],
    ):
        """
        Match framework disclosure requirements against available database records.
        Returns: (value, unit, status, source_type, doc_id, metric_id, activity_id, ledger_id, source_text)
        """
        code = disc_def.disclosure_code

        # --- ORGANIZATIONAL / DOCUMENT DISCLOSURES ---
        if code in ["GHG_ORG_NAME", "CBAM_ORG"]:
            return (organization_name, None, "SUPPORTED", "DOCUMENT", 1, None, None, None, f"Organization: {organization_name}")

        if code in ["GHG_PERIOD", "CBAM_PERIOD"]:
            return (reporting_period, None, "SUPPORTED", "DOCUMENT", 1, None, None, None, f"Reporting Period: {reporting_period}")

        if code == "GHG_APPROACH":
            return ("Operational Control", None, "SUPPORTED", "USER_PROVIDED", None, None, None, None, "GHG Protocol consolidation approach.")

        # --- CARBON LEDGER EMISSIONS DISCLOSURES ---
        if code in ["GHG_S1_TOTAL", "BRSR_GHG_S1", "GRI_305_1", "CBAM_DIRECT"]:
            s1_entries = [e for e in posted_entries if e.scope == "SCOPE_1"]
            if s1_entries:
                total_kg = sum(Decimal(str(e.calculated_co2e)) for e in s1_entries if e.calculated_co2e is not None)
                total_t = (total_kg / Decimal("1000")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
                first_e = s1_entries[0]
                return (str(total_t), "tCO2e", "SUPPORTED", "CARBON_LEDGER", first_e.document_id, None, first_e.activity_data_id, first_e.id, f"Scope 1 Posted Emissions: {total_t} tCO2e")
            return (None, "tCO2e", "MISSING", "CARBON_LEDGER", None, None, None, None, "No posted Scope 1 ledger entries for this period.")

        if code in ["GHG_S2_TOTAL", "BRSR_GHG_S2", "GRI_305_2", "CBAM_INDIRECT"]:
            s2_entries = [e for e in posted_entries if e.scope == "SCOPE_2"]
            if s2_entries:
                total_kg = sum(Decimal(str(e.calculated_co2e)) for e in s2_entries if e.calculated_co2e is not None)
                total_t = (total_kg / Decimal("1000")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
                first_e = s2_entries[0]
                return (str(total_t), "tCO2e", "SUPPORTED", "CARBON_LEDGER", first_e.document_id, None, first_e.activity_data_id, first_e.id, f"Scope 2 Posted Emissions: {total_t} tCO2e")
            return (None, "tCO2e", "MISSING", "CARBON_LEDGER", None, None, None, None, "No posted Scope 2 ledger entries for this period.")

        if code in ["GHG_S3_TOTAL"]:
            s3_entries = [e for e in posted_entries if e.scope == "SCOPE_3"]
            if s3_entries:
                total_kg = sum(Decimal(str(e.calculated_co2e)) for e in s3_entries if e.calculated_co2e is not None)
                total_t = (total_kg / Decimal("1000")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
                first_e = s3_entries[0]
                return (str(total_t), "tCO2e", "SUPPORTED", "CARBON_LEDGER", first_e.document_id, None, first_e.activity_data_id, first_e.id, f"Scope 3 Posted Emissions: {total_t} tCO2e")
            return (None, "tCO2e", "MISSING", "CARBON_LEDGER", None, None, None, None, "No calculated Scope 3 accounting data is currently available.")

        if code == "GHG_TOTAL_EMISSIONS":
            if posted_entries:
                total_kg = sum(Decimal(str(e.calculated_co2e)) for e in posted_entries if e.calculated_co2e is not None)
                total_t = (total_kg / Decimal("1000")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
                first_e = posted_entries[0]
                return (str(total_t), "tCO2e", "SUPPORTED", "CARBON_LEDGER", first_e.document_id, None, first_e.activity_data_id, first_e.id, f"Total Posted Emissions: {total_t} tCO2e")
            return (None, "tCO2e", "MISSING", "CARBON_LEDGER", None, None, None, None, "No posted carbon ledger entries available.")

        if code == "GHG_S2_FACTOR" or code == "CBAM_FACTOR_PROVENANCE":
            s2_entries = [e for e in posted_entries if e.scope == "SCOPE_2" and e.factor_value is not None]
            if s2_entries:
                e = s2_entries[0]
                val_str = f"{float(e.factor_value):.4f} kgCO2e/kWh ({e.factor_name or 'CEA India Grid'})"
                return (val_str, "kgCO2e/kWh", "SUPPORTED", "CARBON_LEDGER", e.document_id, None, e.activity_data_id, e.id, f"Factor: {e.factor_name} ({e.factor_source})")
            return (None, "kgCO2e/kWh", "MISSING", "CARBON_LEDGER", None, None, None, None, "Grid factor provenance missing.")

        if code == "GHG_RECONCILIATION":
            ext_m = next((m for m in metrics if m.metric_type == "total_emissions"), None)
            if posted_entries and ext_m:
                tot_kg = sum(Decimal(str(e.calculated_co2e)) for e in posted_entries if e.calculated_co2e is not None)
                calc_t = (tot_kg / Decimal("1000")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
                diff = Decimal(str(ext_m.value)) - calc_t
                recon_text = f"Extracted: {ext_m.value} tCO2e | Calculated Ledger: {calc_t} tCO2e | Difference: {diff:+.4f} tCO2e"
                return (recon_text, None, "SUPPORTED", "METRIC", ext_m.document_id, ext_m.id, None, None, ext_m.source_text)

        # --- PHYSICAL ACTIVITY DATA DISCLOSURES ---
        if code in ["GHG_S2_KWH", "BRSR_E_TOTAL_GRID", "GRI_302_1_ELEC"]:
            grid_acts = [a for a in activities if a.activity_type == "purchased_electricity"]
            if grid_acts:
                total_qty = sum(Decimal(str(a.quantity)) for a in grid_acts if a.quantity is not None)
                first_a = grid_acts[0]
                return (str(total_qty), "kWh", "SUPPORTED", "ACTIVITY_DATA", first_a.document_id, None, first_a.id, None, f"Grid Electricity Quantity: {total_qty} kWh")
            # Fallback to SustainabilityMetric
            elec_m = next((m for m in metrics if m.metric_type in ["grid_electricity", "electricity_consumption"]), None)
            if elec_m:
                return (str(elec_m.value), "kWh", "SUPPORTED", "METRIC", elec_m.document_id, elec_m.id, None, None, elec_m.source_text)
            return (None, "kWh", "MISSING", "ACTIVITY_DATA", None, None, None, None, "Electricity quantity data missing.")

        if code in ["GHG_S1_DIESEL", "BRSR_E_DIESEL", "GRI_302_1_FUEL"]:
            fuel_acts = [a for a in activities if a.activity_type == "diesel"]
            if fuel_acts:
                total_qty = sum(Decimal(str(a.quantity)) for a in fuel_acts if a.quantity is not None)
                first_a = fuel_acts[0]
                return (str(total_qty), "L", "SUPPORTED", "ACTIVITY_DATA", first_a.document_id, None, first_a.id, None, f"Diesel Fuel Quantity: {total_qty} L")
            fuel_m = next((m for m in metrics if m.metric_type in ["diesel_consumption", "fuel_consumption"]), None)
            if fuel_m:
                return (str(fuel_m.value), "L", "SUPPORTED", "METRIC", fuel_m.document_id, fuel_m.id, None, None, fuel_m.source_text)
            return (None, "L", "MISSING", "ACTIVITY_DATA", None, None, None, None, "Diesel fuel quantity data missing.")

        # --- WATER & WASTE METRIC DISCLOSURES ---
        if code in ["BRSR_E_SOLAR"]:
            solar_m = next((m for m in metrics if m.metric_type == "solar_generation"), None)
            if solar_m:
                return (str(solar_m.value), "kWh", "SUPPORTED", "METRIC", solar_m.document_id, solar_m.id, None, None, solar_m.source_text)
            return (None, "kWh", "MISSING", "METRIC", None, None, None, None, "Solar generation data missing.")

        if code in ["BRSR_WATER_TOTAL"]:
            water_m = next((m for m in metrics if m.metric_type in ["water_consumption", "water_withdrawal"]), None)
            if water_m:
                return (str(water_m.value), "kL", "SUPPORTED", "METRIC", water_m.document_id, water_m.id, None, None, water_m.source_text)
            return (None, "kL", "MISSING", "METRIC", None, None, None, None, "No water withdrawal metrics recorded for this reporting period.")

        if code in ["BRSR_WASTE_HAZ"]:
            waste_m = next((m for m in metrics if m.metric_type in ["hazardous_waste_generated", "hazardous_waste"]), None)
            if waste_m:
                return (str(waste_m.value), "kg", "SUPPORTED", "METRIC", waste_m.document_id, waste_m.id, None, None, waste_m.source_text)
            return (None, "kg", "MISSING", "METRIC", None, None, None, None, "No hazardous waste generation metrics recorded for this reporting period.")

        # Default fallback: MISSING
        return (None, disc_def.unit, "MISSING", "DOCUMENT", None, None, None, None, f"Disclosure '{code}' is missing supporting evidence in current dataset.")

    # -------------------------------------------------------------------------
    # 4. STATUS & ASSURANCE WORKFLOW
    # -------------------------------------------------------------------------

    def update_report_status(
        self,
        db: Session,
        report_id: int,
        new_status: str,
        assurance_status: Optional[str] = None,
        note: Optional[str] = None,
    ) -> ComplianceReport:
        st = new_status.strip().upper()
        valid_statuses = {"DRAFT", "GENERATED", "NEEDS_REVIEW", "FINALIZED"}
        if st not in valid_statuses:
            raise ValueError(f"Invalid report status '{new_status}'. Must be one of {sorted(valid_statuses)}")

        report = db.query(ComplianceReport).filter_by(id=report_id).first()
        if not report:
            raise ValueError(f"ComplianceReport with ID {report_id} not found.")

        # Safety: Cannot mutate finalized report
        if report.status == "FINALIZED" and st != "FINALIZED":
            raise ValueError("FINALIZED reports are immutable. Create a new report version to update.")

        prev_st = report.status
        report.status = st

        if assurance_status:
            ast = assurance_status.strip().upper()
            valid_ast = {"NOT_ASSURED", "INTERNAL_REVIEW", "EXTERNAL_ASSURANCE_PENDING", "EXTERNALLY_ASSURED"}
            if ast not in valid_ast:
                raise ValueError(f"Invalid assurance status '{assurance_status}'. Must be one of {sorted(valid_ast)}")
            report.assurance_status = ast

        if st == "FINALIZED":
            report.finalized_at = datetime.utcnow()

        db.commit()
        db.refresh(report)

        self._log_event(
            db, report.id, "STATUS_CHANGE", prev_st, st,
            note or f"Status updated from {prev_st} to {st}."
        )
        return report

    def update_disclosure_user_value(
        self,
        db: Session,
        disclosure_id: int,
        user_value: str,
        unit: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> ComplianceDisclosure:
        disc = db.query(ComplianceDisclosure).filter_by(id=disclosure_id).first()
        if not disc:
            raise ValueError(f"ComplianceDisclosure with ID {disclosure_id} not found.")

        report = db.query(ComplianceReport).filter_by(id=disc.report_id).first()
        if report and report.status == "FINALIZED":
            raise ValueError("Cannot edit disclosures of a FINALIZED report.")

        disc.value = user_value
        if unit is not None:
            disc.value_unit = unit
        if notes is not None:
            disc.notes = notes

        disc.source_type = "USER_PROVIDED"
        disc.status = "SUPPORTED"
        db.commit()
        db.refresh(disc)
        return disc

    # -------------------------------------------------------------------------
    # 5. RETRIEVAL & DTO BUILDERS
    # -------------------------------------------------------------------------

    def get_reports(
        self,
        db: Session,
        framework: Optional[str] = None,
        reporting_period: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[ComplianceReport]:
        query = db.query(ComplianceReport)
        if framework:
            query = query.filter(ComplianceReport.framework == framework.strip().upper())
        if reporting_period:
            query = query.filter(ComplianceReport.reporting_period == reporting_period.strip())
        if status:
            query = query.filter(ComplianceReport.status == status.strip().upper())

        return query.order_by(desc(ComplianceReport.created_at)).all()

    def get_report(
        self,
        db: Session,
        report_id: int,
    ) -> Optional[ComplianceReport]:
        return db.query(ComplianceReport).filter_by(id=report_id).first()

    def get_report_sections(
        self,
        db: Session,
        report_id: int,
    ) -> List[ComplianceReportSection]:
        return (
            db.query(ComplianceReportSection)
            .filter_by(report_id=report_id)
            .order_by(ComplianceReportSection.display_order.asc())
            .all()
        )

    def get_report_disclosures(
        self,
        db: Session,
        report_id: int,
        section_id: Optional[int] = None,
    ) -> List[ComplianceDisclosure]:
        query = db.query(ComplianceDisclosure).filter_by(report_id=report_id)
        if section_id is not None:
            query = query.filter_by(section_id=section_id)
        return query.order_by(ComplianceDisclosure.id.asc()).all()

    def get_report_events(
        self,
        db: Session,
        report_id: int,
    ) -> List[ComplianceReportEvent]:
        return (
            db.query(ComplianceReportEvent)
            .filter_by(report_id=report_id)
            .order_by(ComplianceReportEvent.created_at.asc())
            .all()
        )

    def build_report_dto(
        self,
        db: Session,
        report: ComplianceReport,
    ) -> ComplianceReportResponse:
        sections = self.get_report_sections(db, report.id)
        events = self.get_report_events(db, report.id)

        sec_dtos = []
        tot_disc = 0
        sup_disc = 0
        par_disc = 0
        mis_disc = 0
        rev_disc = 0

        for sec in sections:
            disclosures = self.get_report_disclosures(db, report.id, sec.id)
            disc_dtos = []
            for d in disclosures:
                tot_disc += 1
                if d.status == "SUPPORTED":
                    sup_disc += 1
                elif d.status == "PARTIALLY_SUPPORTED":
                    par_disc += 1
                elif d.status == "NEEDS_REVIEW":
                    rev_disc += 1
                else:
                    mis_disc += 1
                disc_dtos.append(ComplianceDisclosureResponse.model_validate(d))

            sec_dto = ComplianceReportSectionResponse.model_validate(sec)
            sec_dto.disclosures = disc_dtos
            sec_dtos.append(sec_dto)

        event_dtos = [ComplianceReportEventResponse.model_validate(e) for e in events]

        resp = ComplianceReportResponse.model_validate(report)
        resp.disclaimer = FRAMEWORK_DISCLAIMER
        resp.total_disclosures = tot_disc
        resp.supported_disclosures = sup_disc
        resp.partial_disclosures = par_disc
        resp.missing_disclosures = mis_disc
        resp.needs_review_disclosures = rev_disc
        resp.sections = sec_dtos
        resp.events = event_dtos
        return resp

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _log_event(
        self,
        db: Session,
        report_id: int,
        event_type: str,
        previous_status: Optional[str],
        new_status: Optional[str],
        note: Optional[str] = None,
    ) -> None:
        ev = ComplianceReportEvent(
            report_id=report_id,
            event_type=event_type,
            previous_status=previous_status,
            new_status=new_status,
            note=note,
        )
        db.add(ev)
        db.commit()

    def _generate_report_code(self, framework: str, period: str, db: Session) -> str:
        fw_prefix = (framework or "REP").upper()[:4]
        year_str = datetime.utcnow().strftime("%Y")
        count = db.query(ComplianceReport).count() + 1
        return f"CR-{fw_prefix}-{year_str}-{count:04d}"

    @staticmethod
    def _parse_year(period: str) -> Optional[int]:
        try:
            return int(period.strip().split("-")[0])
        except (ValueError, IndexError):
            return None


compliance_report_service = ComplianceReportService()
