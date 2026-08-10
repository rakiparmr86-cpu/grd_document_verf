from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class DocumentType(str, Enum):
    BANK_STATEMENT = "bank_statement"
    SALARY_SLIP = "salary_slip"
    VENDOR_INVOICE = "vendor_invoice"


class DetectedFileType(str, Enum):
    PDF = "pdf"
    JPEG = "jpeg"
    PNG = "png"
    TIFF = "tiff"


class MalwareScanStatus(str, Enum):
    QUEUED = "QUEUED"
    CLEAN = "CLEAN"
    INFECTED = "INFECTED"
    ERROR = "ERROR"


class DocumentRead(BaseModel):
    id: str
    case_id: str
    filename: str
    document_type: DocumentType
    detected_file_type: DetectedFileType
    size_bytes: int
    sha256: str
    page_count: int
    password_protected: bool
    status: str
    malware_scan_status: MalwareScanStatus
    storage_available: bool
    storage_deleted_at: datetime | None = None
    observations: list[str]
    issuer_or_organisation: str | None = None
    created_at: datetime
    updated_at: datetime


class DocumentStatusRead(BaseModel):
    id: str
    case_id: str
    status: str
    malware_scan_status: MalwareScanStatus
    storage_available: bool
    storage_deleted_at: datetime | None = None
    observations: list[str]
    updated_at: datetime


class DocumentUploadAccepted(BaseModel):
    document_id: str
    case_id: str
    status: str
    malware_scan_status: MalwareScanStatus
    duplicate: bool = False


class DocumentRetryAccepted(BaseModel):
    document_id: str
    case_id: str
    status: str
    malware_scan_status: MalwareScanStatus
    processing_task_id: str
