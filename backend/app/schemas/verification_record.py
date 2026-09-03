"""
schemas/verification_record.py — Pydantic Schemas for Verification Records (Step 17).
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class VerificationRecordCreate(BaseModel):
    verifier_name: Optional[str] = None
    verifier_organization: Optional[str] = None
    verification_reference: Optional[str] = None
    verification_date: Optional[datetime] = None
    verification_notes: Optional[str] = None
    verification_status: str = "NOT_SUBMITTED"


class VerificationRecordStatusUpdate(BaseModel):
    verification_status: str  # NOT_SUBMITTED, INTERNAL_REVIEW, ACCEPTED, REJECTED, EXTERNAL_VERIFICATION_PENDING, EXTERNALLY_VERIFIED
    verifier_name: Optional[str] = None
    verifier_organization: Optional[str] = None
    verification_reference: Optional[str] = None
    verification_date: Optional[datetime] = None
    verification_notes: Optional[str] = None
    note: Optional[str] = None


class VerificationRecordResponse(BaseModel):
    id: int
    project_id: int
    measurement_id: int
    verifier_name: Optional[str] = None
    verifier_organization: Optional[str] = None
    verification_reference: Optional[str] = None
    verification_date: Optional[datetime] = None
    verification_notes: Optional[str] = None
    verification_status: str
    disclaimer: str = "Senseible does not perform independent verification. External verification requires an independent verifier."
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
