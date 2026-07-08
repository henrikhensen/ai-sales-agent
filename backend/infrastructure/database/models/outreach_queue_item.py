from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.database.base import Base, TimestampMixin, UUIDMixin


class OutreachQueueItemModel(UUIDMixin, TimestampMixin, Base):
    """One prioritized, campaign-scoped queue entry awaiting a
    human-triggered next step. Never a record that outreach happened."""

    __tablename__ = "outreach_queue_items"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("outreach_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
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
        index=True,
    )
    qualification_result_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("qualification_results.id", ondelete="SET NULL"),
        nullable=True,
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
    priority_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    qualification_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    qualification_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="not_fit"
    )
    queue_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="queued", index=True
    )
    recommended_outreach_angle: Mapped[str | None] = mapped_column(Text, nullable=True)
    personalization_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    compliance_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="clear"
    )
    do_not_contact_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="unknown"
    )
    duplicate_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="unknown"
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
    review_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    external_draft_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("external_email_drafts.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_action: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
