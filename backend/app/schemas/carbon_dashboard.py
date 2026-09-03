"""
schemas/carbon_dashboard.py — Pydantic Schemas for Carbon Footprint Dashboard & Analytics (Step 15).
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CarbonDashboardSummary(BaseModel):
    """
    High-level executive summary of calculated & posted carbon emissions.
    """
    total_calculated_co2e_kg: Optional[float] = None
    total_calculated_co2e_t: Optional[float] = None
    total_calculated_co2e_unit: str = "tCO2e"
    scope_1_co2e_kg: Optional[float] = None
    scope_1_co2e_t: Optional[float] = None
    scope_2_co2e_kg: Optional[float] = None
    scope_2_co2e_t: Optional[float] = None
    scope_3_co2e_kg: Optional[float] = None
    scope_3_co2e_t: Optional[float] = None
    posted_entry_count: int = 0
    excluded_entry_count: int = 0
    superseded_entry_count: int = 0
    document_count: int = 0
    activity_count: int = 0
    reporting_period_count: int = 0
    latest_reporting_period: Optional[str] = None


class CarbonScopeItem(BaseModel):
    scope: str  # SCOPE_1, SCOPE_2, SCOPE_3
    scope_label: str
    co2e_kg: float
    co2e_t: float
    percentage_of_total: Optional[float] = None
    entry_count: int = 0


class CarbonScopeBreakdown(BaseModel):
    total_co2e_kg: float = 0.0
    total_co2e_t: float = 0.0
    items: List[CarbonScopeItem] = Field(default_factory=list)


class CarbonCategoryItem(BaseModel):
    category: str  # ENERGY, FUEL, TRANSPORT, WATER, WASTE, OTHER
    co2e_kg: float
    co2e_t: float
    percentage_of_total: Optional[float] = None
    entry_count: int = 0


class CarbonCategoryBreakdown(BaseModel):
    total_co2e_kg: float = 0.0
    total_co2e_t: float = 0.0
    items: List[CarbonCategoryItem] = Field(default_factory=list)


class CarbonActivityItem(BaseModel):
    activity_type: str
    category: str
    scope: Optional[str] = None
    co2e_kg: float
    co2e_t: float
    percentage_of_total: Optional[float] = None
    entry_count: int = 0


class CarbonActivityBreakdown(BaseModel):
    items: List[CarbonActivityItem] = Field(default_factory=list)


class CarbonDocumentContributionItem(BaseModel):
    document_id: int
    document_name: str
    reporting_period: Optional[str] = None
    reporting_year: Optional[int] = None
    total_co2e_kg: float
    total_co2e_t: float
    scope_1_t: Optional[float] = None
    scope_2_t: Optional[float] = None
    scope_3_t: Optional[float] = None
    percentage_of_total: Optional[float] = None
    posted_records: int = 0


class CarbonDocumentContribution(BaseModel):
    total_documents: int = 0
    items: List[CarbonDocumentContributionItem] = Field(default_factory=list)


class CarbonHistoricalPoint(BaseModel):
    reporting_period: str
    total_co2e_kg: float
    total_co2e_t: float
    scope_1_kg: Optional[float] = None
    scope_1_t: Optional[float] = None
    scope_2_kg: Optional[float] = None
    scope_2_t: Optional[float] = None
    scope_3_kg: Optional[float] = None
    scope_3_t: Optional[float] = None
    entry_count: int = 0


class CarbonYearPoint(BaseModel):
    year: int
    total_co2e_kg: float
    total_co2e_t: float
    scope_1_t: Optional[float] = None
    scope_2_t: Optional[float] = None
    scope_3_t: Optional[float] = None
    entry_count: int = 0


class CarbonPeriodComparison(BaseModel):
    comparison_available: bool = False
    current_period: Optional[str] = None
    previous_period: Optional[str] = None
    current_co2e_t: Optional[float] = None
    previous_co2e_t: Optional[float] = None
    absolute_change_t: Optional[float] = None
    percentage_change: Optional[float] = None
    message: Optional[str] = None


class CarbonTrendsResponse(BaseModel):
    periods: List[CarbonHistoricalPoint] = Field(default_factory=list)
    years: List[CarbonYearPoint] = Field(default_factory=list)
    comparison: CarbonPeriodComparison


class CarbonDataCoverage(BaseModel):
    total_activity_records: int = 0
    calculated_records: int = 0
    posted_ledger_records: int = 0
    excluded_records: int = 0
    superseded_records: int = 0
    no_factor_records: int = 0
    ineligible_records: int = 0
    multiple_factor_records: int = 0
    invalid_records: int = 0
    missing_geography_records: int = 0
    missing_year_records: int = 0
    unresolved_items: List[Dict[str, Any]] = Field(default_factory=list)
    notice: str = "Excluded records are not treated as zero emissions."


class CarbonTopSourceItem(BaseModel):
    rank: int
    activity_type: str
    category: str
    scope: Optional[str] = None
    co2e_kg: float
    co2e_t: float
    percentage_of_total: Optional[float] = None
    document_id: Optional[int] = None
    document_name: Optional[str] = None


class CarbonTopSourcesResponse(BaseModel):
    items: List[CarbonTopSourceItem] = Field(default_factory=list)


class DashboardReconciliationItem(BaseModel):
    scope_or_metric: str
    extracted_value_t: Optional[float] = None
    calculated_value_t: Optional[float] = None
    difference_t: Optional[float] = None
    status: str
    notes: Optional[str] = None


class CarbonDashboardReconciliation(BaseModel):
    total_extracted_t: Optional[float] = None
    total_calculated_t: Optional[float] = None
    difference_t: Optional[float] = None
    overall_status: str
    items: List[DashboardReconciliationItem] = Field(default_factory=list)


class CarbonDashboardResponse(BaseModel):
    summary: CarbonDashboardSummary
    scopes: CarbonScopeBreakdown
    categories: CarbonCategoryBreakdown
    activities: CarbonActivityBreakdown
    documents: CarbonDocumentContribution
    trends: CarbonTrendsResponse
    coverage: CarbonDataCoverage
    top_sources: CarbonTopSourcesResponse
    reconciliation: CarbonDashboardReconciliation
    dashboard_version: str = "1.0"
