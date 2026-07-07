"""Mock reply tracking provider: the default. Makes no external API calls,
needs no OAuth credentials or secrets, and generates deterministic sample
replies for local development and tests.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from uuid import UUID

from backend.domain.entities.email_provider_connection import EmailProviderConnection
from backend.domain.enums import EmailProviderType
from backend.domain.repositories.email_provider_connection_repository import (
    EmailProviderConnectionRepository,
)
from backend.infrastructure.reply_tracking.base import (
    ProviderConnectionStatus,
    ReplySyncRequest,
    ReplyTrackingProvider,
    SyncedReplyMessage,
)

_MOCK_ACCOUNT_EMAIL = "mock@example.com"

# Rotated deterministically per known_email so re-syncing the same address
# always produces the same sample reply — real-looking test data, never a
# real message, and never sent anywhere.
_SAMPLE_BODIES = [
    "[mock] Vielen Dank fuer die Nachricht, das klingt interessant fuer uns. "
    "Koennen wir kurz telefonieren?",
    "[mock] Danke, aber aktuell kein Bedarf. Bitte nicht mehr kontaktieren.",
    "[mock] Koennten Sie mir noch mehr Details zum Preis schicken?",
    "[mock] Passt naechste Woche Dienstag 14 Uhr fuer ein kurzes Gespraech?",
    "[mock] Ich bin diese Woche im Urlaub (out of office), melde mich danach.",
    "[mock] Bitte unsubscribe mich aus diesem Verteiler, kein Interesse mehr.",
]


def _mock_message_id(email: str) -> str:
    digest = hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()[:16]
    return f"mock-reply-{digest}"


def _mock_thread_id(email: str) -> str:
    digest = hashlib.sha256(f"thread:{email.strip().lower()}".encode("utf-8")).hexdigest()[:16]
    return f"mock-thread-{digest}"


def _sample_body(email: str) -> str:
    index = int(hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest(), 16) % len(
        _SAMPLE_BODIES
    )
    return _SAMPLE_BODIES[index]


class MockReplyTrackingProvider(ReplyTrackingProvider):
    """Simulates reply reading for local development and tests.

    Generates exactly one deterministic sample reply per known email
    address passed to a sync call — no real mailbox is ever touched.
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
            message="Mock provider — no real mailbox is ever read.",
        )

    async def _ensure_connected(self, user_id: UUID) -> None:
        existing = await self._connections.get_active_for_user(
            user_id, EmailProviderType.MOCK
        )
        if existing is None:
            await self._connections.create(
                EmailProviderConnection(
                    user_id=user_id,
                    provider=EmailProviderType.MOCK,
                    external_account_email=_MOCK_ACCOUNT_EMAIL,
                    scope="mock.compose mock.readonly",
                )
            )

    def _generate(self, request: ReplySyncRequest) -> list[SyncedReplyMessage]:
        messages: list[SyncedReplyMessage] = []
        for email in request.known_emails[: request.max_messages]:
            received_at = datetime.now(UTC) - timedelta(hours=1)
            message_id = _mock_message_id(email)
            messages.append(
                SyncedReplyMessage(
                    provider_message_id=message_id,
                    provider_thread_id=_mock_thread_id(email),
                    from_email=email,
                    from_name=None,
                    to_email=None,
                    subject="Re: [mock] Ihre Anfrage",
                    body_text=_sample_body(email),
                    received_at=received_at,
                    provider_message_url=self.get_reply_provider_message_url(
                        message_id
                    ),
                )
            )
        return messages

    async def sync_replies_for_draft(
        self, user_id: UUID, request: ReplySyncRequest
    ) -> list[SyncedReplyMessage]:
        await self._ensure_connected(user_id)
        return self._generate(request)

    async def sync_replies_for_lead(
        self, user_id: UUID, request: ReplySyncRequest
    ) -> list[SyncedReplyMessage]:
        await self._ensure_connected(user_id)
        return self._generate(request)

    async def sync_recent_replies(
        self, user_id: UUID, request: ReplySyncRequest
    ) -> list[SyncedReplyMessage]:
        await self._ensure_connected(user_id)
        return self._generate(request)

    async def get_thread_messages(
        self, user_id: UUID, provider_thread_id: str
    ) -> list[SyncedReplyMessage]:
        return []

    def get_reply_provider_message_url(self, provider_message_id: str) -> str | None:
        return f"https://mock.local/messages/{provider_message_id}"
