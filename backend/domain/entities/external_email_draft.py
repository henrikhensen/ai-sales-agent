from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from backend.domain.enums import EmailProviderType, ExternalDraftProviderStatus


@dataclass
class ExternalEmailDraft:
    """External (Gmail/Outlook/Mock) draft metadata for one persisted
    :class:`~backend.domain.entities.email_draft.EmailDraft`.

    This only ever records that a *draft* was created at a provider (or why
    it wasn't) — ``provider_status`` never takes a value meaning "sent",
    and nothing on this entity represents automatic contact. One row per
    ``email_draft_id``; a retried attempt updates the same row rather than
    creating a new one, so this doubles as the audit trail for that draft's
    external-draft attempts.
    """

    email_draft_id: UUID
    provider: EmailProviderType
    provider_status: ExternalDraftProviderStatus = ExternalDraftProviderStatus.BLOCKED
    provider_draft_id: str | None = None
    provider_draft_url: str | None = None
    created_by_user_id: UUID | None = None
    last_error: str | None = None
    is_active: bool = True
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
