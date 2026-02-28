import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vibehouse.db.base import BaseModel


class ChangeOrder(BaseModel):
    __tablename__ = "change_orders"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    contract_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=True
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(String(50), nullable=False)
    cost_impact: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    timeline_impact_days: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(30), default="proposed", nullable=False)
    items: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=list)

    # Relationships
    project = relationship("Project", backref="change_orders", lazy="selectin")
    contract = relationship("Contract", backref="change_orders", lazy="selectin")
    requester = relationship("User", backref="change_orders_requested", lazy="selectin")
