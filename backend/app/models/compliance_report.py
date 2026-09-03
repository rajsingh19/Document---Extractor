"""
models/compliance_report.py — SQLAlchemy Models for Compliance & Sustainability Reports (Step 18).

Stores framework-oriented compliance reports, sections, disclosures, and immutable audit event logs.
Supported frameworks: GHG_PROTOCOL, BRSR, GRI, CBAM.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from backend.app.database.base import Base


class ComplianceReport(Base):
    __tablename__ = "compliance_reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    report_code = Column(String(100), unique=True, nullable=False, index=True)
    report_name = Column(String(255), nullable=False)
    framework = Column(String(50), nullable=False, index=True)  # GHG_PROTOCOL, BRSR, GRI, CBAM
    framework_version = Column(String(50), default="1.0", nullable=False)

    reporting_period = Column(String(50), nullable=False, index=True)
    reporting_year = Column(Integer, nullable=True, index=True)
    organization_name = Column(String(255), default="TARA ENGINEERING WORKS", nullable=False)

    # Workflow Statuses: DRAFT, GENERATED, NEEDS_REVIEW, FINALIZED
    status = Column(String(50), default="DRAFT", nullable=False, index=True)
    report_version = Column(Integer, default=1, nullable=False)

    # Completeness & Quality Summary
    data_quality_status = Column(String(50), default="GOOD", nullable=False)
    completeness_status = Column(String(50), default="INCOMPLETE", nullable=False)  # COMPLETE, PARTIAL, INCOMPLETE, NEEDS_REVIEW
    assurance_status = Column(String(50), default="NOT_ASSURED", nullable=False)  # NOT_ASSURED, INTERNAL_REVIEW, EXTERNAL_ASSURANCE_PENDING, EXTERNALLY_ASSURED

    notes = Column(Text, nullable=True)
    generated_at = Column(DateTime, nullable=True)
    finalized_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ComplianceReportSection(Base):
    """
    Framework-defined section within a ComplianceReport.
    """
    __tablename__ = "compliance_report_sections"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("compliance_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    section_code = Column(String(100), nullable=False, index=True)
    section_title = Column(String(255), nullable=False)
    framework = Column(String(50), nullable=False)
    display_order = Column(Integer, default=1, nullable=False)

    # Statuses: AVAILABLE, PARTIAL, MISSING, NOT_APPLICABLE, NEEDS_REVIEW
    status = Column(String(50), default="MISSING", nullable=False)
    completeness = Column(String(50), default="0%", nullable=False)
    content = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ComplianceDisclosure(Base):
    """
    Individual disclosure item mapped to a report section.
    Holds value, source provenance, evidence references, and status.
    """
    __tablename__ = "compliance_disclosures"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("compliance_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    section_id = Column(Integer, ForeignKey("compliance_report_sections.id", ondelete="CASCADE"), nullable=False, index=True)

    disclosure_code = Column(String(100), nullable=False, index=True)
    disclosure_title = Column(String(255), nullable=False)
    disclosure_description = Column(Text, nullable=True)

    value = Column(Text, nullable=True)
    value_unit = Column(String(50), nullable=True)
    value_type = Column(String(50), default="TEXT", nullable=False)  # NUMERIC, TEXT, BOOLEAN, DATE, ENUM

    # Source Provenance
    source_type = Column(String(50), default="METRIC", nullable=False)  # DOCUMENT, METRIC, ACTIVITY_DATA, CARBON_LEDGER, CARBON_MEASUREMENT, USER_PROVIDED
    source_document_id = Column(Integer, nullable=True)
    source_metric_id = Column(Integer, nullable=True)
    source_activity_id = Column(Integer, nullable=True)
    source_ledger_entry_id = Column(Integer, nullable=True)
    source_text = Column(Text, nullable=True)
    reporting_period = Column(String(50), nullable=True)

    # Statuses: SUPPORTED, PARTIALLY_SUPPORTED, MISSING, NOT_APPLICABLE, NEEDS_REVIEW
    status = Column(String(50), default="MISSING", nullable=False, index=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ComplianceReportEvent(Base):
    """
    Immutable audit log for report lifecycle events.
    """
    __tablename__ = "compliance_report_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("compliance_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)  # CREATED, GENERATED, STATUS_CHANGE, FINALIZED, VERSION_CREATED
    previous_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
