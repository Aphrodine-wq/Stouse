import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vibehouse.common.enums import DesignArtifactType
from vibehouse.db.base import BaseModel


class DesignArtifact(BaseModel):
    __tablename__ = "design_artifacts"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    artifact_type: Mapped[DesignArtifactType] = mapped_column(String(30), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True, default=dict)
    is_selected: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    project = relationship("Project", back_populates="design_artifacts")
