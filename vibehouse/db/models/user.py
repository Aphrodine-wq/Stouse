from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vibehouse.common.enums import UserRole
from vibehouse.db.base import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    role: Mapped[UserRole] = mapped_column(String(20), nullable=False, default=UserRole.HOMEOWNER)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    preferences: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    # Relationships
    projects = relationship("Project", back_populates="owner", lazy="selectin")
    filed_disputes = relationship("Dispute", back_populates="filed_by", lazy="selectin")
