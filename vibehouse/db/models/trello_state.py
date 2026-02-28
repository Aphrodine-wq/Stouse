import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vibehouse.db.base import BaseModel


class TrelloSyncState(BaseModel):
    __tablename__ = "trello_sync_state"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, unique=True, index=True
    )
    board_id: Mapped[str] = mapped_column(String(100), nullable=False)
    last_sync: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    state_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sync_status: Mapped[str] = mapped_column(String(20), default="idle")
    board_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    # Relationships
    project = relationship("Project", back_populates="trello_sync_state")
