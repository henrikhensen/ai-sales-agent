"""Tests for the email draft provider safety guard in
backend/infrastructure/email_integration/factory.py.

Mirrors tests/test_llm_provider_factory.py: a real (Gmail/Outlook) provider
call can only ever happen when EMAIL_INTEGRATION_PROVIDER is gmail/outlook,
the matching OAuth client id/secret and EMAIL_TOKEN_ENCRYPTION_KEY are all
set, AND EMAIL_INTEGRATION_ENABLE_REAL_DRAFTS=true all hold at once — any
one missing falls back to the free, offline mock provider instead of
raising.
"""

from backend.infrastructure.email_integration.factory import (
    UnknownEmailProviderError,
    create_email_draft_provider,
)
from backend.infrastructure.email_integration.gmail_provider import GmailDraftProvider
from backend.infrastructure.email_integration.mock_provider import (
    MockEmailDraftProvider,
)
from backend.infrastructure.email_integration.outlook_provider import (
    OutlookDraftProvider,
)
from backend.shared.config import Settings
from tests.conftest import FakeEmailProviderConnectionRepository

import pytest


def _settings(**overrides) -> Settings:
    defaults: dict = dict(
        EMAIL_INTEGRATION_PROVIDER="mock",
        EMAIL_INTEGRATION_ENABLE_REAL_DRAFTS=False,
        GOOGLE_CLIENT_ID=None,
        GOOGLE_CLIENT_SECRET=None,
        MICROSOFT_CLIENT_ID=None,
        MICROSOFT_CLIENT_SECRET=None,
        MICROSOFT_TENANT_ID="common",
        EMAIL_TOKEN_ENCRYPTION_KEY=None,
    )
    defaults.update(overrides)
    return Settings(**defaults)


def _connections():
    return FakeEmailProviderConnectionRepository()


def test_factory_returns_mock_provider_by_default():
    provider = create_email_draft_provider(_connections(), _settings())
    assert isinstance(provider, MockEmailDraftProvider)


def test_factory_falls_back_to_mock_when_real_drafts_disabled_even_with_config():
    provider = create_email_draft_provider(
        _connections(),
        _settings(
            EMAIL_INTEGRATION_PROVIDER="gmail",
            GOOGLE_CLIENT_ID="client-id",
            GOOGLE_CLIENT_SECRET="client-secret",
            EMAIL_TOKEN_ENCRYPTION_KEY="a-test-key",
            EMAIL_INTEGRATION_ENABLE_REAL_DRAFTS=False,
        ),
    )
    assert isinstance(provider, MockEmailDraftProvider)


def test_factory_falls_back_to_mock_when_gmail_config_missing_even_if_enabled():
    provider = create_email_draft_provider(
        _connections(),
        _settings(
            EMAIL_INTEGRATION_PROVIDER="gmail",
            EMAIL_INTEGRATION_ENABLE_REAL_DRAFTS=True,
            EMAIL_TOKEN_ENCRYPTION_KEY="a-test-key",
        ),
    )
    assert isinstance(provider, MockEmailDraftProvider)


def test_factory_falls_back_to_mock_when_encryption_key_missing_even_if_enabled():
    provider = create_email_draft_provider(
        _connections(),
        _settings(
            EMAIL_INTEGRATION_PROVIDER="gmail",
            EMAIL_INTEGRATION_ENABLE_REAL_DRAFTS=True,
            GOOGLE_CLIENT_ID="client-id",
            GOOGLE_CLIENT_SECRET="client-secret",
            EMAIL_TOKEN_ENCRYPTION_KEY=None,
        ),
    )
    assert isinstance(provider, MockEmailDraftProvider)


def test_factory_returns_gmail_provider_only_when_fully_enabled():
    provider = create_email_draft_provider(
        _connections(),
        _settings(
            EMAIL_INTEGRATION_PROVIDER="gmail",
            EMAIL_INTEGRATION_ENABLE_REAL_DRAFTS=True,
            GOOGLE_CLIENT_ID="client-id",
            GOOGLE_CLIENT_SECRET="client-secret",
            EMAIL_TOKEN_ENCRYPTION_KEY="a-test-key",
        ),
    )
    assert isinstance(provider, GmailDraftProvider)
    assert provider.name == "gmail"


def test_factory_returns_outlook_provider_only_when_fully_enabled():
    provider = create_email_draft_provider(
        _connections(),
        _settings(
            EMAIL_INTEGRATION_PROVIDER="outlook",
            EMAIL_INTEGRATION_ENABLE_REAL_DRAFTS=True,
            MICROSOFT_CLIENT_ID="client-id",
            MICROSOFT_CLIENT_SECRET="client-secret",
            EMAIL_TOKEN_ENCRYPTION_KEY="a-test-key",
        ),
    )
    assert isinstance(provider, OutlookDraftProvider)
    assert provider.name == "outlook"


def test_factory_falls_back_to_mock_when_outlook_config_missing_even_if_enabled():
    provider = create_email_draft_provider(
        _connections(),
        _settings(
            EMAIL_INTEGRATION_PROVIDER="outlook",
            EMAIL_INTEGRATION_ENABLE_REAL_DRAFTS=True,
            EMAIL_TOKEN_ENCRYPTION_KEY="a-test-key",
        ),
    )
    assert isinstance(provider, MockEmailDraftProvider)


def test_factory_raises_for_unknown_provider():
    with pytest.raises(UnknownEmailProviderError):
        create_email_draft_provider(
            _connections(), _settings(EMAIL_INTEGRATION_PROVIDER="yahoo")
        )
