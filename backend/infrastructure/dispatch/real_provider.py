"""Gmail/Outlook Controlled Outreach Dispatch providers.

Both providers only ever support external draft creation — delegated
entirely to the existing, already-gated Email Draft Integration service
(``backend.application.integrations.email_draft_integration_service``),
which itself only ever requests draft-creation OAuth scopes
(``gmail.compose`` / ``Mail.ReadWrite``). Neither provider ever requests a
send scope (``gmail.send`` / ``Mail.Send``), so
:meth:`send_manual_confirmed_message` always returns a clear, safe-mode
"not implemented" result here — this is a deliberate design choice, not a
bug: real sending is the first send-capable action ever introduced into
this codebase, and is intentionally never wired up for real providers,
regardless of ``OUTREACH_DISPATCH_ENABLE_REAL_SEND``. Only the mock
provider ever simulates a confirmed send. Secrets/tokens are never read,
logged, or returned by this module — connection status is reported only
as booleans/messages.
"""

from __future__ import annotations

from uuid import UUID

from backend.application.integrations.email_draft_integration_service import (
    EmailDraftIntegrationService,
)
from backend.domain.enums import EmailProviderType
from backend.domain.repositories.email_provider_connection_repository import (
    EmailProviderConnectionRepository,
)
from backend.infrastructure.dispatch.base import (
    DispatchActionResult,
    DispatchProvider,
    DispatchProviderStatus,
)
from backend.shared.config import Settings


class _RealDispatchProviderBase(DispatchProvider):
    """Shared behaviour for Gmail/Outlook: draft creation is delegated and
    may be real (governed entirely by the existing Email Integration
    settings); manual send is always safe-mode/not-implemented."""

    _provider_type: EmailProviderType

    def __init__(
        self,
        email_draft_integration: EmailDraftIntegrationService,
        connections: EmailProviderConnectionRepository,
        settings: Settings,
    ) -> None:
        self._email_draft_integration = email_draft_integration
        self._connections = connections
        self._settings = settings

    async def get_provider_status(self, user_id: UUID) -> DispatchProviderStatus:
        connection = await self._connections.get_active_for_user(
            user_id, self._provider_type
        )
        configured = self._is_configured()
        return DispatchProviderStatus(
            provider=self.name,
            configured=configured,
            safe_mode=True,
            connected=connection is not None,
            supports_manual_send=False,
            message=(
                f"'{self.name}' draft creation follows the existing Email "
                "Integration settings (may be real once configured). Manual "
                "send is not implemented for this provider — no send scope "
                "(e.g. gmail.send/Mail.Send) is ever requested, so real "
                "sending is unavailable regardless of "
                "OUTREACH_DISPATCH_ENABLE_REAL_SEND."
            ),
        )

    def _is_configured(self) -> bool:
        raise NotImplementedError

    async def create_external_draft(
        self, *, user_id: UUID, email_draft_id: UUID
    ) -> DispatchActionResult:
        response = await self._email_draft_integration.create_external_draft(
            user_id, email_draft_id
        )
        if response.blocked:
            return DispatchActionResult(
                status="blocked", blocked=True, message=response.message
            )
        draft = response.external_draft
        return DispatchActionResult(
            status="external_draft_created",
            blocked=False,
            provider_draft_id=draft.provider_draft_id if draft else None,
            provider_url=draft.provider_draft_url if draft else None,
            message=response.message,
        )

    async def send_manual_confirmed_message(
        self, *, user_id: UUID, email_draft_id: UUID, dispatch_id: UUID
    ) -> DispatchActionResult:
        return DispatchActionResult(
            status="blocked",
            blocked=True,
            message=(
                f"Real send is not implemented for provider '{self.name}'. "
                "Sending a real email would require requesting a send scope "
                "that this integration deliberately never asks for. Only "
                "external draft creation is supported for this provider — "
                "use the mock provider to test the manual-send flow."
            ),
        )

    async def get_dispatch_status(
        self, *, provider_message_id: str | None, provider_draft_id: str | None
    ) -> DispatchProviderStatus:
        return DispatchProviderStatus(
            provider=self.name,
            configured=self._is_configured(),
            safe_mode=True,
            connected=bool(provider_draft_id),
            supports_manual_send=False,
            message="Status is derived from the stored dispatch record only.",
        )


class GmailDispatchProvider(_RealDispatchProviderBase):
    name = "gmail"
    _provider_type = EmailProviderType.GMAIL

    def _is_configured(self) -> bool:
        return bool(
            self._settings.google_client_id
            and self._settings.google_client_secret
            and self._settings.email_token_encryption_key
        )


class OutlookDispatchProvider(_RealDispatchProviderBase):
    name = "outlook"
    _provider_type = EmailProviderType.OUTLOOK

    def _is_configured(self) -> bool:
        return bool(
            self._settings.microsoft_client_id
            and self._settings.microsoft_client_secret
            and self._settings.email_token_encryption_key
        )
