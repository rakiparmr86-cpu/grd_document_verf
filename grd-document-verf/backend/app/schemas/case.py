from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.document import DetectedFileType, DocumentType, MalwareScanStatus


class CaseStatus(str, Enum):
    DRAFT = "DRAFT"
    UPLOADED = "UPLOADED"
    VALIDATING = "VALIDATING"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    PARTIALLY_PROCESSED = "PARTIALLY_PROCESSED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    HIGH_RISK = "HIGH_RISK"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class DocumentStatus(str, Enum):
    # Current public workflow. Legacy values below remain readable while old
    # database rows are migrated naturally or explicitly.
    UPLOADED = "UPLOADED"
    RECEIVED = "RECEIVED"
    QUARANTINED = "QUARANTINED"
    SCANNING = "SCANNING"
    PROCESSING = "PROCESSING"
    VALIDATED = "VALIDATED"
    OCR_RUNNING = "OCR_RUNNING"
    EXTRACTION_RUNNING = "EXTRACTION_RUNNING"
    CHECKS_RUNNING = "CHECKS_RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class CaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=250)
    reference: str | None = Field(default=None, max_length=100)


class StatusChange(BaseModel):
    status: str
    reason: str | None = Field(default=None, max_length=1000)


class StatusHistoryRead(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    from_status: str | None
    to_status: str
    reason: str | None
    changed_by: str
    changed_at: datetime


class CaseDocumentRead(BaseModel):
    id: str
    filename: str
    document_type: DocumentType
    detected_file_type: DetectedFileType
    size_bytes: int
    page_count: int
    password_protected: bool
    status: DocumentStatus
    malware_scan_status: MalwareScanStatus
    storage_available: bool
    storage_deleted_at: datetime | None = None
    observations: list[str] = Field(default_factory=list)
    issuer_or_organisation: str | None = None
    created_at: datetime
    updated_at: datetime


class CaseRead(BaseModel):
    id: str
    tenant_id: str
    name: str
    reference: str | None
    status: CaseStatus
    documents: list[CaseDocumentRead] = Field(default_factory=list)
    created_by: str
    created_at: datetime
    updated_by: str
    updated_at: datetime
