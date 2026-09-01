from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from backend.app.database.base import Base

class SustainabilityMetric(Base):
    __tablename__ = "sustainability_metrics"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    company_name = Column(String(255), nullable=True, index=True)
    metric_type = Column(String(100), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)  # energy, carbon, water, waste, financial
    value = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)
    period_start = Column(String(50), nullable=True)
    period_end = Column(String(50), nullable=True)
    source_field = Column(String(100), nullable=False)
    source_text = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    verification_status = Column(String(50), default="AI_EXTRACTED", index=True)  # AI_EXTRACTED, HUMAN_VERIFIED
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "document_id": self.document_id,
            "company_name": self.company_name,
            "metric_type": self.metric_type,
            "category": self.category,
            "value": self.value,
            "unit": self.unit,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "source_field": self.source_field,
            "source_text": self.source_text,
            "confidence": self.confidence,
            "verification_status": self.verification_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
