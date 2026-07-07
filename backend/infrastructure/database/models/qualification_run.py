from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.database.base import Base, TimestampMixin, UUIDMixin


class QualificationRunModel(UUIDMixin, TimestampMixin, Base):
    """One execution of the Lead Qualification engine. Only ever scores
    and prioritizes — never sends anything or starts a Sales Workflow."""

    __tablename__ = "qualification_runs"

    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="lead_candidate"
    )
    icp_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("icp_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    offer_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("offer_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="running", index=True
    )
    started_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    qualified_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    priority_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    disqualified_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    needs_review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    average_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    warnings: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
