"""
services/compliance_frameworks.py — Deterministic Compliance Framework Registry (Step 18).

Provides structure mappings and disclosure specifications for report preparation under:
1. GHG Protocol Corporate Accounting Standard
2. BRSR (Business Responsibility & Sustainability Reporting - SEBI)
3. GRI (Global Reporting Initiative Environmental Standards)
4. CBAM (EU Carbon Border Adjustment Mechanism Disclosures)

IMPORTANT BOUNDARY:
This registry represents "report preparation mappings", NOT "regulatory compliance certifications".
"""
from typing import Dict, List, Any
from backend.app.schemas.compliance_framework import (
    ComplianceFrameworkResponse,
    ComplianceFrameworkSectionDefinition,
    ComplianceFrameworkDisclosureDefinition,
)

FRAMEWORK_REGISTRY: Dict[str, Dict[str, Any]] = {
    "GHG_PROTOCOL": {
        "framework_code": "GHG_PROTOCOL",
        "framework_name": "GHG Protocol Corporate Standard",
        "framework_version": "1.0",
        "description": "Standardized accounting framework for corporate Scope 1, Scope 2, and Scope 3 greenhouse gas inventory reporting.",
        "applicable_jurisdiction": "Global / WRI / WBCSD",
        "sections": [
            {
                "section_code": "GHG_ORG_INFO",
                "section_title": "1. Organizational Boundary & Reporting Period",
                "display_order": 1,
                "disclosures": [
                    {
                        "disclosure_code": "GHG_ORG_NAME",
                        "disclosure_title": "Reporting Organization Name",
                        "disclosure_description": "Legal entity name covered by GHG accounting boundary.",
                        "value_type": "TEXT",
                        "required": True,
                        "suggested_source_type": "DOCUMENT",
                    },
                    {
                        "disclosure_code": "GHG_PERIOD",
                        "disclosure_title": "Reporting Period",
                        "disclosure_description": "Time period covered by the GHG inventory.",
                        "value_type": "TEXT",
                        "required": True,
                        "suggested_source_type": "DOCUMENT",
                    },
                    {
                        "disclosure_code": "GHG_APPROACH",
                        "disclosure_title": "Consolidation Approach",
                        "disclosure_description": "Operational control, financial control, or equity share.",
                        "value_type": "TEXT",
                        "required": True,
                        "suggested_source_type": "USER_PROVIDED",
                    },
                ],
            },
            {
                "section_code": "GHG_SCOPE_1",
                "section_title": "2. Direct Scope 1 GHG Emissions",
                "display_order": 2,
                "disclosures": [
                    {
                        "disclosure_code": "GHG_S1_TOTAL",
                        "disclosure_title": "Total Scope 1 Emissions (tCO2e)",
                        "disclosure_description": "Direct GHG emissions from stationary combustion (diesel generators, boilers).",
                        "value_type": "NUMERIC",
                        "unit": "tCO2e",
                        "required": True,
                        "suggested_source_type": "CARBON_LEDGER",
                    },
                    {
                        "disclosure_code": "GHG_S1_DIESEL",
                        "disclosure_title": "Stationary Fuel Consumption (Diesel)",
                        "disclosure_description": "Total volume of diesel fuel consumed in stationary operations.",
                        "value_type": "NUMERIC",
                        "unit": "L",
                        "required": True,
                        "suggested_source_type": "ACTIVITY_DATA",
                    },
                ],
            },
            {
                "section_code": "GHG_SCOPE_2",
                "section_title": "3. Location-Based Scope 2 GHG Emissions",
                "display_order": 3,
                "disclosures": [
                    {
                        "disclosure_code": "GHG_S2_TOTAL",
                        "disclosure_title": "Total Scope 2 Emissions (tCO2e)",
                        "disclosure_description": "Location-based indirect emissions from purchased grid electricity.",
                        "value_type": "NUMERIC",
                        "unit": "tCO2e",
                        "required": True,
                        "suggested_source_type": "CARBON_LEDGER",
                    },
                    {
                        "disclosure_code": "GHG_S2_KWH",
                        "disclosure_title": "Purchased Electricity Quantity",
                        "disclosure_description": "Total grid electricity purchased.",
                        "value_type": "NUMERIC",
                        "unit": "kWh",
                        "required": True,
                        "suggested_source_type": "ACTIVITY_DATA",
                    },
                    {
                        "disclosure_code": "GHG_S2_FACTOR",
                        "disclosure_title": "Grid Emission Factor Applied",
                        "disclosure_description": "CEA India grid emission factor value.",
                        "value_type": "NUMERIC",
                        "unit": "kgCO2e/kWh",
                        "required": True,
                        "suggested_source_type": "CARBON_LEDGER",
                    },
                ],
            },
            {
                "section_code": "GHG_SCOPE_3",
                "section_title": "4. Scope 3 Value Chain Emissions",
                "display_order": 4,
                "disclosures": [
                    {
                        "disclosure_code": "GHG_S3_TOTAL",
                        "disclosure_title": "Total Scope 3 Emissions (tCO2e)",
                        "disclosure_description": "Other indirect GHG emissions (upstream supply chain, transport).",
                        "value_type": "NUMERIC",
                        "unit": "tCO2e",
                        "required": False,
                        "suggested_source_type": "CARBON_LEDGER",
                    },
                ],
            },
            {
                "section_code": "GHG_TOTALS",
                "section_title": "5. Total GHG Inventory & Data Quality",
                "display_order": 5,
                "disclosures": [
                    {
                        "disclosure_code": "GHG_TOTAL_EMISSIONS",
                        "disclosure_title": "Total GHG Footprint (tCO2e)",
                        "disclosure_description": "Sum of posted Scope 1 and Scope 2 emissions.",
                        "value_type": "NUMERIC",
                        "unit": "tCO2e",
                        "required": True,
                        "suggested_source_type": "CARBON_LEDGER",
                    },
                    {
                        "disclosure_code": "GHG_RECONCILIATION",
                        "disclosure_title": "Extracted vs Calculated Reconciliation",
                        "disclosure_description": "Comparison between document-extracted emissions and calculated ledger totals.",
                        "value_type": "TEXT",
                        "required": True,
                        "suggested_source_type": "METRIC",
                    },
                ],
            },
        ],
    },
    "BRSR": {
        "framework_code": "BRSR",
        "framework_name": "BRSR Core (SEBI Essential Indicators)",
        "framework_version": "1.0",
        "description": "Business Responsibility & Sustainability Reporting framework for Indian listed entities (Principle 6 - Environment).",
        "applicable_jurisdiction": "India / SEBI",
        "sections": [
            {
                "section_code": "BRSR_P6_ENERGY",
                "section_title": "Principle 6 — Essential Indicator 1: Energy Consumption",
                "display_order": 1,
                "disclosures": [
                    {
                        "disclosure_code": "BRSR_E_TOTAL_GRID",
                        "disclosure_title": "Total Electricity Purchased (kWh)",
                        "disclosure_description": "Grid electricity purchased from discom.",
                        "value_type": "NUMERIC",
                        "unit": "kWh",
                        "required": True,
                        "suggested_source_type": "ACTIVITY_DATA",
                    },
                    {
                        "disclosure_code": "BRSR_E_SOLAR",
                        "disclosure_title": "Renewable Solar Generation (kWh)",
                        "disclosure_description": "Rooftop solar generation.",
                        "value_type": "NUMERIC",
                        "unit": "kWh",
                        "required": False,
                        "suggested_source_type": "METRIC",
                    },
                    {
                        "disclosure_code": "BRSR_E_DIESEL",
                        "disclosure_title": "Fuel Consumption (Diesel Liters)",
                        "disclosure_description": "Diesel fuel consumed in stationary backup operations.",
                        "value_type": "NUMERIC",
                        "unit": "L",
                        "required": True,
                        "suggested_source_type": "ACTIVITY_DATA",
                    },
                ],
            },
            {
                "section_code": "BRSR_P6_GHG",
                "section_title": "Principle 6 — Essential Indicator 2: GHG Emissions",
                "display_order": 2,
                "disclosures": [
                    {
                        "disclosure_code": "BRSR_GHG_S1",
                        "disclosure_title": "Direct Scope 1 GHG Emissions (tCO2e)",
                        "disclosure_description": "Scope 1 emissions calculated using India stationary combustion factors.",
                        "value_type": "NUMERIC",
                        "unit": "tCO2e",
                        "required": True,
                        "suggested_source_type": "CARBON_LEDGER",
                    },
                    {
                        "disclosure_code": "BRSR_GHG_S2",
                        "disclosure_title": "Indirect Scope 2 GHG Emissions (tCO2e)",
                        "disclosure_description": "Scope 2 emissions calculated using CEA grid factors.",
                        "value_type": "NUMERIC",
                        "unit": "tCO2e",
                        "required": True,
                        "suggested_source_type": "CARBON_LEDGER",
                    },
                ],
            },
            {
                "section_code": "BRSR_P6_WATER_WASTE",
                "section_title": "Principle 6 — Essential Indicator 3 & 4: Water & Waste Management",
                "display_order": 3,
                "disclosures": [
                    {
                        "disclosure_code": "BRSR_WATER_TOTAL",
                        "disclosure_title": "Total Water Withdrawal (kL)",
                        "disclosure_description": "Water consumed across facilities.",
                        "value_type": "NUMERIC",
                        "unit": "kL",
                        "required": False,
                        "suggested_source_type": "METRIC",
                    },
                    {
                        "disclosure_code": "BRSR_WASTE_HAZ",
                        "disclosure_title": "Hazardous Waste Generated (kg)",
                        "disclosure_description": "Hazardous waste generated.",
                        "value_type": "NUMERIC",
                        "unit": "kg",
                        "required": False,
                        "suggested_source_type": "METRIC",
                    },
                ],
            },
        ],
    },
    "GRI": {
        "framework_code": "GRI",
        "framework_name": "GRI Environmental Standards (GRI 302 & 305)",
        "framework_version": "1.0",
        "description": "Global Reporting Initiative standards covering Energy (GRI 302) and Emissions (GRI 305).",
        "applicable_jurisdiction": "Global / GRI Standards",
        "sections": [
            {
                "section_code": "GRI_302",
                "section_title": "GRI 302: Energy (302-1 Energy Consumption Within Organization)",
                "display_order": 1,
                "disclosures": [
                    {
                        "disclosure_code": "GRI_302_1_ELEC",
                        "disclosure_title": "302-1a Electricity Consumption (kWh)",
                        "disclosure_description": "Grid electricity purchased for operation.",
                        "value_type": "NUMERIC",
                        "unit": "kWh",
                        "required": True,
                        "suggested_source_type": "ACTIVITY_DATA",
                    },
                    {
                        "disclosure_code": "GRI_302_1_FUEL",
                        "disclosure_title": "302-1b Non-renewable Fuel Consumption (Liters)",
                        "disclosure_description": "Diesel fuel consumed.",
                        "value_type": "NUMERIC",
                        "unit": "L",
                        "required": True,
                        "suggested_source_type": "ACTIVITY_DATA",
                    },
                ],
            },
            {
                "section_code": "GRI_305",
                "section_title": "GRI 305: Emissions (305-1 & 305-2 Direct & Indirect GHG)",
                "display_order": 2,
                "disclosures": [
                    {
                        "disclosure_code": "GRI_305_1",
                        "disclosure_title": "305-1 Direct (Scope 1) GHG Emissions",
                        "disclosure_description": "Gross Scope 1 GHG emissions in metric tons of CO2 equivalent.",
                        "value_type": "NUMERIC",
                        "unit": "tCO2e",
                        "required": True,
                        "suggested_source_type": "CARBON_LEDGER",
                    },
                    {
                        "disclosure_code": "GRI_305_2",
                        "disclosure_title": "305-2 Energy Indirect (Scope 2) GHG Emissions",
                        "disclosure_description": "Gross location-based Scope 2 GHG emissions in metric tons of CO2 equivalent.",
                        "value_type": "NUMERIC",
                        "unit": "tCO2e",
                        "required": True,
                        "suggested_source_type": "CARBON_LEDGER",
                    },
                ],
            },
        ],
    },
    "CBAM": {
        "framework_code": "CBAM",
        "framework_name": "EU CBAM Emissions Disclosure Preparation",
        "framework_version": "1.0",
        "description": "Preparation disclosures for EU Carbon Border Adjustment Mechanism embedded emissions data.",
        "applicable_jurisdiction": "European Union / CBAM Regulation",
        "sections": [
            {
                "section_code": "CBAM_GENERAL",
                "section_title": "1. Installation & Activity Context",
                "display_order": 1,
                "disclosures": [
                    {
                        "disclosure_code": "CBAM_ORG",
                        "disclosure_title": "Installation Operating Entity",
                        "disclosure_description": "Name of manufacturing or industrial installation entity.",
                        "value_type": "TEXT",
                        "required": True,
                        "suggested_source_type": "DOCUMENT",
                    },
                    {
                        "disclosure_code": "CBAM_PERIOD",
                        "disclosure_title": "Reporting Period",
                        "disclosure_description": "Billing month / year of accounting snapshot.",
                        "value_type": "TEXT",
                        "required": True,
                        "suggested_source_type": "DOCUMENT",
                    },
                ],
            },
            {
                "section_code": "CBAM_EMISSIONS",
                "section_title": "2. Specific Embedded Emissions Disclosures",
                "display_order": 2,
                "disclosures": [
                    {
                        "disclosure_code": "CBAM_DIRECT",
                        "disclosure_title": "Direct Specific Emissions (Scope 1 tCO2e)",
                        "disclosure_description": "Calculated Scope 1 direct emissions from installation fuel combustion.",
                        "value_type": "NUMERIC",
                        "unit": "tCO2e",
                        "required": True,
                        "suggested_source_type": "CARBON_LEDGER",
                    },
                    {
                        "disclosure_code": "CBAM_INDIRECT",
                        "disclosure_title": "Indirect Specific Emissions (Scope 2 tCO2e)",
                        "disclosure_description": "Calculated Scope 2 indirect emissions from electricity consumption.",
                        "value_type": "NUMERIC",
                        "unit": "tCO2e",
                        "required": True,
                        "suggested_source_type": "CARBON_LEDGER",
                    },
                    {
                        "disclosure_code": "CBAM_FACTOR_PROVENANCE",
                        "disclosure_title": "Grid Factor Provenance",
                        "disclosure_description": "Source and version of grid emission factor used.",
                        "value_type": "TEXT",
                        "required": True,
                        "suggested_source_type": "CARBON_LEDGER",
                    },
                ],
            },
        ],
    },
}


class ComplianceFrameworkService:
    """
    Registry service for querying supported compliance framework definitions.
    """

    def get_supported_frameworks(self) -> List[ComplianceFrameworkResponse]:
        result = []
        for code, fw in FRAMEWORK_REGISTRY.items():
            sections_dto = []
            for sec in fw["sections"]:
                disclosures_dto = [
                    ComplianceFrameworkDisclosureDefinition(**d) for d in sec["disclosures"]
                ]
                sections_dto.append(
                    ComplianceFrameworkSectionDefinition(
                        section_code=sec["section_code"],
                        section_title=sec["section_title"],
                        display_order=sec["display_order"],
                        disclosures=disclosures_dto,
                    )
                )
            result.append(
                ComplianceFrameworkResponse(
                    framework_code=fw["framework_code"],
                    framework_name=fw["framework_name"],
                    framework_version=fw["framework_version"],
                    description=fw["description"],
                    applicable_jurisdiction=fw["applicable_jurisdiction"],
                    sections=sections_dto,
                )
            )
        return result

    def get_framework(self, framework_code: str) -> ComplianceFrameworkResponse:
        code = framework_code.strip().upper()
        if code not in FRAMEWORK_REGISTRY:
            raise ValueError(
                f"Unsupported compliance framework '{framework_code}'. "
                f"Supported options: {list(FRAMEWORK_REGISTRY.keys())}"
            )
        fw = FRAMEWORK_REGISTRY[code]
        sections_dto = []
        for sec in fw["sections"]:
            disclosures_dto = [
                ComplianceFrameworkDisclosureDefinition(**d) for d in sec["disclosures"]
            ]
            sections_dto.append(
                ComplianceFrameworkSectionDefinition(
                    section_code=sec["section_code"],
                    section_title=sec["section_title"],
                    display_order=sec["display_order"],
                    disclosures=disclosures_dto,
                )
            )
        return ComplianceFrameworkResponse(
            framework_code=fw["framework_code"],
            framework_name=fw["framework_name"],
            framework_version=fw["framework_version"],
            description=fw["description"],
            applicable_jurisdiction=fw["applicable_jurisdiction"],
            sections=sections_dto,
        )


compliance_framework_service = ComplianceFrameworkService()
