"""
services/carbon_ledger.py — Deterministic Carbon Accounting Ledger Service (Step 14).

Consumes calculated emissions from CarbonCalculation without recalculating CO2e.
Maintains an immutable, versioned, and auditable accounting layer.
Performs deterministic aggregation, double-counting protection enforcement, and reconciliation.
ZERO floating-point math in financial/accounting calculations; strict Python Decimal arithmetic with ROUND_HALF_UP.
"""
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.models.carbon_ledger import CarbonLedgerEntry
from backend.app.models.carbon_calculation import CarbonCalculation
from backend.app.models.activity_data import ActivityData
from backend.app.models.document import Document
from backend.app.models.sustainability_metric import SustainabilityMetric
from backend.app.schemas.carbon_ledger import (
    CarbonLedgerEntryResponse,
    CarbonLedgerListResponse,
    DocumentLedgerSummary,
    LedgerReconciliationResponse,
    ReconciliationItem,
    LedgerAggregationResponse,
)

logger = logging.getLogger("senseible-carbon-ledger-service")


class CarbonLedgerService:
    """
    Deterministic Carbon Accounting Ledger Service.
    Builds the accounting layer on top of CarbonCalculation results.
    """

    def __init__(self):
        self.ledger_version = "1.0"

    def post_calculation(
        self,
        db: Session,
        carbon_calculation_id: int
    ) -> CarbonLedgerEntry:
        """
        Post a single CarbonCalculation into the accounting ledger.
        Enforces posting rules, double-counting protection, version tracking, and idempotency.
        """
        calc = db.query(CarbonCalculation).filter(
            CarbonCalculation.id == carbon_calculation_id
        ).first()

        if not calc:
            raise ValueError(f"CarbonCalculation ID {carbon_calculation_id} not found.")

        # Load associated ActivityData if present
        activity = None
        if calc.activity_data_id:
            activity = db.query(ActivityData).filter(
                ActivityData.id == calc.activity_data_id
            ).first()

        # Category from ActivityData or fallback
        category = activity.category if activity and activity.category else "OTHER"

        # Determine accounting status & reason
        if calc.status != "CALCULATED":
            if calc.status in ["INVALID_ACTIVITY", "ERROR"]:
                accounting_status = "INVALID"
            else:
                accounting_status = "EXCLUDED"
            accounting_reason = f"Excluded: Calculation status is '{calc.status}'. {calc.calculation_reason or ''}".strip()
        else:
            # Valid CALCULATED record: Check double-counting rules across activity groups
            if calc.activity_group_id:
                # Query peer calculations in the same group and document
                peer_calcs = db.query(CarbonCalculation).filter(
                    CarbonCalculation.document_id == calc.document_id,
                    CarbonCalculation.activity_group_id == calc.activity_group_id
                ).all()

                has_total = any(c.activity_role == "TOTAL" for c in peer_calcs)
                has_components = any(c.activity_role == "COMPONENT" for c in peer_calcs)

                if has_total and has_components:
                    if calc.activity_role == "TOTAL":
                        accounting_status = "EXCLUDED"
                        accounting_reason = "Excluded from accounting aggregation to prevent double-counting with constituent component activities."
                    else:
                        accounting_status = "POSTED"
                        accounting_reason = "Constituent component calculation accepted and posted into accounting ledger."
                elif has_total and not has_components:
                    accounting_status = "POSTED"
                    accounting_reason = "Total activity calculation accepted and posted into accounting ledger."
                elif has_components and not has_total:
                    accounting_status = "POSTED"
                    accounting_reason = "Component activity calculation accepted and posted into accounting ledger."
                else:
                    if calc.activity_role != "TOTAL":
                        accounting_status = "POSTED"
                        accounting_reason = "Calculation accepted and posted into accounting ledger."
                    else:
                        accounting_status = "EXCLUDED"
                        accounting_reason = "Excluded: Ambiguous activity group role."
            else:
                accounting_status = "POSTED"
                accounting_reason = "Calculation accepted and posted into accounting ledger."

        # Idempotency & Versioning: Check if an entry exists for this calculation and ledger_version
        existing_entries = db.query(CarbonLedgerEntry).filter(
            CarbonLedgerEntry.carbon_calculation_id == calc.id,
            CarbonLedgerEntry.ledger_version == self.ledger_version
        ).order_by(desc(CarbonLedgerEntry.id)).all()

        active_entry = next((e for e in existing_entries if e.accounting_status != "SUPERSEDED"), None)

        if active_entry:
            # If calculation_version is identical, update fields idempotently
            if active_entry.calculation_version == calc.calculation_version:
                active_entry.activity_data_id = calc.activity_data_id
                active_entry.document_id = calc.document_id
                active_entry.metric_id = calc.metric_id
                active_entry.activity_type = calc.activity_type
                active_entry.category = category
                active_entry.activity_role = calc.activity_role
                active_entry.activity_group_id = calc.activity_group_id
                active_entry.quantity = calc.quantity
                active_entry.activity_unit = calc.activity_unit
                active_entry.calculated_co2e = calc.calculated_co2e if accounting_status == "POSTED" else None
                active_entry.calculated_co2e_unit = calc.calculated_co2e_unit or "kgCO2e"
                active_entry.emission_factor_id = calc.emission_factor_id
                active_entry.factor_code = calc.factor_code
                active_entry.factor_name = calc.factor_name
                active_entry.factor_value = calc.factor_value
                active_entry.factor_unit = calc.factor_unit
                active_entry.factor_version = calc.factor_version
                active_entry.factor_source = calc.factor_source
                active_entry.geography = calc.geography
                active_entry.reporting_period = calc.reporting_period
                active_entry.reporting_year = calc.reporting_year
                active_entry.scope = calc.scope
                active_entry.accounting_status = accounting_status
                active_entry.accounting_reason = accounting_reason
                active_entry.source_field = calc.source_field
                active_entry.source_text = calc.source_text
                active_entry.page = calc.page
                db.commit()
                db.refresh(active_entry)
                return active_entry
            else:
                # Calculation version changed: Mark old entry as SUPERSEDED and create new
                active_entry.accounting_status = "SUPERSEDED"
                active_entry.accounting_reason = f"Superseded by calculation version {calc.calculation_version}."
                db.commit()

        # Create new ledger entry
        new_entry = CarbonLedgerEntry(
            carbon_calculation_id=calc.id,
            activity_data_id=calc.activity_data_id,
            document_id=calc.document_id,
            metric_id=calc.metric_id,
            activity_type=calc.activity_type,
            category=category,
            activity_role=calc.activity_role,
            activity_group_id=calc.activity_group_id,
            quantity=calc.quantity,
            activity_unit=calc.activity_unit,
            calculated_co2e=calc.calculated_co2e if accounting_status == "POSTED" else None,
            calculated_co2e_unit=calc.calculated_co2e_unit or "kgCO2e",
            calculation_version=calc.calculation_version or "1.0",
            emission_factor_id=calc.emission_factor_id,
            factor_code=calc.factor_code,
            factor_name=calc.factor_name,
            factor_value=calc.factor_value,
            factor_unit=calc.factor_unit,
            factor_version=calc.factor_version,
            factor_source=calc.factor_source,
            geography=calc.geography,
            reporting_period=calc.reporting_period,
            reporting_year=calc.reporting_year,
            scope=calc.scope,
            accounting_status=accounting_status,
            accounting_reason=accounting_reason,
            ledger_version=self.ledger_version,
            source_field=calc.source_field,
            source_text=calc.source_text,
            page=calc.page,
        )
        db.add(new_entry)
        db.commit()
        db.refresh(new_entry)
        return new_entry

    def post_document(
        self,
        db: Session,
        document_id: int
    ) -> DocumentLedgerSummary:
        """
        Post all eligible calculations for a document into the accounting ledger.
        Consumes existing calculations without recalculating CO2e.
        """
        calculations = db.query(CarbonCalculation).filter(
            CarbonCalculation.document_id == document_id
        ).order_by(CarbonCalculation.id.asc()).all()

        for calc in calculations:
            self.post_calculation(db, calc.id)

        return self.get_document_ledger(db, document_id)

    def get_document_ledger(
        self,
        db: Session,
        document_id: int
    ) -> DocumentLedgerSummary:
        """
        Retrieve the accounting ledger summary for a document.
        Aggregates only POSTED entries using exact Python Decimal arithmetic.
        """
        entries = db.query(CarbonLedgerEntry).filter(
            CarbonLedgerEntry.document_id == document_id,
            CarbonLedgerEntry.ledger_version == self.ledger_version
        ).order_by(CarbonLedgerEntry.id.asc()).all()

        # Latest non-superseded entries for aggregation
        # If there are superseded entries, we only sum the active ones
        active_entries = [e for e in entries if e.accounting_status != "SUPERSEDED"]
        posted_entries = [e for e in active_entries if e.accounting_status == "POSTED"]

        posted_count = len(posted_entries)
        excluded_count = sum(1 for e in active_entries if e.accounting_status == "EXCLUDED")
        superseded_count = sum(1 for e in entries if e.accounting_status == "SUPERSEDED")

        # Sum emissions deterministically using Decimal
        scope_1_sum = Decimal("0.0")
        scope_2_sum = Decimal("0.0")
        scope_3_sum = Decimal("0.0")
        total_sum = Decimal("0.0")
        category_totals_dec: Dict[str, Decimal] = {}

        periods = set()
        years = set()

        for e in posted_entries:
            if e.calculated_co2e is not None:
                val = Decimal(str(e.calculated_co2e))
                total_sum += val
                if e.scope == "SCOPE_1":
                    scope_1_sum += val
                elif e.scope == "SCOPE_2":
                    scope_2_sum += val
                elif e.scope == "SCOPE_3":
                    scope_3_sum += val

                cat = (e.category or "OTHER").upper()
                category_totals_dec[cat] = category_totals_dec.get(cat, Decimal("0.0")) + val

            if e.reporting_period:
                periods.add(e.reporting_period)
            if e.reporting_year is not None:
                years.add(e.reporting_year)

        category_totals = {k: float(v) for k, v in category_totals_dec.items()}

        return DocumentLedgerSummary(
            document_id=document_id,
            total_ledger_records=len(entries),
            posted_records=posted_count,
            excluded_records=excluded_count,
            superseded_records=superseded_count,
            total_posted_co2e=float(total_sum) if posted_count > 0 else None,
            total_posted_co2e_unit="kgCO2e",
            scope_1_posted_co2e=float(scope_1_sum) if scope_1_sum > 0 else None,
            scope_2_posted_co2e=float(scope_2_sum) if scope_2_sum > 0 else None,
            scope_3_posted_co2e=float(scope_3_sum) if scope_3_sum > 0 else None,
            category_totals=category_totals,
            reporting_periods=sorted(list(periods)),
            reporting_years=sorted(list(years)),
            entries=[CarbonLedgerEntryResponse.model_validate(e) for e in entries],
        )

    def get_document_reconciliation(
        self,
        db: Session,
        document_id: int
    ) -> LedgerReconciliationResponse:
        """
        Reconcile extracted emissions against calculated & posted ledger emissions.
        Uses exact Decimal arithmetic (1 tCO2e = 1000 kgCO2e).
        Does NOT label differences as errors or fabricate causal claims.
        """
        # 1. Extracted emissions from SustainabilityMetric
        extracted_scope_1 = None
        extracted_scope_2 = None
        extracted_total = None

        metrics = db.query(SustainabilityMetric).filter(
            SustainabilityMetric.document_id == document_id
        ).all()

        for m in metrics:
            if m.metric_type == "scope_1_emissions" and m.value is not None:
                extracted_scope_1 = Decimal(str(m.value))
            elif m.metric_type == "scope_2_emissions" and m.value is not None:
                extracted_scope_2 = Decimal(str(m.value))
            elif m.metric_type == "total_ghg_emissions" and m.value is not None:
                extracted_total = Decimal(str(m.value))

        # Fallback to Document.total_emissions_tco2e if total_ghg_emissions metric was not found
        if extracted_total is None:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc and doc.total_emissions_tco2e is not None:
                extracted_total = Decimal(str(doc.total_emissions_tco2e))

        # 2. Calculated & Posted emissions from CarbonLedgerEntry
        ledger_summary = self.get_document_ledger(db, document_id)

        posted_s1_kg = Decimal(str(ledger_summary.scope_1_posted_co2e)) if ledger_summary.scope_1_posted_co2e is not None else None
        posted_s2_kg = Decimal(str(ledger_summary.scope_2_posted_co2e)) if ledger_summary.scope_2_posted_co2e is not None else None
        posted_total_kg = Decimal(str(ledger_summary.total_posted_co2e)) if ledger_summary.total_posted_co2e is not None else None

        # Build Scope 1 item
        item_s1 = self._build_reconciliation_item(
            "Scope 1",
            extracted_val=extracted_scope_1,
            calculated_kg=posted_s1_kg
        )

        # Build Scope 2 item
        item_s2 = self._build_reconciliation_item(
            "Scope 2",
            extracted_val=extracted_scope_2,
            calculated_kg=posted_s2_kg
        )

        # Build Total item
        item_total = self._build_reconciliation_item(
            "Total GHG Footprint",
            extracted_val=extracted_total,
            calculated_kg=posted_total_kg
        )

        all_items = [item_s1, item_s2, item_total]

        # Determine overall status
        statuses = [it.status for it in all_items if it.status != "NO_DATA"]
        if not statuses:
            overall_status = "NO_DATA"
        elif any(s == "DIFFERENCE" for s in statuses):
            overall_status = "DIFFERENCE"
        elif all(s == "MATCH" for s in statuses):
            overall_status = "MATCH"
        elif all(s == "EXTRACTED_ONLY" for s in statuses):
            overall_status = "EXTRACTED_ONLY"
        elif all(s == "CALCULATED_ONLY" for s in statuses):
            overall_status = "CALCULATED_ONLY"
        else:
            overall_status = "DIFFERENCE"

        return LedgerReconciliationResponse(
            document_id=document_id,
            overall_status=overall_status,
            scope_1=item_s1,
            scope_2=item_s2,
            total=item_total,
            items=all_items,
        )

    def _build_reconciliation_item(
        self,
        label: str,
        extracted_val: Optional[Decimal],
        calculated_kg: Optional[Decimal]
    ) -> ReconciliationItem:
        """
        Helper to construct a deterministic ReconciliationItem comparing tCO2e to kgCO2e.
        1 tCO2e = 1000 kgCO2e (exact Decimal conversion).
        """
        if extracted_val is None and calculated_kg is None:
            return ReconciliationItem(
                scope_or_metric=label,
                extracted_value=None,
                extracted_unit="tCO2e",
                calculated_value_kg=None,
                calculated_value_t=None,
                difference_t=None,
                difference_kg=None,
                status="NO_DATA",
                notes="Neither extracted nor calculated emission values are available."
            )

        if extracted_val is not None and calculated_kg is None:
            return ReconciliationItem(
                scope_or_metric=label,
                extracted_value=float(extracted_val),
                extracted_unit="tCO2e",
                calculated_value_kg=None,
                calculated_value_t=None,
                difference_t=None,
                difference_kg=None,
                status="EXTRACTED_ONLY",
                notes="Extracted from document evidence; no calculated ledger entry posted."
            )

        if extracted_val is None and calculated_kg is not None:
            calc_t = (calculated_kg / Decimal("1000")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            return ReconciliationItem(
                scope_or_metric=label,
                extracted_value=None,
                extracted_unit="tCO2e",
                calculated_value_kg=float(calculated_kg),
                calculated_value_t=float(calc_t),
                difference_t=None,
                difference_kg=None,
                status="CALCULATED_ONLY",
                notes="Calculated and posted from activity data; not present in extracted document text."
            )

        # Both exist: compute differences using Decimal
        calc_t = (calculated_kg / Decimal("1000")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        extracted_kg = extracted_val * Decimal("1000")

        diff_t = (calc_t - extracted_val).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        diff_kg = (calculated_kg - extracted_kg).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        # Match threshold: within 0.0001 tCO2e (0.1 kgCO2e)
        if abs(diff_t) <= Decimal("0.0001"):
            status = "MATCH"
            notes = "Calculated emissions match extracted document value within tolerance."
        else:
            status = "DIFFERENCE"
            notes = f"Variance of {diff_t} tCO2e ({diff_kg} kgCO2e) between calculated and extracted values."

        return ReconciliationItem(
            scope_or_metric=label,
            extracted_value=float(extracted_val),
            extracted_unit="tCO2e",
            calculated_value_kg=float(calculated_kg),
            calculated_value_t=float(calc_t),
            difference_t=float(diff_t),
            difference_kg=float(diff_kg),
            status=status,
            notes=notes,
        )

    def get_ledger_summary(
        self,
        db: Session,
        reporting_year: Optional[int] = None,
        reporting_period: Optional[str] = None,
        scope: Optional[str] = None,
        category: Optional[str] = None,
        activity_type: Optional[str] = None
    ) -> LedgerAggregationResponse:
        """
        Global / filtered accounting aggregation across the ledger.
        """
        query = db.query(CarbonLedgerEntry).filter(
            CarbonLedgerEntry.ledger_version == self.ledger_version
        )

        if reporting_year is not None:
            query = query.filter(CarbonLedgerEntry.reporting_year == reporting_year)
        if reporting_period:
            query = query.filter(CarbonLedgerEntry.reporting_period == reporting_period)
        if scope:
            query = query.filter(CarbonLedgerEntry.scope == scope.strip().upper())
        if category:
            query = query.filter(CarbonLedgerEntry.category == category.strip().upper())
        if activity_type:
            query = query.filter(CarbonLedgerEntry.activity_type == activity_type.strip().lower())

        entries = query.all()

        active_entries = [e for e in entries if e.accounting_status != "SUPERSEDED"]
        posted_entries = [e for e in active_entries if e.accounting_status == "POSTED"]

        total_sum = Decimal("0.0")
        scope_1_sum = Decimal("0.0")
        scope_2_sum = Decimal("0.0")
        scope_3_sum = Decimal("0.0")

        by_scope: Dict[str, Decimal] = {}
        by_cat: Dict[str, Decimal] = {}
        by_act: Dict[str, Decimal] = {}
        by_period: Dict[str, Decimal] = {}
        by_year: Dict[str, Decimal] = {}

        for e in posted_entries:
            if e.calculated_co2e is not None:
                val = Decimal(str(e.calculated_co2e))
                total_sum += val

                sc = e.scope or "UNSPECIFIED"
                by_scope[sc] = by_scope.get(sc, Decimal("0.0")) + val
                if e.scope == "SCOPE_1":
                    scope_1_sum += val
                elif e.scope == "SCOPE_2":
                    scope_2_sum += val
                elif e.scope == "SCOPE_3":
                    scope_3_sum += val

                cat = (e.category or "OTHER").upper()
                by_cat[cat] = by_cat.get(cat, Decimal("0.0")) + val

                act = e.activity_type
                by_act[act] = by_act.get(act, Decimal("0.0")) + val

                if e.reporting_period:
                    by_period[e.reporting_period] = by_period.get(e.reporting_period, Decimal("0.0")) + val
                if e.reporting_year is not None:
                    by_year[str(e.reporting_year)] = by_year.get(str(e.reporting_year), Decimal("0.0")) + val

        return LedgerAggregationResponse(
            total_posted_co2e=float(total_sum) if posted_entries else None,
            total_posted_co2e_unit="kgCO2e",
            scope_1_co2e=float(scope_1_sum) if scope_1_sum > 0 else None,
            scope_2_co2e=float(scope_2_sum) if scope_2_sum > 0 else None,
            scope_3_co2e=float(scope_3_sum) if scope_3_sum > 0 else None,
            total_posted_entries=len(posted_entries),
            total_excluded_entries=sum(1 for e in active_entries if e.accounting_status == "EXCLUDED"),
            total_superseded_entries=sum(1 for e in entries if e.accounting_status == "SUPERSEDED"),
            by_scope={k: float(v) for k, v in by_scope.items()},
            by_category={k: float(v) for k, v in by_cat.items()},
            by_activity_type={k: float(v) for k, v in by_act.items()},
            by_reporting_period={k: float(v) for k, v in by_period.items()},
            by_reporting_year={k: float(v) for k, v in by_year.items()},
        )


carbon_ledger_service = CarbonLedgerService()
