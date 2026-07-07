from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from backend.domain.enums import EmailProviderType, ReplyCategory, ReplyIntent, ReplySentiment


@dataclass
class Reply:
    """A single reply message read from Gmail/Outlook/Mock and stored for
    human review.

    This only ever records that a reply was *received* — nothing on this
    entity represents that a reply, or any other email, was sent
    automatically. ``body_text`` is only populated when
    ``REPLY_TRACKING_STORE_BODY_PREVIEW_ONLY=false``; otherwise only
    ``body_preview`` is kept. No attachment data is ever stored.
    ``(provider, provider_message_id)`` is unique, so re-syncing the same
    message never creates a duplicate row.
    """

    provider: EmailProviderType
    provider_message_id: str
    from_email: str
    received_at: datetime
    lead_id: UUID | None = None
    company_id: UUID | None = None
    email_draft_id: UUID | None = None
    external_draft_id: UUID | None = None
    provider_thread_id: str | None = None
    provider_message_url: str | None = None
    from_name: str | None = None
    to_email: str | None = None
    subject: str | None = None
    body_preview: str | None = None
    body_text: str | None = None
    detected_intent: ReplyIntent | None = None
    sentiment: ReplySentiment | None = None
    reply_category: ReplyCategory | None = None
    confidence_score: float | None = None
    is_read: bool = False
    is_archived: bool = False
    last_error: str | None = None
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
