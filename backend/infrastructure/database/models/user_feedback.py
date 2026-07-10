from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.database.base import Base, TimestampMixin, UUIDMixin


class UserFeedbackModel(UUIDMixin, TimestampMixin, Base):
    """One human's feedback on one entity. Never triggers any automatic
    action — purely tracked signal reviewed separately by a human."""

    __tablename__ = "user_feedback"

    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, index=True
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    feedback_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    feedback_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    issue_tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    improvement_tags: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    is_blocking: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
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
    submitted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    review_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="open", index=True
    )
