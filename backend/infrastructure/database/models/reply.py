import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.domain.enums import (
    EmailProviderType,
    ReplyCategory,
    ReplyIntent,
    ReplySentiment,
)
from backend.infrastructure.database.base import Base, TimestampMixin, UUIDMixin


class ReplyModel(UUIDMixin, TimestampMixin, Base):
    """Reply table: messages read from Gmail/Outlook/Mock and stored for
    human review.

    ``(provider, provider_message_id)`` is unique so re-syncing the same
    message never creates a duplicate row. No attachment data is ever
    stored, and no column here ever represents that anything was sent.
    """

    __tablename__ = "replies"
    __table_args__ = (
        UniqueConstraint(
            "provider", "provider_message_id", name="uq_replies_provider_message_id"
        ),
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
        index=True,
    )
    email_draft_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("email_drafts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    external_draft_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("external_email_drafts.id", ondelete="SET NULL"),
        nullable=True,
    )
    provider: Mapped[EmailProviderType] = mapped_column(
        SAEnum(EmailProviderType, name="email_provider_type"),
        nullable=False,
    )
    provider_message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_message_url: Mapped[str | None] = mapped_column(
        String(2000), nullable=True
    )
    from_email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    from_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    to_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body_preview: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body_text: Mapped[str | None] = mapped_column(String(20_000), nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    detected_intent: Mapped[ReplyIntent | None] = mapped_column(
        SAEnum(ReplyIntent, name="reply_intent"), nullable=True
    )
    sentiment: Mapped[ReplySentiment | None] = mapped_column(
        SAEnum(ReplySentiment, name="reply_sentiment"), nullable=True
    )
    reply_category: Mapped[ReplyCategory | None] = mapped_column(
        SAEnum(ReplyCategory, name="reply_category"), nullable=True, index=True
    )
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    last_error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
