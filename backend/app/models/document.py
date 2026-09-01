from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, JSON
from backend.app.database.base import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), default="application/pdf")
    page_count = Column(Integer, default=1)
    
    # Status: PENDING, EXTRACTING_TEXT, RUNNING_LLM, VALIDATING, COMPLETED, FAILED
    status = Column(String(50), default="PENDING", index=True)
    
    # Extraction Method: pymupdf, ocr_fallback, hybrid
    extraction_method = Column(String(50), nullable=True)
    
    # High-level extracted fields for quick querying & filtering
    company_name = Column(String(255), nullable=True, index=True)
    document_type = Column(String(100), nullable=True, index=True)
    reporting_period = Column(String(100), nullable=True)
    confidence_score = Column(Float, default=0.0)
    
    # Key Sustainability Summary Fields (for fast analytics/KPIs)
    total_energy_kwh = Column(Float, nullable=True)
    total_emissions_tco2e = Column(Float, nullable=True)
    total_water_kl = Column(Float, nullable=True)
    total_waste_kg = Column(Float, nullable=True)
    compliance_status = Column(String(100), nullable=True)
    
    # Raw extracted text from PDF / OCR
    extracted_text = Column(Text, nullable=True)
    
    # Full Structured JSON Data validated against Pydantic schema
    structured_data = Column(JSON, nullable=True)
    
    # Error message if any step failed
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "page_count": self.page_count,
            "status": self.status,
            "extraction_method": self.extraction_method,
            "company_name": self.company_name,
            "document_type": self.document_type,
            "reporting_period": self.reporting_period,
            "confidence_score": self.confidence_score,
            "total_energy_kwh": self.total_energy_kwh,
            "total_emissions_tco2e": self.total_emissions_tco2e,
            "total_water_kl": self.total_water_kl,
            "total_waste_kg": self.total_waste_kg,
            "compliance_status": self.compliance_status,
            "extracted_text": self.extracted_text,
            "structured_data": self.structured_data,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
