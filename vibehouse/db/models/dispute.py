import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vibehouse.common.enums import DisputeStatus, DisputeType
from vibehouse.db.base import BaseModel


class Dispute(BaseModel):
    __tablename__ = "disputes"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    filed_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    status: Mapped[DisputeStatus] = mapped_column(
        String(30), nullable=False, default=DisputeStatus.IDENTIFIED
    )
    dispute_type: Mapped[DisputeType] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    parties: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=list)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution_options: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=list)
    resolution_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    escalated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    history: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=list)

    # Relationships
    project = relationship("Project", back_populates="disputes")
    filed_by = relationship("User", back_populates="filed_disputes")
