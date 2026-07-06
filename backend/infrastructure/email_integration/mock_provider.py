"""Mock email draft provider: the default. Makes no external API calls,
needs no OAuth credentials or secrets, and is safe to use in any
environment.
"""

from __future__ import annotations

import uuid
from uuid import UUID

from backend.domain.entities.email_provider_connection import EmailProviderConnection
from backend.domain.enums import EmailProviderType, ExternalDraftProviderStatus
from backend.domain.repositories.email_provider_connection_repository import (
    EmailProviderConnectionRepository,
)
from backend.infrastructure.email_integration.base import (
    EmailDraftProvider,
    ExternalDraftRequest,
    ExternalDraftResult,
    OAuthStartResult,
    ProviderConnectionStatus,
)

_MOCK_ACCOUNT_EMAIL = "mock@example.com"


class MockEmailDraftProvider(EmailDraftProvider):
    """Simulates draft creation for local development and tests.

    "Connecting" succeeds immediately with no real OAuth roundtrip and no
    external account is ever touched — the connection is still persisted
    via the same repository real providers use, so its status behaves
    consistently across requests.
    """

    name = "mock"

    def __init__(self, connections: EmailProviderConnectionRepository) -> None:
        self._connections = connections

    async def get_provider_status(self, user_id: UUID) -> ProviderConnectionStatus:
        connection = await self._connections.get_active_for_user(
            user_id, EmailProviderType.MOCK
        )
        return ProviderConnectionStatus(
            provider=self.name,
            connected=connection is not None,
            external_account_email=(
                connection.external_account_email if connection else None
            ),
            message="Mock provider — no real Gmail/Outlook account is ever touched.",
        )

    async def start_oauth_connection(
        self, user_id: UUID, redirect_uri: str
    ) -> OAuthStartResult:
        existing = await self._connections.get_active_for_user(
            user_id, EmailProviderType.MOCK
        )
        if existing is None:
            await self._connections.create(
                EmailProviderConnection(
                    user_id=user_id,
                    provider=EmailProviderType.MOCK,
                    external_account_email=_MOCK_ACCOUNT_EMAIL,
                    scope="mock.compose",
                )
            )
        return OAuthStartResult(
            authorization_url="mock://oauth/authorize", state="mock-state"
        )

    async def handle_oauth_callback(
        self, user_id: UUID, code: str, state: str, redirect_uri: str
    ) -> ProviderConnectionStatus:
        return await self.get_provider_status(user_id)

    async def disconnect_provider(self, user_id: UUID) -> None:
        await self._connections.deactivate_for_user(user_id, EmailProviderType.MOCK)

    async def create_external_draft(
        self, user_id: UUID, request: ExternalDraftRequest
    ) -> ExternalDraftResult:
        draft_id = f"mock-draft-{uuid.uuid4().hex[:12]}"
        return ExternalDraftResult(
            provider=self.name,
            status=ExternalDraftProviderStatus.MOCK_CREATED,
            provider_draft_id=draft_id,
            provider_draft_url=f"https://mock.local/drafts/{draft_id}",
            message="Mock draft created — no real Gmail/Outlook draft exists.",
        )

    async def get_external_draft_status(
        self, user_id: UUID, provider_draft_id: str
    ) -> ExternalDraftResult:
        return ExternalDraftResult(
            provider=self.name,
            status=ExternalDraftProviderStatus.MOCK_CREATED,
            provider_draft_id=provider_draft_id,
            provider_draft_url=f"https://mock.local/drafts/{provider_draft_id}",
            message="Mock draft.",
        )
