"""Schemas for the Gmail/Outlook Draft Integration.

Used both by
:class:`~backend.application.integrations.email_draft_integration_service.
EmailDraftIntegrationService` directly and as ``response_model`` for
``backend/api/v1/routes/integrations.py``, following the same pattern as
``backend/application/crm/pipeline_schemas.py`` and
``backend/application/compliance/schemas.py``.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EmailProviderInfo(BaseModel):
    """One available email draft provider and its current state."""

    provider: str
    display_name: str
    is_active_provider: bool
    requires_oauth: bool
    configured: bool
    connected: bool
    external_account_email: str | None = None


class EmailIntegrationProvidersResponse(BaseModel):
    """Response for ``GET /api/v1/integrations/email/providers``."""

    items: list[EmailProviderInfo]


class EmailIntegrationStatusResponse(BaseModel):
    """Response for ``GET /api/v1/integrations/email/status``.

    Never includes an OAuth token or client secret — only whether a
    connection is currently active.
    """

    active_provider: str
    real_drafts_enabled: bool
    safe_mode: bool
    connected: bool
    external_account_email: str | None = None
    message: str


class StartEmailProviderConnectionResponse(BaseModel):
    """Response for ``POST /api/v1/integrations/email/{provider}/connect/start``."""

    provider: str
    authorization_url: str
    message: str


class ExternalEmailDraftResponse(BaseModel):
    """External (Gmail/Outlook/Mock) draft metadata for one local draft."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email_draft_id: UUID
    provider: str
    provider_status: str
    provider_draft_id: str | None
    provider_draft_url: str | None
    created_by_user_id: UUID | None
    last_error: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CreateExternalEmailDraftResponse(BaseModel):
    """Response for ``POST /api/v1/email-drafts/{draft_id}/external-draft``.

    ``blocked=True`` means no provider call was made at all — the
    do-not-contact list or missing review approval stopped this before it
    ever reached Gmail/Outlook.
    """

    blocked: bool
    block_reason: str | None = None
    external_draft: ExternalEmailDraftResponse | None = None
    message: str


class ExternalEmailDraftStatusResponse(BaseModel):
    """Response for ``GET /api/v1/email-drafts/{draft_id}/external-draft``."""

    exists: bool
    external_draft: ExternalEmailDraftResponse | None = None
    message: str
