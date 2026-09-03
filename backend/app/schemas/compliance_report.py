"""
schemas/compliance_report.py — Pydantic Schemas for Compliance Reports (Step 18).
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ComplianceReportCreate(BaseModel):
    framework: str  # GHG_PROTOCOL, BRSR, GRI, CBAM
    reporting_period: str  # e.g. '2024-10'
    reporting_year: Optional[int] = None
    organization_name: Optional[str] = "TARA ENGINEERING WORKS"
    report_name: Optional[str] = None
    notes: Optional[str] = None


class ComplianceReportStatusUpdate(BaseModel):
    status: str  # DRAFT, GENERATED, NEEDS_REVIEW, FINALIZED
    assurance_status: Optional[str] = None  # NOT_ASSURED, INTERNAL_REVIEW, EXTERNAL_ASSURANCE_PENDING, EXTERNALLY_ASSURED
    note: Optional[str] = None


class ComplianceDisclosureUserUpdate(BaseModel):
    value: str
    value_unit: Optional[str] = None
    notes: Optional[str] = None


class ComplianceDisclosureResponse(BaseModel):
    id: int
    report_id: int
    section_id: int
    disclosure_code: str
    disclosure_title: str
    disclosure_description: Optional[str] = None
    value: Optional[str] = None
    value_unit: Optional[str] = None
    value_type: str
    source_type: str
    source_document_id: Optional[int] = None
    source_metric_id: Optional[int] = None
    source_activity_id: Optional[int] = None
    source_ledger_entry_id: Optional[int] = None
    source_text: Optional[str] = None
    reporting_period: Optional[str] = None
    status: str
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class ComplianceReportSectionResponse(BaseModel):
    id: int
    report_id: int
    section_code: str
    section_title: str
    framework: str
    display_order: int
    status: str
    completeness: str
    content: Optional[str] = None
    notes: Optional[str] = None
    disclosures: List[ComplianceDisclosureResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ComplianceReportEventResponse(BaseModel):
    id: int
    report_id: int
    event_type: str
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ComplianceReportResponse(BaseModel):
    id: int
    report_code: str
    report_name: str
    framework: str
    framework_version: str
    reporting_period: str
    reporting_year: Optional[int] = None
    organization_name: str
    status: str
    report_version: int
    data_quality_status: str
    completeness_status: str
    assurance_status: str
    notes: Optional[str] = None
    generated_at: Optional[datetime] = None
    finalized_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    # Aggregated metrics
    total_disclosures: int = 0
    supported_disclosures: int = 0
    partial_disclosures: int = 0
    missing_disclosures: int = 0
    needs_review_disclosures: int = 0

    disclaimer: str = (
        "This framework mapping is provided for report preparation and does not constitute legal, regulatory, audit, or assurance certification."
    )
    sections: List[ComplianceReportSectionResponse] = Field(default_factory=list)
    events: List[ComplianceReportEventResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ComplianceReportList(BaseModel):
    total: int
    items: List[ComplianceReportResponse] = Field(default_factory=list)
