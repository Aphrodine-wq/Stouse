import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vibehouse.common.enums import ContractStatus
from vibehouse.db.base import BaseModel


class Contract(BaseModel):
    __tablename__ = "contracts"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False, index=True
    )
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    status: Mapped[ContractStatus] = mapped_column(
        String(20), nullable=False, default=ContractStatus.DRAFT
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    milestones: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=list)
    terms: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    # Relationships
    project = relationship("Project", back_populates="contracts")
    vendor = relationship("Vendor", back_populates="contracts")
