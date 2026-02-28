import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vibehouse.db.base import BaseModel


class ChangeOrder(BaseModel):
    __tablename__ = "change_orders"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    requested_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(String(100), nullable=False)  # scope_change, error, client_request, unforeseen
    cost_impact: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    schedule_impact_days: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")  # pending, approved, rejected, implemented
    affected_phases: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=list)
    attachments: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=list)
    approval_chain: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=list)
