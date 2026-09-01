from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from backend.app.database.base import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    field_name = Column(String(100), nullable=False, index=True)
    original_ai_value = Column(JSON, nullable=True)
    corrected_value = Column(JSON, nullable=True)
    action = Column(String(50), nullable=False)  # "human_correction", "field_verified", "review_status_change"
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    notes = Column(Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "document_id": self.document_id,
            "field_name": self.field_name,
            "original_ai_value": self.original_ai_value,
            "corrected_value": self.corrected_value,
            "action": self.action,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "notes": self.notes
        }
