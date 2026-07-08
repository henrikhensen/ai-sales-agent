from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.database.base import Base, TimestampMixin, UUIDMixin


class OnboardingStatusModel(UUIDMixin, TimestampMixin, Base):
    """One user's progress through the guided product setup checklist."""

    __tablename__ = "onboarding_statuses"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    current_step: Mapped[str] = mapped_column(
        String(50), nullable=False, default="welcome"
    )
    completed_steps: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    skipped_steps: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    is_completed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
