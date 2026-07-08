"""Mock Controlled Outreach Dispatch provider.

Never makes an external API call. Draft creation delegates to the existing
Email Draft Integration service (itself mock-backed by default), and
manual send is fully simulated in-process — a fake message id/URL is
generated locally, nothing is transmitted anywhere. This is the default
provider and requires no configuration or secrets whatsoever.
"""

from __future__ import annotations

import uuid
from uuid import UUID

from backend.application.integrations.email_draft_integration_service import (
    EmailDraftIntegrationService,
)
from backend.infrastructure.dispatch.base import (
    DispatchActionResult,
    DispatchProvider,
    DispatchProviderStatus,
)


class MockDispatchProvider(DispatchProvider):
    name = "mock"

    def __init__(self, email_draft_integration: EmailDraftIntegrationService) -> None:
        self._email_draft_integration = email_draft_integration

    async def get_provider_status(self, user_id: UUID) -> DispatchProviderStatus:
        return DispatchProviderStatus(
            provider=self.name,
            configured=True,
            safe_mode=True,
            connected=True,
            supports_manual_send=True,
            message=(
                "Mock dispatch provider is active. No external API call is ever "
                "made — draft creation and manual send are both simulated."
            ),
        )

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
        mock_message_id = f"mock-msg-{uuid.uuid4().hex[:16]}"
        return DispatchActionResult(
            status="mock_dispatched",
            blocked=False,
            provider_message_id=mock_message_id,
            provider_url=f"https://mock-dispatch-provider.local/messages/{mock_message_id}",
            message=(
                "Mock provider: manual send was simulated only. No real email "
                "was sent — this is a local, in-process simulation for testing "
                "the controlled dispatch flow."
            ),
        )

    async def get_dispatch_status(
        self, *, provider_message_id: str | None, provider_draft_id: str | None
    ) -> DispatchProviderStatus:
        connected = bool(provider_message_id or provider_draft_id)
        return DispatchProviderStatus(
            provider=self.name,
            configured=True,
            safe_mode=True,
            connected=connected,
            supports_manual_send=True,
            message=(
                "Mock provider record found." if connected else "No mock provider record yet."
            ),
        )
