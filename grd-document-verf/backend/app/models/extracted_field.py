from uuid import UUID, uuid4

from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TenantAuditMixin


class ExtractedField(TenantAuditMixin, Base):
    __tablename__ = "extracted_fields"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String(200), nullable=False)
    field_value: Mapped[str | None] = mapped_column(String(2000))
    confidence: Mapped[float | None] = mapped_column(Float)
