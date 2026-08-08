from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, Enum, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TenantAuditMixin
from app.schemas.case import DocumentStatus
from app.schemas.document import DetectedFileType, DocumentType, MalwareScanStatus


class Document(TenantAuditMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("tenant_id", "sha256", name="uq_documents_tenant_sha256"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1000), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    detected_file_type: Mapped[DetectedFileType] = mapped_column(
        Enum(DetectedFileType), nullable=False
    )
    page_count: Mapped[int] = mapped_column(Integer, nullable=False)
    password_protected: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    malware_scan_status: Mapped[MalwareScanStatus] = mapped_column(
        Enum(MalwareScanStatus), nullable=False, default=MalwareScanStatus.QUEUED
    )
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType), nullable=False
    )
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), nullable=False, default=DocumentStatus.RECEIVED
    )
    issuer_or_organisation: Mapped[str | None] = mapped_column(String(300))
