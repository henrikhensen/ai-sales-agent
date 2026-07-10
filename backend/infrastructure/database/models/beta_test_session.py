from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.database.base import Base, TimestampMixin, UUIDMixin


class BetaTestSessionModel(UUIDMixin, TimestampMixin, Base):
    """A tracked, structured round of manual beta testing."""

    __tablename__ = "beta_test_sessions"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tester_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="planned", index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    target_goal: Mapped[str | None] = mapped_column(String(500), nullable=True)
    total_workflows_tested: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    total_drafts_reviewed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    total_feedback_items: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    average_quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    blockers_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bugs_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
