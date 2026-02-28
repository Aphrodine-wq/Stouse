import uuid
from decimal import Decimal

from sqlalchemy import Boolean, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vibehouse.db.base import BaseModel


class Vendor(BaseModel):
    __tablename__ = "vendors"

    company_name: Mapped[str] = mapped_column(String(500), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    trades: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=list)
    license_info: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    insurance_info: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    total_projects: Mapped[int] = mapped_column(Integer, default=0)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    location_lat: Mapped[float | None] = mapped_column(nullable=True)
    location_lng: Mapped[float | None] = mapped_column(nullable=True)
    service_radius_miles: Mapped[int] = mapped_column(Integer, default=50)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    contracts = relationship("Contract", back_populates="vendor", lazy="selectin")
    assigned_tasks = relationship("Task", back_populates="assignee", lazy="selectin")
    bids = relationship("Bid", back_populates="vendor", lazy="selectin")


class Bid(BaseModel):
    __tablename__ = "bids"

    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    scope_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    timeline_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="submitted")
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    # Relationships
    vendor = relationship("Vendor", back_populates="bids")
