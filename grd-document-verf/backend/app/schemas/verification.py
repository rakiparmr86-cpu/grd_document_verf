from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.document import DocumentType


class VerificationStatus(str, Enum):
    NO_MAJOR_ANOMALY = "No Major Anomaly"
    REVIEW_RECOMMENDED = "Review Recommended"
    HIGH_RISK = "High Risk"
    UNABLE_TO_VERIFY = "Unable to Verify"
    REJECTED_BY_REVIEWER = "Rejected by Reviewer"
    VERIFIED_BY_REVIEWER = "Verified by Reviewer"


class ProcessingEvent(BaseModel):
    stage: str
    status: str
    occurred_at: datetime


class VerificationResult(BaseModel):
    case_id: str
    tenant_id: str
    created_by: str
    created_at: datetime
    updated_by: str
    updated_at: datetime
    filename: str
    document_type: DocumentType
    issuer_or_organisation: str | None = None
    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    ocr_confidence: float | None = Field(default=None, ge=0, le=1)
    validation_results: list[str] = Field(default_factory=list)
    suspicious_indicators: list[str] = Field(default_factory=list)
    duplicate_matches: list[str] = Field(default_factory=list)
    risk_score: int | None = Field(default=None, ge=0, le=100)
    risk_level: VerificationStatus
    recommended_action: str
    human_review_required: bool
    processing_history: list[ProcessingEvent]
