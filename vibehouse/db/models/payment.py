import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vibehouse.db.base import BaseModel


class Payment(BaseModel):
    __tablename__ = "payments"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="usd", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    # Relationships
    project = relationship("Project", backref="payments", lazy="selectin")
    user = relationship("User", backref="payments", lazy="selectin")


class Invoice(BaseModel):
    __tablename__ = "invoices"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=True
    )
    contract_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=True
    )
    stripe_invoice_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="usd", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    due_date: Mapped[str | None] = mapped_column(String(30), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    line_items: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=list)
    hosted_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    project = relationship("Project", backref="invoices", lazy="selectin")
    vendor = relationship("Vendor", backref="invoices", lazy="selectin")
    contract = relationship("Contract", backref="invoices", lazy="selectin")
