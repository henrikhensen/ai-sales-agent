from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.database.base import Base, TimestampMixin, UUIDMixin


class RealWorldTestRunModel(UUIDMixin, TimestampMixin, Base):
    """A controlled, auditable test run against real leads/websites and,
    optionally, real LLM output — never an automatic send, external draft,
    or contact attempt."""

    __tablename__ = "real_world_test_runs"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="safe")
    lead_candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("lead_candidates.id", ondelete="SET NULL"),
        nullable=True,
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("leads.id", ondelete="SET NULL"), nullable=True
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
    workflow_run_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("workflow_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    quality_score_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("quality_scores.id", ondelete="SET NULL"),
        nullable=True,
    )
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    result_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    warnings: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    errors: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    aborted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
