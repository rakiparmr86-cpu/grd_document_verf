from uuid import UUID, uuid4

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TenantAuditMixin


class FraudSignal(TenantAuditMixin, Base):
    __tablename__ = "fraud_signals"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    verification_case_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    signal_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
