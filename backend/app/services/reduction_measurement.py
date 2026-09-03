"""
services/reduction_measurement.py — Reduction Project Measurement & Verification Service (Step 17).

Deterministic accounting measurement service that:
- Retrieves actual POSTED CarbonLedgerEntry records for reference and measurement periods.
- Calculates observed accounting changes between periods (NOT verified reductions).
- Enforces strict data-availability guardrails (missing data != zero).
- Supports scope, category, and activity-level comparisons.
- Maintains versioned, auditable measurement history.
- Provides verification workflow without claiming independent verification.

CRITICAL BOUNDARIES:
- Does NOT recalculate emissions.
- Does NOT modify CarbonLedgerEntry, CarbonCalculation, ActivityData, or SustainabilityMetric.
- Does NOT claim causality.
- Does NOT issue carbon credits.
- Does NOT calculate ROI or savings.
- Does NOT use LLM for numerical calculations.
"""
import logging
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Dict, Any, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.models.carbon_ledger import CarbonLedgerEntry
from backend.app.models.reduction_measurement import ReductionMeasurement, ReductionMeasurementEvent
from backend.app.models.reduction_project import ReductionProject
from backend.app.models.verification_record import VerificationRecord

logger = logging.getLogger("senseible-reduction-measurement-service")

CAUSALITY_LIMITATIONS = (
    "This comparison shows an observed change in accounting data between the selected periods. "
    "It does not establish that the reduction project caused the change."
)

VALID_MEASUREMENT_STATUSES = {"DRAFT", "READY", "MEASURED", "NEEDS_REVIEW", "FINALIZED"}
VALID_VERIFICATION_STATUSES = {
    "NOT_SUBMITTED", "INTERNAL_REVIEW", "ACCEPTED", "REJECTED",
    "EXTERNAL_VERIFICATION_PENDING", "EXTERNALLY_VERIFIED"
}


def _aggregate_posted_ledger(
    db: Session,
    reporting_period: str,
    scope: Optional[str] = None,
    category: Optional[str] = None,
    activity_type: Optional[str] = None,
    document_id: Optional[int] = None,
) -> Tuple[Optional[Decimal], List[int], List[int]]:
    """
    Aggregate POSTED CarbonLedgerEntry records for a given reporting_period.

    Returns:
        - total_co2e_kg (Decimal | None) — None if no POSTED records exist (not zero)
        - ledger_entry_ids (List[int]) — IDs of POSTED records used
        - document_ids (List[int]) — unique document IDs contributing to the total

    DOES NOT recalculate emissions. DOES NOT treat missing data as zero.
    """
    query = db.query(CarbonLedgerEntry).filter(
        CarbonLedgerEntry.reporting_period == reporting_period,
        CarbonLedgerEntry.accounting_status == "POSTED",
    )
    if document_id is not None:
        query = query.filter(CarbonLedgerEntry.document_id == document_id)
    if scope:
        query = query.filter(CarbonLedgerEntry.scope == scope.strip().upper())
    if category:
        query = query.filter(CarbonLedgerEntry.category == category.strip().upper())
    if activity_type:
        query = query.filter(CarbonLedgerEntry.activity_type == activity_type.strip().lower())

    entries = query.all()

    if not entries:
        return None, [], []

    total_kg = Decimal("0")
    entry_ids = []
    doc_ids = set()
    has_data = False

    for e in entries:
        if e.calculated_co2e is not None:
            total_kg += Decimal(str(e.calculated_co2e))
            has_data = True
        entry_ids.append(e.id)
        if e.document_id:
            doc_ids.add(e.document_id)

    if not has_data:
        # Records exist but all have null calculated_co2e (EXCLUDED-like edge case)
        return None, entry_ids, list(doc_ids)

    return total_kg, entry_ids, list(doc_ids)


class ReductionMeasurementService:
    """
    Deterministic Reduction Project Measurement & Verification Service.
    Operates exclusively on top of POSTED CarbonLedgerEntry records.
    """

    # -------------------------------------------------------------------------
    # MEASUREMENT CREATION
    # -------------------------------------------------------------------------

    def create_measurement(
        self,
        db: Session,
        project_id: int,
        reference_period: str,
        measurement_period: str,
        measurement_scope_type: str = "TOTAL",
        measurement_scope: Optional[str] = None,
        measurement_category: Optional[str] = None,
        measurement_activity_type: Optional[str] = None,
        methodology_note: Optional[str] = None,
    ) -> ReductionMeasurement:
        """
        Create a new ReductionMeasurement for a project.

        Idempotency: Prevents duplicate measurements for the same
        project + reference_period + measurement_period + scope_type + category + activity_type.
        """
        # Validate project exists
        project = db.query(ReductionProject).filter_by(id=project_id).first()
        if not project:
            raise ValueError(f"ReductionProject with ID {project_id} not found.")

        # Validate periods differ
        if reference_period == measurement_period:
            raise ValueError(
                "Reference period and measurement period must be different. "
                "A period cannot be compared with itself."
            )

        scope_type = measurement_scope_type.strip().upper()
        category_n = measurement_category.strip().upper() if measurement_category else None
        activity_n = measurement_activity_type.strip().lower() if measurement_activity_type else None
        scope_n = measurement_scope.strip().upper() if measurement_scope else None

        # Idempotency check: prevent exact duplicate measurements
        existing = db.query(ReductionMeasurement).filter_by(
            project_id=project_id,
            reference_period=reference_period.strip(),
            measurement_period=measurement_period.strip(),
            measurement_scope_type=scope_type,
            measurement_category=category_n,
            measurement_activity_type=activity_n,
            measurement_scope=scope_n,
        ).first()

        if existing:
            return existing

        # Parse years from period strings (YYYY-MM format)
        ref_year = self._parse_year(reference_period)
        meas_year = self._parse_year(measurement_period)

        measurement = ReductionMeasurement(
            project_id=project_id,
            reference_period=reference_period.strip(),
            measurement_period=measurement_period.strip(),
            reference_year=ref_year,
            measurement_year=meas_year,
            measurement_scope_type=scope_type,
            measurement_scope=scope_n,
            measurement_category=category_n,
            measurement_activity_type=activity_n,
            measurement_status="DRAFT",
            evidence_status="NONE",
            verification_status="NOT_SUBMITTED",
            methodology_note=methodology_note,
            limitations=CAUSALITY_LIMITATIONS,
            measurement_version=1,
        )
        db.add(measurement)
        db.commit()
        db.refresh(measurement)

        # Audit event: CREATED
        self._log_event(db, measurement.id, "CREATED", None, "DRAFT",
                        f"Measurement created: reference={reference_period} vs measurement={measurement_period}.")
        return measurement

    # -------------------------------------------------------------------------
    # MEASUREMENT CALCULATION
    # -------------------------------------------------------------------------

    def calculate_measurement(
        self,
        db: Session,
        measurement_id: int,
        document_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve POSTED ledger data for both periods and compute observed accounting change.

        Returns a dict with the comparison result and is_comparable flag.
        DOES NOT recalculate emissions.
        DOES NOT treat missing data as zero.
        """
        measurement = db.query(ReductionMeasurement).filter_by(id=measurement_id).first()
        if not measurement:
            raise ValueError(f"ReductionMeasurement with ID {measurement_id} not found.")

        # If FINALIZED, do not overwrite — require versioning
        if measurement.measurement_status == "FINALIZED":
            raise ValueError(
                "This measurement is FINALIZED and cannot be overwritten. "
                "Create a new measurement version to recalculate."
            )

        # Determine scope filter
        scope_filter = None
        if measurement.measurement_scope_type == "SCOPE":
            scope_filter = measurement.measurement_scope

        # Retrieve POSTED data for REFERENCE period
        ref_co2e_kg, ref_entry_ids, ref_doc_ids = _aggregate_posted_ledger(
            db,
            reporting_period=measurement.reference_period,
            scope=scope_filter,
            category=measurement.measurement_category,
            activity_type=measurement.measurement_activity_type,
            document_id=document_id,
        )

        # Retrieve POSTED data for MEASUREMENT period
        meas_co2e_kg, meas_entry_ids, meas_doc_ids = _aggregate_posted_ledger(
            db,
            reporting_period=measurement.measurement_period,
            scope=scope_filter,
            category=measurement.measurement_category,
            activity_type=measurement.measurement_activity_type,
            document_id=document_id,
        )

        # Comparability check
        is_comparable = True
        reason = None
        if ref_co2e_kg is None:
            is_comparable = False
            reason = (
                f"Reference period '{measurement.reference_period}' has no POSTED accounting data. "
                "Observed change cannot be calculated. "
                "REFERENCE_DATA_UNAVAILABLE"
            )
        elif meas_co2e_kg is None:
            is_comparable = False
            reason = (
                f"Measurement period '{measurement.measurement_period}' has no POSTED accounting data. "
                "Observed change cannot be calculated. "
                "MEASUREMENT_DATA_UNAVAILABLE"
            )

        # Determine evidence status
        all_doc_ids = set(ref_doc_ids) | set(meas_doc_ids)
        if ref_entry_ids or meas_entry_ids:
            evidence_status = "ACCOUNTING_DATA"
        else:
            evidence_status = "NONE"

        if is_comparable:
            # Compute observed change using Decimal arithmetic only
            observed_change = meas_co2e_kg - ref_co2e_kg  # type: ignore[operator]
            observed_pct: Optional[Decimal] = None
            if ref_co2e_kg != Decimal("0"):
                observed_pct = (observed_change / ref_co2e_kg * Decimal("100")).quantize(
                    Decimal("0.0001"), rounding=ROUND_HALF_UP
                )
            # else: divide-by-zero guard — percentage stays None

            # Update measurement record
            measurement.reference_co2e = ref_co2e_kg
            measurement.measurement_co2e = meas_co2e_kg
            measurement.reference_co2e_unit = "kgCO2e"
            measurement.measurement_co2e_unit = "kgCO2e"
            measurement.observed_change = observed_change
            measurement.observed_change_percentage = observed_pct
            measurement.measurement_status = "MEASURED"
            measurement.evidence_status = evidence_status
            measurement.calculated_at = datetime.utcnow()
            measurement.limitations = CAUSALITY_LIMITATIONS

            db.commit()
            db.refresh(measurement)

            # Audit: MEASURED event
            self._log_event(
                db, measurement.id, "MEASURED", "DRAFT", "MEASURED",
                f"Observed accounting change calculated: "
                f"ref={float(ref_co2e_kg):.2f}kgCO2e, meas={float(meas_co2e_kg):.2f}kgCO2e, "
                f"change={float(observed_change):+.4f}kgCO2e."
            )

            return {
                "measurement_id": measurement.id,
                "project_id": measurement.project_id,
                "reference_period": measurement.reference_period,
                "measurement_period": measurement.measurement_period,
                "reference_co2e_kg": float(ref_co2e_kg),
                "measurement_co2e_kg": float(meas_co2e_kg),
                "reference_co2e_t": float(ref_co2e_kg / Decimal("1000")),
                "measurement_co2e_t": float(meas_co2e_kg / Decimal("1000")),
                "observed_change_kg": float(observed_change),
                "observed_change_t": float(observed_change / Decimal("1000")),
                "observed_change_percentage": float(observed_pct) if observed_pct is not None else None,
                "is_comparable": True,
                "measurement_status": "MEASURED",
                "evidence_status": evidence_status,
                "verification_status": measurement.verification_status,
                "reference_ledger_entry_ids": ref_entry_ids,
                "measurement_ledger_entry_ids": meas_entry_ids,
                "reference_document_ids": ref_doc_ids,
                "measurement_document_ids": meas_doc_ids,
                "limitations": CAUSALITY_LIMITATIONS,
                "reason": None,
            }
        else:
            # Mark NEEDS_REVIEW with reason
            measurement.measurement_status = "NEEDS_REVIEW"
            measurement.evidence_status = evidence_status
            measurement.reference_co2e = ref_co2e_kg
            measurement.measurement_co2e = meas_co2e_kg
            measurement.calculated_at = datetime.utcnow()
            db.commit()
            db.refresh(measurement)

            self._log_event(
                db, measurement.id, "STATUS_CHANGE", "DRAFT", "NEEDS_REVIEW",
                f"Measurement requires review: {reason}"
            )

            return {
                "measurement_id": measurement.id,
                "project_id": measurement.project_id,
                "reference_period": measurement.reference_period,
                "measurement_period": measurement.measurement_period,
                "reference_co2e_kg": float(ref_co2e_kg) if ref_co2e_kg is not None else None,
                "measurement_co2e_kg": float(meas_co2e_kg) if meas_co2e_kg is not None else None,
                "reference_co2e_t": float(ref_co2e_kg / Decimal("1000")) if ref_co2e_kg is not None else None,
                "measurement_co2e_t": float(meas_co2e_kg / Decimal("1000")) if meas_co2e_kg is not None else None,
                "observed_change_kg": None,
                "observed_change_t": None,
                "observed_change_percentage": None,
                "is_comparable": False,
                "measurement_status": "NEEDS_REVIEW",
                "evidence_status": evidence_status,
                "verification_status": measurement.verification_status,
                "reference_ledger_entry_ids": ref_entry_ids,
                "measurement_ledger_entry_ids": meas_entry_ids,
                "reference_document_ids": ref_doc_ids,
                "measurement_document_ids": meas_doc_ids,
                "limitations": CAUSALITY_LIMITATIONS,
                "reason": reason,
            }

    # -------------------------------------------------------------------------
    # STATUS MANAGEMENT
    # -------------------------------------------------------------------------

    def update_status(
        self,
        db: Session,
        measurement_id: int,
        new_status: str,
        note: Optional[str] = None,
    ) -> ReductionMeasurement:
        st = new_status.strip().upper()
        if st not in VALID_MEASUREMENT_STATUSES:
            raise ValueError(
                f"Invalid measurement status '{new_status}'. "
                f"Must be one of {sorted(VALID_MEASUREMENT_STATUSES)}"
            )

        measurement = db.query(ReductionMeasurement).filter_by(id=measurement_id).first()
        if not measurement:
            raise ValueError(f"ReductionMeasurement with ID {measurement_id} not found.")

        prev = measurement.measurement_status
        measurement.measurement_status = st
        db.commit()

        self._log_event(db, measurement_id, "STATUS_CHANGE", prev, st,
                        note or f"Measurement status changed from {prev} to {st}.")
        db.refresh(measurement)
        return measurement

    # -------------------------------------------------------------------------
    # LIST & RETRIEVE
    # -------------------------------------------------------------------------

    def get_measurements(
        self,
        db: Session,
        project_id: int,
    ) -> List[ReductionMeasurement]:
        return (
            db.query(ReductionMeasurement)
            .filter_by(project_id=project_id)
            .order_by(desc(ReductionMeasurement.created_at))
            .all()
        )

    def get_measurement(
        self,
        db: Session,
        measurement_id: int,
    ) -> Optional[ReductionMeasurement]:
        return db.query(ReductionMeasurement).filter_by(id=measurement_id).first()

    def get_measurement_events(
        self,
        db: Session,
        measurement_id: int,
    ) -> List[ReductionMeasurementEvent]:
        return (
            db.query(ReductionMeasurementEvent)
            .filter_by(measurement_id=measurement_id)
            .order_by(ReductionMeasurementEvent.created_at.asc())
            .all()
        )

    # -------------------------------------------------------------------------
    # VERIFICATION WORKFLOW
    # -------------------------------------------------------------------------

    def submit_verification(
        self,
        db: Session,
        measurement_id: int,
        verifier_name: Optional[str] = None,
        verifier_organization: Optional[str] = None,
        verification_reference: Optional[str] = None,
        verification_date=None,
        verification_notes: Optional[str] = None,
        initial_status: str = "INTERNAL_REVIEW",
    ) -> VerificationRecord:
        """
        Create or update VerificationRecord for a measurement.
        Does NOT claim independent verification — only records workflow metadata.
        """
        measurement = db.query(ReductionMeasurement).filter_by(id=measurement_id).first()
        if not measurement:
            raise ValueError(f"ReductionMeasurement with ID {measurement_id} not found.")

        st = initial_status.strip().upper()
        if st not in VALID_VERIFICATION_STATUSES:
            raise ValueError(f"Invalid verification status '{initial_status}'.")

        # Check if record already exists
        existing = db.query(VerificationRecord).filter_by(measurement_id=measurement_id).first()

        if existing:
            existing.verifier_name = verifier_name
            existing.verifier_organization = verifier_organization
            existing.verification_reference = verification_reference
            existing.verification_date = verification_date
            existing.verification_notes = verification_notes
            existing.verification_status = st
            db.commit()
            db.refresh(existing)
            record = existing
        else:
            record = VerificationRecord(
                project_id=measurement.project_id,
                measurement_id=measurement_id,
                verifier_name=verifier_name,
                verifier_organization=verifier_organization,
                verification_reference=verification_reference,
                verification_date=verification_date,
                verification_notes=verification_notes,
                verification_status=st,
            )
            db.add(record)
            db.commit()
            db.refresh(record)

        # Update measurement verification status
        prev_vst = measurement.verification_status
        measurement.verification_status = st
        db.commit()

        self._log_event(
            db, measurement_id, "VERIFICATION_SUBMITTED", prev_vst, st,
            f"Verification submitted. Status: {st}."
        )
        return record

    def update_verification_status(
        self,
        db: Session,
        measurement_id: int,
        new_status: str,
        verifier_name: Optional[str] = None,
        verifier_organization: Optional[str] = None,
        verification_reference: Optional[str] = None,
        verification_date=None,
        verification_notes: Optional[str] = None,
        note: Optional[str] = None,
    ) -> VerificationRecord:
        """
        Update verification workflow status with required fields for EXTERNALLY_VERIFIED.
        """
        st = new_status.strip().upper()
        if st not in VALID_VERIFICATION_STATUSES:
            raise ValueError(f"Invalid verification status '{new_status}'.")

        # Safety: EXTERNALLY_VERIFIED requires verifier metadata
        if st == "EXTERNALLY_VERIFIED":
            if not verifier_name:
                raise ValueError("verifier_name is required for EXTERNALLY_VERIFIED status.")
            if not verifier_organization:
                raise ValueError("verifier_organization is required for EXTERNALLY_VERIFIED status.")
            if not verification_reference:
                raise ValueError("verification_reference is required for EXTERNALLY_VERIFIED status.")
            if not verification_date:
                raise ValueError("verification_date is required for EXTERNALLY_VERIFIED status.")

        measurement = db.query(ReductionMeasurement).filter_by(id=measurement_id).first()
        if not measurement:
            raise ValueError(f"ReductionMeasurement with ID {measurement_id} not found.")

        record = db.query(VerificationRecord).filter_by(measurement_id=measurement_id).first()
        if not record:
            # Auto-create if not exists
            record = VerificationRecord(
                project_id=measurement.project_id,
                measurement_id=measurement_id,
                verification_status=st,
            )
            db.add(record)

        # Update fields provided
        if verifier_name is not None:
            record.verifier_name = verifier_name
        if verifier_organization is not None:
            record.verifier_organization = verifier_organization
        if verification_reference is not None:
            record.verification_reference = verification_reference
        if verification_date is not None:
            record.verification_date = verification_date
        if verification_notes is not None:
            record.verification_notes = verification_notes

        prev_vst = record.verification_status
        record.verification_status = st
        db.commit()
        db.refresh(record)

        # Sync measurement verification_status
        measurement.verification_status = st
        db.commit()

        event_type = "VERIFICATION_ACCEPTED" if st == "ACCEPTED" else (
            "VERIFICATION_REJECTED" if st == "REJECTED" else "STATUS_CHANGE"
        )
        self._log_event(
            db, measurement_id, event_type, prev_vst, st,
            note or f"Verification status updated: {prev_vst} → {st}."
        )
        return record

    def get_verification(
        self,
        db: Session,
        measurement_id: int,
    ) -> Optional[VerificationRecord]:
        return db.query(VerificationRecord).filter_by(measurement_id=measurement_id).first()

    # -------------------------------------------------------------------------
    # AUDIT EVENT
    # -------------------------------------------------------------------------

    def _log_event(
        self,
        db: Session,
        measurement_id: int,
        event_type: str,
        previous_status: Optional[str],
        new_status: Optional[str],
        note: Optional[str] = None,
    ) -> None:
        event = ReductionMeasurementEvent(
            measurement_id=measurement_id,
            event_type=event_type,
            previous_status=previous_status,
            new_status=new_status,
            note=note,
        )
        db.add(event)
        db.commit()

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    @staticmethod
    def _parse_year(period: str) -> Optional[int]:
        """Extract year from YYYY-MM period string."""
        try:
            return int(period.strip().split("-")[0])
        except (ValueError, IndexError):
            return None

    @staticmethod
    def build_measurement_dto(measurement: ReductionMeasurement, events=None) -> Dict[str, Any]:
        """
        Build a serializable dict for a measurement response, converting kgCO2e to tCO2e.
        """
        kg_to_t = lambda v: float(Decimal(str(v)) / Decimal("1000")) if v is not None else None

        return {
            "id": measurement.id,
            "project_id": measurement.project_id,
            "reference_period": measurement.reference_period,
            "measurement_period": measurement.measurement_period,
            "reference_year": measurement.reference_year,
            "measurement_year": measurement.measurement_year,
            "measurement_scope_type": measurement.measurement_scope_type,
            "measurement_scope": measurement.measurement_scope,
            "measurement_category": measurement.measurement_category,
            "measurement_activity_type": measurement.measurement_activity_type,
            "reference_co2e": float(measurement.reference_co2e) if measurement.reference_co2e is not None else None,
            "measurement_co2e": float(measurement.measurement_co2e) if measurement.measurement_co2e is not None else None,
            "reference_co2e_unit": measurement.reference_co2e_unit,
            "measurement_co2e_unit": measurement.measurement_co2e_unit,
            "reference_co2e_t": kg_to_t(measurement.reference_co2e),
            "measurement_co2e_t": kg_to_t(measurement.measurement_co2e),
            "observed_change": float(measurement.observed_change) if measurement.observed_change is not None else None,
            "observed_change_t": kg_to_t(measurement.observed_change),
            "observed_change_percentage": float(measurement.observed_change_percentage) if measurement.observed_change_percentage is not None else None,
            "measurement_status": measurement.measurement_status,
            "evidence_status": measurement.evidence_status,
            "verification_status": measurement.verification_status,
            "methodology_note": measurement.methodology_note,
            "limitations": measurement.limitations,
            "measurement_version": measurement.measurement_version,
            "calculated_at": measurement.calculated_at.isoformat() if measurement.calculated_at else None,
            "created_at": measurement.created_at.isoformat() if measurement.created_at else None,
            "updated_at": measurement.updated_at.isoformat() if measurement.updated_at else None,
            "events": [
                {
                    "id": e.id,
                    "measurement_id": e.measurement_id,
                    "event_type": e.event_type,
                    "previous_status": e.previous_status,
                    "new_status": e.new_status,
                    "note": e.note,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in (events or [])
            ],
        }


reduction_measurement_service = ReductionMeasurementService()
