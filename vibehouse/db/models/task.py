import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vibehouse.common.enums import TaskStatus
from vibehouse.db.base import BaseModel


class Task(BaseModel):
    __tablename__ = "tasks"

    phase_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project_phases.id"), nullable=False, index=True
    )
    trello_card_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        String(20), nullable=False, default=TaskStatus.BACKLOG
    )
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=True
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    dependencies: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=list)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True, default=dict)
    order_index: Mapped[int] = mapped_column(default=0)

    # Relationships
    phase = relationship("ProjectPhase", back_populates="tasks")
    assignee = relationship("Vendor", back_populates="assigned_tasks", lazy="selectin")
