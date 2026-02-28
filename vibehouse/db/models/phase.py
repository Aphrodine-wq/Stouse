import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vibehouse.common.enums import PhaseType, TaskStatus
from vibehouse.db.base import BaseModel


class ProjectPhase(BaseModel):
    __tablename__ = "project_phases"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    phase_type: Mapped[PhaseType] = mapped_column(String(20), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        String(20), nullable=False, default=TaskStatus.BACKLOG
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    budget_allocated: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    budget_spent: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    order_index: Mapped[int] = mapped_column(default=0)

    # Relationships
    project = relationship("Project", back_populates="phases")
    tasks = relationship("Task", back_populates="phase", lazy="selectin")
