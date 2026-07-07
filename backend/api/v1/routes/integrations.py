"""Gmail/Outlook Draft Integration: provider status, OAuth connection
lifecycle, and (via ``backend/api/v1/routes/email_drafts.py``) external
draft creation.

No endpoint in this module — or anywhere in this integration — can send
an email. Every endpoint either reports status or manages an OAuth
connection; the only place a draft is actually created is
``POST /api/v1/email-drafts/{draft_id}/external-draft``, which is a
conscious, one-draft-at-a-time user action, never triggered automatically.
"""

import logging

from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse

from backend.api.dependencies.auth import (
    RequireSalesOrAdminDep,
    RequireSalesReviewerOrAdminDep,
)
from backend.api.v1.dependencies import (
    EmailDraftIntegrationServiceDep,
    ReplyTrackingServiceDep,
)
from backend.application.integrations.reply_schemas import (
    ReplyIntegrationStatusResponse,
)
from backend.application.integrations.schemas import (
    EmailIntegrationProvidersResponse,
    EmailIntegrationStatusResponse,
    StartEmailProviderConnectionResponse,
)
from backend.domain.enums import EmailProviderType
from backend.infrastructure.email_integration.base import EmailIntegrationError
from backend.shared.config import get_settings

router = APIRouter(prefix="/integrations/email", tags=["email-integration"])
logger = logging.getLogger("backend.email_integration")

reply_status_router = APIRouter(prefix="/integrations/replies", tags=["replies"])


@reply_status_router.get("/status", response_model=ReplyIntegrationStatusResponse)
async def get_reply_integration_status(
    service: ReplyTrackingServiceDep,
    current_user: RequireSalesReviewerOrAdminDep,
) -> ReplyIntegrationStatusResponse:
    """Report the active reply tracking provider and the caller's connection.

    Read-only, any active admin, sales, or reviewer account. Never returns
    an OAuth token or client secret.
    """
    return await service.get_status(current_user.id)


@router.get("/status", response_model=EmailIntegrationStatusResponse)
async def get_email_integration_status(
    service: EmailDraftIntegrationServiceDep,
    current_user: RequireSalesReviewerOrAdminDep,
) -> EmailIntegrationStatusResponse:
    """Report the active email draft provider and the caller's connection.

    Read-only, any active admin, sales, or reviewer account. Never returns
    an OAuth token or client secret.
    """
    return await service.get_status(current_user.id)


@router.get("/providers", response_model=EmailIntegrationProvidersResponse)
async def list_email_integration_providers(
    service: EmailDraftIntegrationServiceDep,
    current_user: RequireSalesReviewerOrAdminDep,
) -> EmailIntegrationProvidersResponse:
    """List every supported provider (mock/gmail/outlook) and its status
    for the caller. Read-only, any active admin, sales, or reviewer account.
    """
    return await service.list_providers(current_user.id)


@router.post(
    "/{provider}/connect/start",
    response_model=StartEmailProviderConnectionResponse,
)
async def start_email_provider_connection(
    provider: EmailProviderType,
    service: EmailDraftIntegrationServiceDep,
    current_user: RequireSalesOrAdminDep,
) -> StartEmailProviderConnectionResponse:
    """Begin an OAuth authorization for ``provider``.

    Requires an active admin or sales account — connecting an account is a
    prerequisite for that same account later creating external drafts.
    Requests draft-only scope (Gmail ``gmail.compose`` / Outlook
    ``Mail.ReadWrite``) — never a send scope.
    """
    return await service.start_connection(current_user.id, provider)


@router.get("/{provider}/callback")
async def email_provider_oauth_callback(
    provider: EmailProviderType,
    service: EmailDraftIntegrationServiceDep,
    code: str = Query(...),
    state: str = Query(...),
) -> RedirectResponse:
    """OAuth redirect target for ``provider``.

    Deliberately has no auth dependency: the provider redirects the user's
    browser straight here, which cannot carry an ``Authorization`` header.
    Identity is instead recovered from the signed ``state`` parameter (see
    ``backend.infrastructure.email_integration.oauth_state``), which is
    only ever valid for 10 minutes and only for the user who started this
    specific connection attempt.
    """
    frontend_origin = get_settings().cors_allowed_origins_list[0]
    try:
        await service.handle_callback(provider, code, state)
        redirect_url = (
            f"{frontend_origin}/settings?email_integration={provider.value}"
            "&connected=true"
        )
    except EmailIntegrationError as exc:
        logger.warning("email provider oauth callback failed: %s", type(exc).__name__)
        redirect_url = (
            f"{frontend_origin}/settings?email_integration={provider.value}"
            "&connected=false"
        )
    return RedirectResponse(url=redirect_url)


@router.post("/disconnect")
async def disconnect_email_provider(
    service: EmailDraftIntegrationServiceDep,
    current_user: RequireSalesOrAdminDep,
    provider: EmailProviderType = Query(...),
) -> dict[str, str]:
    """Disconnect the caller's own connection to ``provider``.

    Requires an active admin or sales account. Idempotent — disconnecting
    an already-disconnected provider succeeds silently.
    """
    await service.disconnect(current_user.id, provider)
    return {"provider": provider.value, "status": "disconnected"}
