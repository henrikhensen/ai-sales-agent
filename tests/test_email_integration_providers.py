"""Unit tests for the email draft providers.

Mock provider tests exercise real behavior end-to-end (in-memory
repository, no mocking needed). Gmail/Outlook tests monkeypatch
``httpx.AsyncClient`` so no real network call is ever made — mirroring
tests/test_anthropic_provider.py's approach for the LLM provider.
"""

import uuid

import pytest

from backend.domain.enums import EmailProviderType, ExternalDraftProviderStatus
from backend.infrastructure.email_integration.base import (
    EmailIntegrationAuthError,
    EmailIntegrationConfigError,
    EmailIntegrationConnectionError,
    EmailIntegrationProviderError,
    EmailIntegrationRateLimitError,
    EmailIntegrationTimeoutError,
    ExternalDraftRequest,
)
from backend.infrastructure.email_integration.gmail_provider import GmailDraftProvider
from backend.infrastructure.email_integration.mock_provider import (
    MockEmailDraftProvider,
)
from backend.infrastructure.email_integration.outlook_provider import (
    OutlookDraftProvider,
)
from backend.infrastructure.email_integration.token_crypto import TokenCipher
from tests.conftest import FakeEmailProviderConnectionRepository

_SECRET_CLIENT_SECRET = "sk-super-secret-oauth-client-secret"


# -- Mock provider --------------------------------------------------------------


async def test_mock_provider_status_starts_disconnected():
    provider = MockEmailDraftProvider(FakeEmailProviderConnectionRepository())
    status = await provider.get_provider_status(uuid.uuid4())
    assert status.connected is False


async def test_mock_provider_connect_then_status_connected():
    provider = MockEmailDraftProvider(FakeEmailProviderConnectionRepository())
    user_id = uuid.uuid4()

    await provider.start_oauth_connection(user_id, "http://localhost/callback")
    status = await provider.get_provider_status(user_id)

    assert status.connected is True
    assert status.external_account_email == "mock@example.com"


async def test_mock_provider_disconnect_then_status_disconnected():
    provider = MockEmailDraftProvider(FakeEmailProviderConnectionRepository())
    user_id = uuid.uuid4()
    await provider.start_oauth_connection(user_id, "http://localhost/callback")

    await provider.disconnect_provider(user_id)
    status = await provider.get_provider_status(user_id)

    assert status.connected is False


async def test_mock_provider_creates_a_draft_without_a_prior_connection():
    provider = MockEmailDraftProvider(FakeEmailProviderConnectionRepository())
    result = await provider.create_external_draft(
        uuid.uuid4(),
        ExternalDraftRequest(subject="Hallo", body="Testinhalt"),
    )

    assert result.status == ExternalDraftProviderStatus.MOCK_CREATED
    assert result.provider_draft_id is not None
    assert result.provider_draft_url is not None
    assert result.status != "sent"


async def test_mock_provider_never_returns_a_sent_status():
    provider = MockEmailDraftProvider(FakeEmailProviderConnectionRepository())
    result = await provider.create_external_draft(
        uuid.uuid4(), ExternalDraftRequest(subject="s", body="b")
    )
    assert "sent" not in result.status.value


# -- Gmail provider ---------------------------------------------------------------


def test_gmail_provider_rejects_missing_client_id():
    with pytest.raises(EmailIntegrationConfigError):
        GmailDraftProvider(
            client_id=None,
            client_secret=_SECRET_CLIENT_SECRET,
            connections=FakeEmailProviderConnectionRepository(),
            token_cipher=TokenCipher("test-key"),
        )


def test_gmail_provider_rejects_missing_client_secret():
    with pytest.raises(EmailIntegrationConfigError):
        GmailDraftProvider(
            client_id="client-id",
            client_secret=None,
            connections=FakeEmailProviderConnectionRepository(),
            token_cipher=TokenCipher("test-key"),
        )


async def test_gmail_provider_requires_a_connection_before_creating_a_draft():
    provider = GmailDraftProvider(
        client_id="client-id",
        client_secret=_SECRET_CLIENT_SECRET,
        connections=FakeEmailProviderConnectionRepository(),
        token_cipher=TokenCipher("test-key"),
    )
    with pytest.raises(EmailIntegrationAuthError):
        await provider.create_external_draft(
            uuid.uuid4(), ExternalDraftRequest(subject="s", body="b")
        )


class _FakeResponse:
    def __init__(self, status_code: int, json_data: dict | None = None):
        self.status_code = status_code
        self._json_data = json_data or {}

    def json(self) -> dict:
        return self._json_data


class _FakeAsyncClient:
    """Stand-in for ``httpx.AsyncClient`` returning canned responses in order."""

    def __init__(self, responses: list):
        self._responses = list(responses)

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


async def test_gmail_oauth_callback_stores_encrypted_tokens_and_never_leaks_secret(
    monkeypatch,
):
    connections = FakeEmailProviderConnectionRepository()
    provider = GmailDraftProvider(
        client_id="client-id",
        client_secret=_SECRET_CLIENT_SECRET,
        connections=connections,
        token_cipher=TokenCipher("test-key"),
    )
    _patch_client(
        monkeypatch,
        "backend.infrastructure.email_integration.gmail_provider",
        [
            _FakeResponse(
                200,
                {
                    "access_token": "real-access-token",
                    "refresh_token": "real-refresh-token",
                    "expires_in": 3600,
                },
            )
        ],
    )
    user_id = uuid.uuid4()

    status = await provider.handle_oauth_callback(
        user_id, "auth-code", "state", "http://localhost/callback"
    )

    assert status.connected is True
    connection = await connections.get_active_for_user(user_id, EmailProviderType.GMAIL)
    assert connection.encrypted_access_token != "real-access-token"
    assert "real-access-token" not in (connection.encrypted_access_token or "")
    assert _SECRET_CLIENT_SECRET not in (connection.encrypted_access_token or "")


async def test_gmail_create_draft_success(monkeypatch):
    connections = FakeEmailProviderConnectionRepository()
    provider = GmailDraftProvider(
        client_id="client-id",
        client_secret=_SECRET_CLIENT_SECRET,
        connections=connections,
        token_cipher=TokenCipher("test-key"),
    )
    _patch_client(
        monkeypatch,
        "backend.infrastructure.email_integration.gmail_provider",
        [_FakeResponse(200, {"access_token": "tok", "expires_in": 3600})],
    )
    user_id = uuid.uuid4()
    await provider.handle_oauth_callback(user_id, "code", "state", "http://x/callback")

    _patch_client(
        monkeypatch,
        "backend.infrastructure.email_integration.gmail_provider",
        [_FakeResponse(200, {"id": "draft-123"})],
    )
    result = await provider.create_external_draft(
        user_id, ExternalDraftRequest(subject="Hallo", body="Testinhalt")
    )

    assert result.status == ExternalDraftProviderStatus.CREATED
    assert result.provider_draft_id == "draft-123"
    assert result.provider_draft_url is not None


@pytest.mark.parametrize(
    "status_code,expected_exception",
    [
        (401, EmailIntegrationAuthError),
        (429, EmailIntegrationRateLimitError),
        (500, EmailIntegrationProviderError),
    ],
)
async def test_gmail_create_draft_maps_error_status_codes(
    monkeypatch, status_code, expected_exception
):
    connections = FakeEmailProviderConnectionRepository()
    provider = GmailDraftProvider(
        client_id="client-id",
        client_secret=_SECRET_CLIENT_SECRET,
        connections=connections,
        token_cipher=TokenCipher("test-key"),
    )
    _patch_client(
        monkeypatch,
        "backend.infrastructure.email_integration.gmail_provider",
        [_FakeResponse(200, {"access_token": "tok", "expires_in": 3600})],
    )
    user_id = uuid.uuid4()
    await provider.handle_oauth_callback(user_id, "code", "state", "http://x/callback")

    _patch_client(
        monkeypatch,
        "backend.infrastructure.email_integration.gmail_provider",
        [_FakeResponse(status_code, {})],
    )
    with pytest.raises(expected_exception):
        await provider.create_external_draft(
            user_id, ExternalDraftRequest(subject="s", body="b")
        )


async def test_gmail_create_draft_maps_timeout_and_connection_errors(monkeypatch):
    import httpx

    connections = FakeEmailProviderConnectionRepository()
    provider = GmailDraftProvider(
        client_id="client-id",
        client_secret=_SECRET_CLIENT_SECRET,
        connections=connections,
        token_cipher=TokenCipher("test-key"),
    )
    _patch_client(
        monkeypatch,
        "backend.infrastructure.email_integration.gmail_provider",
        [_FakeResponse(200, {"access_token": "tok", "expires_in": 3600})],
    )
    user_id = uuid.uuid4()
    await provider.handle_oauth_callback(user_id, "code", "state", "http://x/callback")

    _patch_client(
        monkeypatch,
        "backend.infrastructure.email_integration.gmail_provider",
        [httpx.TimeoutException("timed out")],
    )
    with pytest.raises(EmailIntegrationTimeoutError):
        await provider.create_external_draft(
            user_id, ExternalDraftRequest(subject="s", body="b")
        )

    _patch_client(
        monkeypatch,
        "backend.infrastructure.email_integration.gmail_provider",
        [httpx.ConnectError("no route to host")],
    )
    with pytest.raises(EmailIntegrationConnectionError):
        await provider.create_external_draft(
            user_id, ExternalDraftRequest(subject="s", body="b")
        )


# -- Outlook provider ---------------------------------------------------------------


def test_outlook_provider_rejects_missing_client_id():
    with pytest.raises(EmailIntegrationConfigError):
        OutlookDraftProvider(
            client_id=None,
            client_secret=_SECRET_CLIENT_SECRET,
            tenant_id="common",
            connections=FakeEmailProviderConnectionRepository(),
            token_cipher=TokenCipher("test-key"),
        )


async def test_outlook_provider_requires_a_connection_before_creating_a_draft():
    provider = OutlookDraftProvider(
        client_id="client-id",
        client_secret=_SECRET_CLIENT_SECRET,
        tenant_id="common",
        connections=FakeEmailProviderConnectionRepository(),
        token_cipher=TokenCipher("test-key"),
    )
    with pytest.raises(EmailIntegrationAuthError):
        await provider.create_external_draft(
            uuid.uuid4(), ExternalDraftRequest(subject="s", body="b")
        )


async def test_outlook_create_draft_success(monkeypatch):
    connections = FakeEmailProviderConnectionRepository()
    provider = OutlookDraftProvider(
        client_id="client-id",
        client_secret=_SECRET_CLIENT_SECRET,
        tenant_id="common",
        connections=connections,
        token_cipher=TokenCipher("test-key"),
    )
    _patch_client(
        monkeypatch,
        "backend.infrastructure.email_integration.outlook_provider",
        [_FakeResponse(200, {"access_token": "tok", "expires_in": 3600})],
    )
    user_id = uuid.uuid4()
    await provider.handle_oauth_callback(user_id, "code", "state", "http://x/callback")

    _patch_client(
        monkeypatch,
        "backend.infrastructure.email_integration.outlook_provider",
        [_FakeResponse(201, {"id": "draft-abc", "webLink": "https://outlook.office.com/mail/drafts/abc"})],
    )
    result = await provider.create_external_draft(
        user_id, ExternalDraftRequest(subject="Hallo", body="Testinhalt")
    )

    assert result.status == ExternalDraftProviderStatus.CREATED
    assert result.provider_draft_id == "draft-abc"
    assert result.provider_draft_url == "https://outlook.office.com/mail/drafts/abc"


async def test_outlook_create_draft_maps_auth_error(monkeypatch):
    connections = FakeEmailProviderConnectionRepository()
    provider = OutlookDraftProvider(
        client_id="client-id",
        client_secret=_SECRET_CLIENT_SECRET,
        tenant_id="common",
        connections=connections,
        token_cipher=TokenCipher("test-key"),
    )
    _patch_client(
        monkeypatch,
        "backend.infrastructure.email_integration.outlook_provider",
        [_FakeResponse(200, {"access_token": "tok", "expires_in": 3600})],
    )
    user_id = uuid.uuid4()
    await provider.handle_oauth_callback(user_id, "code", "state", "http://x/callback")

    _patch_client(
        monkeypatch,
        "backend.infrastructure.email_integration.outlook_provider",
        [_FakeResponse(401, {})],
    )
    with pytest.raises(EmailIntegrationAuthError):
        await provider.create_external_draft(
            user_id, ExternalDraftRequest(subject="s", body="b")
        )
