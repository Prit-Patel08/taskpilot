from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ApplicationLimit(Base):
    __tablename__ = "application_limits"
    __table_args__ = (
        Index("ix_application_limits_user_id", "user_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        primary_key=True,
        nullable=False,
    )
    date: Mapped[date] = mapped_column(
        Date,
        primary_key=True,
        nullable=False,
    )
    applications_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
