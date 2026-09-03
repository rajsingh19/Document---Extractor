"""
schemas/compliance_framework.py — Pydantic Schemas for Compliance Frameworks Registry (Step 18).
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class ComplianceFrameworkDisclosureDefinition(BaseModel):
    disclosure_code: str
    disclosure_title: str
    disclosure_description: Optional[str] = None
    value_type: str = "TEXT"  # NUMERIC, TEXT, BOOLEAN, DATE, ENUM
    required: bool = True
    suggested_source_type: str = "METRIC"
    unit: Optional[str] = None


class ComplianceFrameworkSectionDefinition(BaseModel):
    section_code: str
    section_title: str
    display_order: int
    disclosures: List[ComplianceFrameworkDisclosureDefinition] = Field(default_factory=list)


class ComplianceFrameworkResponse(BaseModel):
    framework_code: str  # GHG_PROTOCOL, BRSR, GRI, CBAM
    framework_name: str
    framework_version: str = "1.0"
    description: str
    applicable_jurisdiction: str = "Global / India"
    disclaimer: str = "This framework mapping is provided for report preparation and does not constitute legal, regulatory, audit, or assurance certification."
    sections: List[ComplianceFrameworkSectionDefinition] = Field(default_factory=list)
