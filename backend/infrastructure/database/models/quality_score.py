from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.database.base import Base, TimestampMixin, UUIDMixin


class QualityScoreModel(UUIDMixin, TimestampMixin, Base):
    """A single quality evaluation of one entity. Append-oriented — a new
    score row is created on every (re-)evaluation rather than overwriting
    the previous one, so score history is preserved."""

    __tablename__ = "quality_scores"

    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, index=True
    )
    score_total: Mapped[int] = mapped_column(Integer, nullable=False)
    score_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="acceptable", index=True
    )
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    strengths: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    weaknesses: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    warnings: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    recommended_improvements: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    compliance_flags: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    evaluated_by: Mapped[str] = mapped_column(
        String(20), nullable=False, default="system"
    )
    evaluated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    provider: Mapped[str] = mapped_column(
        String(20), nullable=False, default="rule_based"
    )
    workflow_run_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("workflow_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    email_draft_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("email_drafts.id", ondelete="SET NULL"),
        nullable=True,
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("leads.id", ondelete="SET NULL"), nullable=True
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
    )
    lead_candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("lead_candidates.id", ondelete="SET NULL"),
        nullable=True,
    )
    qualification_result_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("qualification_results.id", ondelete="SET NULL"),
        nullable=True,
    )
    outreach_queue_item_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("outreach_queue_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    reply_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("replies.id", ondelete="SET NULL"), nullable=True
    )
