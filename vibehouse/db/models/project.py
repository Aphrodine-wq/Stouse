import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vibehouse.common.enums import ProjectStatus
from vibehouse.db.base import BaseModel


class Project(BaseModel):
    __tablename__ = "projects"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[ProjectStatus] = mapped_column(
        String(20), nullable=False, default=ProjectStatus.DRAFT
    )
    vibe_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    location_lat: Mapped[float | None] = mapped_column(nullable=True)
    location_lng: Mapped[float | None] = mapped_column(nullable=True)
    budget: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    budget_spent: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    trello_board_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    owner = relationship("User", back_populates="projects", lazy="selectin")
    phases = relationship("ProjectPhase", back_populates="project", lazy="selectin")
    design_artifacts = relationship("DesignArtifact", back_populates="project", lazy="selectin")
    contracts = relationship("Contract", back_populates="project", lazy="selectin")
    disputes = relationship("Dispute", back_populates="project", lazy="selectin")
    daily_reports = relationship("DailyReport", back_populates="project", lazy="selectin")
    trello_sync_state = relationship(
        "TrelloSyncState", back_populates="project", uselist=False, lazy="selectin"
    )
