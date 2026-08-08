from uuid import UUID, uuid4

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TenantAuditMixin


class ReviewDecision(TenantAuditMixin, Base):
    __tablename__ = "review_decisions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    verification_case_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(2000))
