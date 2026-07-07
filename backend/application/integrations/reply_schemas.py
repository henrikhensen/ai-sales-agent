"""Schemas for Reply Inbox / Reply Tracking.

Used both by
:class:`~backend.application.integrations.reply_tracking_service.
ReplyTrackingService` directly and as ``response_model`` for
``backend/api/v1/routes/replies.py``, following the same pattern as
``backend/application/integrations/schemas.py`` (the Gmail/Outlook draft
integration).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReplyResponse(BaseModel):
    """A single reply message, stored for human review.

    Never includes an OAuth token, client secret, or attachment data.
    ``recommended_pipeline_status`` and ``compliance_warning`` are computed
    from ``reply_category`` — neither is ever applied automatically; both
    are shown so a human can act on them deliberately (e.g. via the
    existing ``PATCH /crm/leads/{lead_id}/pipeline-status`` endpoint).
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_id: UUID | None
    company_id: UUID | None
    email_draft_id: UUID | None
    external_draft_id: UUID | None
    provider: str
    provider_message_id: str
    provider_thread_id: str | None
    provider_message_url: str | None
    from_email: str
    from_name: str | None
    to_email: str | None
    subject: str | None
    body_preview: str | None
    body_text: str | None
    received_at: datetime
    detected_intent: str | None
    sentiment: str | None
    reply_category: str | None
    confidence_score: float | None
    is_read: bool
    is_archived: bool
    last_error: str | None
    created_at: datetime
    updated_at: datetime
    recommended_pipeline_status: str | None = None
    compliance_warning: str | None = None


class ReplyListResponse(BaseModel):
    """Response for ``GET /api/v1/replies`` and
    ``GET /api/v1/leads/{lead_id}/replies``."""

    items: list[ReplyResponse]
    limit: int
    offset: int


class SyncRepliesResponse(BaseModel):
    """Response for every ``.../replies/sync*`` endpoint.

    ``status`` is one of :class:`~backend.domain.enums.ReplySyncStatus` —
    describes the sync attempt itself, never a "sent" outcome (there is
    none: this integration only ever reads).
    """

    status: str
    provider: str
    synced_count: int
    new_count: int
    duplicate_count: int
    do_not_contact_signals: int
    message: str
    error: str | None = None
    replies: list[ReplyResponse] = []


class ReplyIntegrationStatusResponse(BaseModel):
    """Response for ``GET /api/v1/integrations/replies/status``.

    Never includes an OAuth token or client secret — only whether a
    connection with sufficient read permission is currently active.
    """

    active_provider: str
    real_reads_enabled: bool
    safe_mode: bool
    connected: bool
    external_account_email: str | None = None
    message: str
