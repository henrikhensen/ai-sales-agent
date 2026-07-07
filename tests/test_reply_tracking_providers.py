"""Unit tests for the reply tracking providers.

Mock provider tests exercise real behavior end-to-end (in-memory
repository, no mocking needed). Gmail/Outlook tests monkeypatch
``httpx.AsyncClient`` so no real network call is ever made.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from backend.domain.entities.email_provider_connection import EmailProviderConnection
from backend.domain.enums import EmailProviderType
from backend.infrastructure.email_integration.token_crypto import TokenCipher
from backend.infrastructure.reply_tracking.base import (
    ReplySyncRequest,
    ReplyTrackingAuthError,
    ReplyTrackingConfigError,
    ReplyTrackingPermissionError,
    ReplyTrackingRateLimitError,
)
from backend.infrastructure.reply_tracking.gmail_provider import (
    GmailReplyTrackingProvider,
)
from backend.infrastructure.reply_tracking.mock_provider import (
    MockReplyTrackingProvider,
)
from backend.infrastructure.reply_tracking.outlook_provider import (
    OutlookReplyTrackingProvider,
)
from tests.conftest import FakeEmailProviderConnectionRepository

_SECRET_CLIENT_SECRET = "sk-super-secret-oauth-client-secret"


# -- Mock provider --------------------------------------------------------------


async def test_mock_provider_generates_a_reply_per_known_email():
    provider = MockReplyTrackingProvider(FakeEmailProviderConnectionRepository())
    request = ReplySyncRequest(known_emails=["a@example.com", "b@example.com"])

    messages = await provider.sync_recent_replies(uuid.uuid4(), request)

    assert len(messages) == 2
    assert {m.from_email for m in messages} == {"a@example.com", "b@example.com"}
    for message in messages:
        assert message.provider_message_id
        assert message.provider_message_url is not None


async def test_mock_provider_is_deterministic_across_calls():
    provider = MockReplyTrackingProvider(FakeEmailProviderConnectionRepository())
    request = ReplySyncRequest(known_emails=["stable@example.com"])

    first = await provider.sync_recent_replies(uuid.uuid4(), request)
    second = await provider.sync_recent_replies(uuid.uuid4(), request)

    assert first[0].provider_message_id == second[0].provider_message_id
    assert first[0].body_text == second[0].body_text


async def test_mock_provider_respects_max_messages():
    provider = MockReplyTrackingProvider(FakeEmailProviderConnectionRepository())
    request = ReplySyncRequest(
        known_emails=["a@example.com", "b@example.com", "c@example.com"],
        max_messages=2,
    )

    messages = await provider.sync_recent_replies(uuid.uuid4(), request)

    assert len(messages) == 2


async def test_mock_provider_connects_on_first_sync():
    connections = FakeEmailProviderConnectionRepository()
    provider = MockReplyTrackingProvider(connections)
    user_id = uuid.uuid4()

    await provider.sync_recent_replies(user_id, ReplySyncRequest(known_emails=[]))

    status = await provider.get_provider_status(user_id)
    assert status.connected is True


def test_mock_provider_never_has_a_send_method():
    provider = MockReplyTrackingProvider(FakeEmailProviderConnectionRepository())
    assert not hasattr(provider, "send_email")
    assert not hasattr(provider, "reply_email")
    assert not hasattr(provider, "send_reply")


# -- Gmail provider ---------------------------------------------------------------


def test_gmail_provider_rejects_missing_client_id():
    with pytest.raises(ReplyTrackingConfigError):
        GmailReplyTrackingProvider(
            client_id=None,
            client_secret=_SECRET_CLIENT_SECRET,
            connections=FakeEmailProviderConnectionRepository(),
            token_cipher=TokenCipher("test-key"),
        )


async def test_gmail_provider_requires_a_connection_before_syncing():
    provider = GmailReplyTrackingProvider(
        client_id="client-id",
        client_secret=_SECRET_CLIENT_SECRET,
        connections=FakeEmailProviderConnectionRepository(),
        token_cipher=TokenCipher("test-key"),
    )
    with pytest.raises(ReplyTrackingAuthError):
        await provider.sync_recent_replies(
            uuid.uuid4(), ReplySyncRequest(known_emails=["lead@example.com"])
        )


async def test_gmail_provider_rejects_draft_only_scope_with_permission_error():
    """A connection made for draft-only use (gmail.compose) must not be
    usable for reply reading — this is exactly the "fehlende Berechtigung /
    Scope" error case Aufgabe 6 requires.
    """
    connections = FakeEmailProviderConnectionRepository()
    user_id = uuid.uuid4()
    await connections.create(
        EmailProviderConnection(
            user_id=user_id,
            provider=EmailProviderType.GMAIL,
            encrypted_access_token=TokenCipher("test-key").encrypt("tok"),
            scope="https://www.googleapis.com/auth/gmail.compose",
        )
    )
    provider = GmailReplyTrackingProvider(
        client_id="client-id",
        client_secret=_SECRET_CLIENT_SECRET,
        connections=connections,
        token_cipher=TokenCipher("test-key"),
    )

    with pytest.raises(ReplyTrackingPermissionError):
        await provider.sync_recent_replies(
            user_id, ReplySyncRequest(known_emails=["lead@example.com"])
        )


class _FakeResponse:
    def __init__(self, status_code: int, json_data: dict | None = None):
        self.status_code = status_code
        self._json_data = json_data or {}

    def json(self) -> dict:
        return self._json_data


class _FakeAsyncClient:
    """Holds a *shared, mutable* reference to the responses queue — the
    Gmail provider opens a fresh ``httpx.AsyncClient()`` per request (one
    for listing messages, one per message detail), so every instance
    created during a single patched test must pop from the same queue in
    order, not each get its own copy.
    """

    def __init__(self, responses: list):
        self._responses = responses

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, **kwargs):
        return self._next()

    async def get(self, url, **kwargs):
        return self._next()

    def _next(self):
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _patch_client(monkeypatch, module, responses: list):
    monkeypatch.setattr(
        f"{module}.httpx.AsyncClient", lambda **kwargs: _FakeAsyncClient(responses)
    )


async def _connected_gmail_provider(connections, user_id):
    await connections.create(
        EmailProviderConnection(
            user_id=user_id,
            provider=EmailProviderType.GMAIL,
            encrypted_access_token=TokenCipher("test-key").encrypt("tok"),
            scope="https://www.googleapis.com/auth/gmail.readonly",
        )
    )
    return GmailReplyTrackingProvider(
        client_id="client-id",
        client_secret=_SECRET_CLIENT_SECRET,
        connections=connections,
        token_cipher=TokenCipher("test-key"),
    )


async def test_gmail_sync_reads_messages_and_maps_fields(monkeypatch):
    connections = FakeEmailProviderConnectionRepository()
    user_id = uuid.uuid4()
    provider = await _connected_gmail_provider(connections, user_id)

    _patch_client(
        monkeypatch,
        "backend.infrastructure.reply_tracking.gmail_provider",
        [
            _FakeResponse(200, {"messages": [{"id": "msg-1"}]}),
            _FakeResponse(
                200,
                {
                    "id": "msg-1",
                    "threadId": "thread-1",
                    "internalDate": "1700000000000",
                    "snippet": "hi there",
                    "payload": {
                        "headers": [
                            {"name": "From", "value": "Lead <lead@example.com>"},
                            {"name": "Subject", "value": "Re: Hello"},
                        ],
                        "mimeType": "text/plain",
                        "body": {},
                    },
                },
            ),
        ],
    )

    messages = await provider.sync_recent_replies(
        user_id, ReplySyncRequest(known_emails=["lead@example.com"])
    )

    assert len(messages) == 1
    assert messages[0].from_email == "lead@example.com"
    assert messages[0].provider_thread_id == "thread-1"
    assert messages[0].subject == "Re: Hello"
    assert messages[0].body_text == "hi there"


async def test_gmail_sync_maps_rate_limit_error(monkeypatch):
    connections = FakeEmailProviderConnectionRepository()
    user_id = uuid.uuid4()
    provider = await _connected_gmail_provider(connections, user_id)

    _patch_client(
        monkeypatch,
        "backend.infrastructure.reply_tracking.gmail_provider",
        [_FakeResponse(429, {})],
    )

    with pytest.raises(ReplyTrackingRateLimitError):
        await provider.sync_recent_replies(
            user_id, ReplySyncRequest(known_emails=["lead@example.com"])
        )


# -- Outlook provider ---------------------------------------------------------------


def test_outlook_provider_rejects_missing_client_id():
    with pytest.raises(ReplyTrackingConfigError):
        OutlookReplyTrackingProvider(
            client_id=None,
            client_secret=_SECRET_CLIENT_SECRET,
            tenant_id="common",
            connections=FakeEmailProviderConnectionRepository(),
            token_cipher=TokenCipher("test-key"),
        )


async def test_outlook_provider_requires_a_connection_before_syncing():
    provider = OutlookReplyTrackingProvider(
        client_id="client-id",
        client_secret=_SECRET_CLIENT_SECRET,
        tenant_id="common",
        connections=FakeEmailProviderConnectionRepository(),
        token_cipher=TokenCipher("test-key"),
    )
    with pytest.raises(ReplyTrackingAuthError):
        await provider.sync_recent_replies(
            uuid.uuid4(), ReplySyncRequest(known_emails=["lead@example.com"])
        )


async def test_outlook_mail_readwrite_scope_already_grants_read_access():
    """Unlike Gmail's compose-only scope, Outlook's existing draft
    connection (Mail.ReadWrite) already includes read access."""
    connections = FakeEmailProviderConnectionRepository()
    user_id = uuid.uuid4()
    await connections.create(
        EmailProviderConnection(
            user_id=user_id,
            provider=EmailProviderType.OUTLOOK,
            encrypted_access_token=TokenCipher("test-key").encrypt("tok"),
            scope="https://graph.microsoft.com/Mail.ReadWrite offline_access",
        )
    )
    provider = OutlookReplyTrackingProvider(
        client_id="client-id",
        client_secret=_SECRET_CLIENT_SECRET,
        tenant_id="common",
        connections=connections,
        token_cipher=TokenCipher("test-key"),
    )

    status = await provider.get_provider_status(user_id)
    assert status.connected is True


async def test_outlook_sync_reads_messages_and_maps_fields(monkeypatch):
    connections = FakeEmailProviderConnectionRepository()
    user_id = uuid.uuid4()
    await connections.create(
        EmailProviderConnection(
            user_id=user_id,
            provider=EmailProviderType.OUTLOOK,
            encrypted_access_token=TokenCipher("test-key").encrypt("tok"),
            scope="https://graph.microsoft.com/Mail.ReadWrite",
        )
    )
    provider = OutlookReplyTrackingProvider(
        client_id="client-id",
        client_secret=_SECRET_CLIENT_SECRET,
        tenant_id="common",
        connections=connections,
        token_cipher=TokenCipher("test-key"),
    )

    _patch_client(
        monkeypatch,
        "backend.infrastructure.reply_tracking.outlook_provider",
        [
            _FakeResponse(
                200,
                {
                    "value": [
                        {
                            "id": "msg-1",
                            "conversationId": "conv-1",
                            "subject": "Re: Hello",
                            "from": {
                                "emailAddress": {
                                    "address": "lead@example.com",
                                    "name": "Lead",
                                }
                            },
                            "toRecipients": [
                                {"emailAddress": {"address": "sales@example.com"}}
                            ],
                            "receivedDateTime": "2024-01-01T12:00:00Z",
                            "body": {"content": "hi there"},
                            "webLink": "https://outlook.office.com/mail/x",
                        }
                    ]
                },
            )
        ],
    )

    messages = await provider.sync_recent_replies(
        user_id, ReplySyncRequest(known_emails=["lead@example.com"])
    )

    assert len(messages) == 1
    assert messages[0].from_email == "lead@example.com"
    assert messages[0].provider_thread_id == "conv-1"
    assert messages[0].body_text == "hi there"
    assert messages[0].provider_message_url == "https://outlook.office.com/mail/x"


def test_outlook_provider_never_has_a_send_method():
    provider = OutlookReplyTrackingProvider(
        client_id="client-id",
        client_secret=_SECRET_CLIENT_SECRET,
        tenant_id="common",
        connections=FakeEmailProviderConnectionRepository(),
        token_cipher=TokenCipher("test-key"),
    )
    assert not hasattr(provider, "send_email")
    assert not hasattr(provider, "reply_email")
    assert not hasattr(provider, "send_reply")
