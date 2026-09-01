from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class CompanyInfo(BaseModel):
    name: Optional[str] = Field(None, description="Company or business name")
    registration_id: Optional[str] = Field(None, description="GSTIN, CIN, MSME Udyam, or Business Reg ID")
    address: Optional[str] = Field(None, description="Registered facility or plant address")
    industry_sector: Optional[str] = Field(None, description="Manufacturing, Textiles, Forging, Chemical, etc.")
    contact_email: Optional[str] = Field(None, description="Official email or representative email")

class PeriodInfo(BaseModel):
    billing_month: Optional[str] = Field(None, description="e.g. October 2024, Q3 2024, FY2023-24")
    start_date: Optional[str] = Field(None, description="Start date YYYY-MM-DD or string")
    end_date: Optional[str] = Field(None, description="End date YYYY-MM-DD or string")
    issue_date: Optional[str] = Field(None, description="Date document was issued YYYY-MM-DD or string")

class EnergyMetrics(BaseModel):
    electricity_kwh: Optional[float] = Field(None, description="Total active electricity consumption in kWh / Units")
    peak_demand_kva_kw: Optional[float] = Field(None, description="Peak demand or connected load in kVA / kW")
    power_factor: Optional[float] = Field(None, description="Average Power Factor (0.00 to 1.00)")
    renewable_energy_kwh: Optional[float] = Field(None, description="Solar/Wind/Renewable energy generated or consumed in kWh")
    fuel_diesel_liters: Optional[float] = Field(None, description="Diesel / HSD consumption in Liters")
    natural_gas_png_cng: Optional[float] = Field(None, description="Natural gas / PNG / CNG in SCM / MMBTU / kg")
    total_energy_cost_inr: Optional[float] = Field(None, description="Total energy cost or bill amount (numerical)")
    currency: Optional[str] = Field("INR", description="Currency symbol or code")

class CarbonEmissionsMetrics(BaseModel):
    scope_1_direct_tco2e: Optional[float] = Field(None, description="Scope 1 Direct GHG emissions (Fuel, Generators, Fleet) in metric tonnes CO2e")
    scope_2_indirect_tco2e: Optional[float] = Field(None, description="Scope 2 Indirect GHG emissions (Purchased Grid Electricity) in metric tonnes CO2e")
    total_ghg_emissions_tco2e: Optional[float] = Field(None, description="Total Scope 1 + Scope 2 emissions in tCO2e explicitly stated")
    emission_intensity_per_unit: Optional[str] = Field(None, description="e.g. 0.82 kg CO2e / kWh or kg CO2e / unit produced")

class WaterAndWasteMetrics(BaseModel):
    water_consumption_kl: Optional[float] = Field(None, description="Total freshwater consumption in kilo-liters (kL) or cubic meters (m³)")
    recycled_water_kl: Optional[float] = Field(None, description="Treated / recycled effluent water in kL")
    hazardous_waste_kg: Optional[float] = Field(None, description="Hazardous industrial waste generated in kg or MT")
    non_hazardous_waste_kg: Optional[float] = Field(None, description="General / non-hazardous waste in kg or MT")
    waste_recycled_percentage: Optional[float] = Field(None, description="Percentage of waste diverted/recycled (0-100%)")

class CertificationAndCompliance(BaseModel):
    certifications_identified: List[str] = Field(default_factory=list, description="e.g. ISO 14001, ISO 50001, ISO 9001, ZED Gold, LEED")
    audit_standard: Optional[str] = Field(None, description="Audit type: Energy Audit, ESG Assessment, Pollution Control Board NOC")
    compliance_status: Optional[str] = Field(None, description="Compliant, Action Required, Pending Renewal, Non-Compliant")
    findings_and_recommendations: List[str] = Field(default_factory=list, description="Key sustainability observations or recommendations")

class LineItem(BaseModel):
    item_description: str = Field(..., description="Line item description")
    quantity: Optional[float] = Field(None, description="Quantity (numerical)")
    unit: Optional[str] = Field(None, description="Unit of measurement (kWh, liters, kg, MT, kL, charges)")
    unit_rate: Optional[float] = Field(None, description="Rate per unit")
    total_amount: Optional[float] = Field(None, description="Total amount or charge")

class FieldEvidence(BaseModel):
    field: str = Field(..., description="Extracted field name (e.g. electricity_kwh, company_name, total_cost)")
    value: Optional[Any] = Field(None, description="Extracted numerical or string value")
    unit: Optional[str] = Field(None, description="Unit associated with the value (e.g. kWh, Liters, INR, kL, kg, tCO2e)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Field-level confidence score (0.0 to 1.0)")
    confidence_level: str = Field("HIGH", description="HIGH (>=0.9), MEDIUM (0.7-0.89), LOW (<0.7)")
    source_text: Optional[str] = Field(None, description="Exact textual excerpt from the document verifying this extracted value")
    is_verified: bool = Field(False, description="Whether a human reviewer has verified this field")
    human_corrected_value: Optional[Any] = Field(None, description="Human corrected value if edited")

class QualitySummary(BaseModel):
    total_fields: int = Field(0, description="Total important fields evaluated")
    total_expected_fields: int = Field(0, description="Total expected fields for document type")
    expected_fields_found: int = Field(0, description="Expected fields present in document")
    expected_fields_missing: int = Field(0, description="Expected fields missing in document")
    not_applicable_fields: int = Field(0, description="Fields not applicable for this document type")
    expected_missing_list: List[str] = Field(default_factory=list, description="List of expected fields missing")
    not_applicable_list: List[str] = Field(default_factory=list, description="List of not applicable fields")
    evidence_backed: int = Field(0, description="Fields supported by verifiable source text evidence")
    high_confidence: int = Field(0, description="Fields with high confidence (>=0.9)")
    medium_confidence: int = Field(0, description="Fields with medium confidence (0.7-0.89)")
    low_confidence: int = Field(0, description="Fields with low confidence (<0.7)")
    missing_fields: List[str] = Field(default_factory=list, description="Important missing fields (alias for expected_missing_list)")
    human_verified: int = Field(0, description="Fields verified by human reviewer")
    quality_score: float = Field(0.0, ge=0.0, le=100.0, description="Deterministic Extraction Quality Score (0 to 100)")
    scoring_breakdown: Dict[str, float] = Field(default_factory=dict, description="Transparent deterministic scoring breakdown")

class ExtractionMetadata(BaseModel):
    provider: str = Field("openai", description="'openai' or 'heuristic_fallback'")
    model: Optional[str] = Field(None, description="LLM model identifier or heuristic engine version")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall document confidence score (0.0 to 1.0)")
    extraction_method: Optional[str] = Field(None, description="'pymupdf' or 'ocr_fallback'")
    review_status: str = Field("NEEDS_REVIEW", description="'COMPLETED', 'NEEDS_REVIEW', 'VERIFIED'")
    quality_score: float = Field(0.0, ge=0.0, le=100.0, description="Deterministic Quality Score (0 to 100)")
    processing_notes: Optional[str] = Field(None, description="Diagnostics, fallback reasoning, or quality notes")

class SustainabilityDocumentExtraction(BaseModel):
    document_type: str = Field(
        ...,
        description="Category: Electricity Bill, Fuel Receipt, Water Bill, Waste Manifest, ESG Audit Report, Commercial Invoice, Environmental Audit"
    )
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Overall confidence score (0.0 to 1.0)")
    executive_summary: str = Field(..., description="A concise factual summary based ONLY on explicit document data")
    metadata: ExtractionMetadata = Field(default_factory=lambda: ExtractionMetadata(provider="openai", confidence=0.9))
    quality_summary: QualitySummary = Field(default_factory=QualitySummary)
    company: CompanyInfo = Field(default_factory=CompanyInfo)
    period: PeriodInfo = Field(default_factory=PeriodInfo)
    energy: EnergyMetrics = Field(default_factory=EnergyMetrics)
    carbon_emissions: CarbonEmissionsMetrics = Field(default_factory=CarbonEmissionsMetrics)
    water_and_waste: WaterAndWasteMetrics = Field(default_factory=WaterAndWasteMetrics)
    compliance: CertificationAndCompliance = Field(default_factory=CertificationAndCompliance)
    line_items: List[LineItem] = Field(default_factory=list, description="Granular line items or tariff charges")
    evidence: List[FieldEvidence] = Field(default_factory=list, description="Field-level confidence and source evidence anchors")
    missing_fields: List[str] = Field(default_factory=list, description="Important fields absent in document")
    raw_key_value_pairs: Dict[str, Any] = Field(default_factory=dict, description="Additional miscellaneous key-value pairs extracted")
