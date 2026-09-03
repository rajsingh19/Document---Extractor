"""
schemas/carbon_ledger.py — Pydantic Schemas for Carbon Accounting Ledger (Step 14).
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CarbonLedgerPostRequest(BaseModel):
    """
    Request payload to post a single CarbonCalculation into the ledger.
    """
    carbon_calculation_id: int = Field(..., description="ID of the CarbonCalculation record to post")


class CarbonLedgerEntryResponse(BaseModel):
    """
    Full serializable representation of a CarbonLedgerEntry record.
    """
    id: int
    carbon_calculation_id: int
    activity_data_id: Optional[int] = None
    document_id: Optional[int] = None
    metric_id: Optional[int] = None
    activity_type: str
    category: str
    activity_role: str
    activity_group_id: Optional[str] = None
    quantity: float
    activity_unit: str
    calculated_co2e: Optional[float] = None
    calculated_co2e_unit: str = "kgCO2e"
    calculation_version: str = "1.0"
    emission_factor_id: Optional[int] = None
    factor_code: Optional[str] = None
    factor_name: Optional[str] = None
    factor_value: Optional[float] = None
    factor_unit: Optional[str] = None
    factor_version: Optional[str] = None
    factor_source: Optional[str] = None
    geography: Optional[str] = None
    reporting_period: Optional[str] = None
    reporting_year: Optional[int] = None
    scope: Optional[str] = None
    accounting_status: str
    accounting_reason: Optional[str] = None
    ledger_version: str = "1.0"
    source_field: Optional[str] = None
    source_text: Optional[str] = None
    page: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CarbonLedgerListResponse(BaseModel):
    total: int
    items: List[CarbonLedgerEntryResponse]


class DocumentLedgerSummary(BaseModel):
    """
    Document-level Carbon Accounting Ledger Summary.
    """
    document_id: int
    total_ledger_records: int = 0
    posted_records: int = 0
    excluded_records: int = 0
    superseded_records: int = 0
    total_posted_co2e: Optional[float] = None
    total_posted_co2e_unit: str = "kgCO2e"
    scope_1_posted_co2e: Optional[float] = None
    scope_2_posted_co2e: Optional[float] = None
    scope_3_posted_co2e: Optional[float] = None
    category_totals: Dict[str, float] = Field(default_factory=dict)
    reporting_periods: List[str] = Field(default_factory=list)
    reporting_years: List[int] = Field(default_factory=list)
    entries: List[CarbonLedgerEntryResponse] = Field(default_factory=list)


class ReconciliationItem(BaseModel):
    """
    Detailed comparison item between extracted and calculated/posted emissions.
    """
    scope_or_metric: str
    extracted_value: Optional[float] = None
    extracted_unit: Optional[str] = None
    calculated_value_kg: Optional[float] = None
    calculated_value_t: Optional[float] = None
    difference_t: Optional[float] = None
    difference_kg: Optional[float] = None
    status: str  # MATCH, DIFFERENCE, EXTRACTED_ONLY, CALCULATED_ONLY, NO_DATA
    notes: Optional[str] = None


class LedgerReconciliationResponse(BaseModel):
    """
    Reconciliation between extracted document metrics and calculated/posted ledger values.
    """
    document_id: int
    overall_status: str
    scope_1: ReconciliationItem
    scope_2: ReconciliationItem
    total: ReconciliationItem
    items: List[ReconciliationItem] = Field(default_factory=list)


class LedgerAggregationResponse(BaseModel):
    """
    Global / multi-document accounting aggregation response.
    """
    total_posted_co2e: Optional[float] = None
    total_posted_co2e_unit: str = "kgCO2e"
    scope_1_co2e: Optional[float] = None
    scope_2_co2e: Optional[float] = None
    scope_3_co2e: Optional[float] = None
    total_posted_entries: int = 0
    total_excluded_entries: int = 0
    total_superseded_entries: int = 0
    by_scope: Dict[str, float] = Field(default_factory=dict)
    by_category: Dict[str, float] = Field(default_factory=dict)
    by_activity_type: Dict[str, float] = Field(default_factory=dict)
    by_reporting_period: Dict[str, float] = Field(default_factory=dict)
    by_reporting_year: Dict[str, float] = Field(default_factory=dict)
