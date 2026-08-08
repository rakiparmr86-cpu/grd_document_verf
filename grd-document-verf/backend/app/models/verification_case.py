from uuid import UUID, uuid4

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TenantAuditMixin
from app.schemas.case import CaseStatus


class VerificationCase(TenantAuditMixin, Base):
    __tablename__ = "verification_cases"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(100), index=True)
    status: Mapped[CaseStatus] = mapped_column(
        Enum(CaseStatus), nullable=False, default=CaseStatus.DRAFT
    )
