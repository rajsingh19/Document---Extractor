from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

class DocumentBase(BaseModel):
    filename: str
    original_filename: str
    file_size: int
    mime_type: str = "application/pdf"
    page_count: int = 1

class DocumentResponse(DocumentBase):
    id: int
    status: str
    extraction_method: Optional[str] = None
    company_name: Optional[str] = None
    document_type: Optional[str] = None
    reporting_period: Optional[str] = None
    confidence_score: float = 0.0
    total_energy_kwh: Optional[float] = None
    total_emissions_tco2e: Optional[float] = None
    total_water_kl: Optional[float] = None
    total_waste_kg: Optional[float] = None
    compliance_status: Optional[str] = None
    extracted_text: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DocumentListResponse(BaseModel):
    total: int
    page: int
    limit: int
    documents: List[DocumentResponse]

class DashboardStatsResponse(BaseModel):
    total_documents: int
    processed_count: int
    pending_count: int
    failed_count: int
    total_energy_kwh: float
    total_emissions_tco2e: float
    total_water_kl: float
    total_waste_kg: float
    document_types_breakdown: Dict[str, int]
    compliance_breakdown: Dict[str, int]
    extraction_methods_breakdown: Dict[str, int]

class ProcessDocumentRequest(BaseModel):
    force_ocr: bool = False
