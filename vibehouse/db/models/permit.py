import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vibehouse.db.base import BaseModel


class Permit(BaseModel):
    __tablename__ = "permits"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    permit_type: Mapped[str] = mapped_column(String(100), nullable=False)  # building, electrical, plumbing, mechanical, grading
    jurisdiction: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="not_applied")  # not_applied, applied, under_review, approved, denied, expired
    application_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    applied_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    approved_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    requirements: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=list)
    documents: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    fee: Mapped[float | None] = mapped_column(nullable=True)


class PermitChecklist(BaseModel):
    __tablename__ = "permit_checklists"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    jurisdiction: Mapped[str] = mapped_column(String(255), nullable=False)
    checklist_items: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    completion_percent: Mapped[float] = mapped_column(default=0.0)
