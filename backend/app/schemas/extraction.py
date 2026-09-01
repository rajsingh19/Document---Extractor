from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class CompanyInfo(BaseModel):
    name: Optional[str] = Field(None, description="Company or business name")
    registration_id: Optional[str] = Field(None, description="GSTIN, CIN, MSME Udyam, or Business Reg ID")
    address: Optional[str] = Field(None, description="Registered facility or plant address")
    industry_sector: Optional[str] = Field(None, description="Manufacturing, Textiles, Forging, Chemical, etc.")
    contact_email: Optional[str] = Field(None, description="Official email or representative email")

class PeriodInfo(BaseModel):
    billing_month: Optional[str] = Field(None, description="e.g. October 2024, Q3 2024")
    start_date: Optional[str] = Field(None, description="Start date YYYY-MM-DD or string")
    end_date: Optional[str] = Field(None, description="End date YYYY-MM-DD or string")
    issue_date: Optional[str] = Field(None, description="Date document was issued")

class EnergyMetrics(BaseModel):
    electricity_kwh: Optional[float] = Field(None, description="Total active electricity consumption in kWh / Units")
    peak_demand_kva_kw: Optional[float] = Field(None, description="Peak demand or connected load in kVA / kW")
    power_factor: Optional[float] = Field(None, description="Average Power Factor (0.00 to 1.00)")
    renewable_energy_kwh: Optional[float] = Field(None, description="Solar/Wind/Renewable energy generated or consumed in kWh")
    fuel_diesel_liters: Optional[float] = Field(None, description="Diesel / HSD consumption in Liters")
    natural_gas_png_cng: Optional[float] = Field(None, description="Natural gas / PNG / CNG in SCM / MMBTU / kg")
    total_energy_cost_inr: Optional[float] = Field(None, description="Total energy cost or bill amount")
    currency: Optional[str] = Field("INR", description="Currency symbol or code")

class CarbonEmissionsMetrics(BaseModel):
    scope_1_direct_tco2e: Optional[float] = Field(None, description="Scope 1 Direct GHG emissions (Fuel, Generators, Fleet) in metric tonnes CO2e")
    scope_2_indirect_tco2e: Optional[float] = Field(None, description="Scope 2 Indirect GHG emissions (Purchased Grid Electricity) in metric tonnes CO2e")
    total_ghg_emissions_tco2e: Optional[float] = Field(None, description="Total Scope 1 + Scope 2 emissions in tCO2e")
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
    quantity: Optional[float] = Field(None, description="Quantity")
    unit: Optional[str] = Field(None, description="Unit of measurement (kWh, liters, kg, MT, kL)")
    unit_rate: Optional[float] = Field(None, description="Rate per unit")
    total_amount: Optional[float] = Field(None, description="Total amount or charge")

class SustainabilityDocumentExtraction(BaseModel):
    document_type: str = Field(
        ...,
        description="Category: Electricity Bill, Energy Audit Report, Carbon Footprint Assessment, Water & Waste Log, ESG Compliance Certificate, Fuel Receipt, Environmental Audit"
    )
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence level of overall extraction (0.0 to 1.0)")
    executive_summary: str = Field(..., description="A 2-3 sentence executive sustainability summary of the document")
    company: CompanyInfo = Field(default_factory=CompanyInfo)
    period: PeriodInfo = Field(default_factory=PeriodInfo)
    energy: EnergyMetrics = Field(default_factory=EnergyMetrics)
    carbon_emissions: CarbonEmissionsMetrics = Field(default_factory=CarbonEmissionsMetrics)
    water_and_waste: WaterAndWasteMetrics = Field(default_factory=WaterAndWasteMetrics)
    compliance: CertificationAndCompliance = Field(default_factory=CertificationAndCompliance)
    line_items: List[LineItem] = Field(default_factory=list, description="Granular extracted line items or tariff breakdown")
    raw_key_value_pairs: Dict[str, Any] = Field(default_factory=dict, description="Additional miscellaneous key-value pairs extracted")
