from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.database.base import Base, TimestampMixin, UUIDMixin


class OutreachDispatchModel(UUIDMixin, TimestampMixin, Base):
    """One controlled attempt to move a single, already-approved Outreach
    Queue item into an external draft or a manually confirmed send. Never
    a record of automatic sending."""

    __tablename__ = "outreach_dispatches"

    queue_item_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("outreach_queue_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    outreach_campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("outreach_campaigns.id", ondelete="SET NULL"),
        nullable=True,
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
    )
    email_draft_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("email_drafts.id", ondelete="SET NULL"),
        nullable=True,
    )
    external_draft_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("external_email_drafts.id", ondelete="SET NULL"),
        nullable=True,
    )
    review_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    provider: Mapped[str] = mapped_column(String(20), nullable=False, default="mock")
    dispatch_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft_only"
    )
    dispatch_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending", index=True
    )
    recipient_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    subject_snapshot: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body_preview_snapshot: Mapped[str | None] = mapped_column(String(600), nullable=True)
    final_confirmation_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    final_confirmation_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    compliance_acknowledged_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    compliance_acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    do_not_contact_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    human_review_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_draft_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
