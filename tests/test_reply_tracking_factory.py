"""Tests for the reply tracking provider safety guard in
backend/infrastructure/reply_tracking/factory.py.

Mirrors tests/test_email_integration_factory.py: a real (Gmail/Outlook)
provider call can only ever happen when REPLY_TRACKING_PROVIDER is
gmail/outlook, the matching OAuth client id/secret and
EMAIL_TOKEN_ENCRYPTION_KEY are all set, AND
REPLY_TRACKING_ENABLE_REAL_READS=true all hold at once — any one missing
falls back to the free, offline mock provider instead of raising.
"""

import pytest

from backend.infrastructure.reply_tracking.factory import (
    UnknownReplyTrackingProviderError,
    create_reply_tracking_provider,
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
from backend.shared.config import Settings
from tests.conftest import FakeEmailProviderConnectionRepository


def _settings(**overrides) -> Settings:
    defaults: dict = dict(
        REPLY_TRACKING_PROVIDER="mock",
        REPLY_TRACKING_ENABLE_REAL_READS=False,
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
    provider = create_reply_tracking_provider(_connections(), _settings())
    assert isinstance(provider, MockReplyTrackingProvider)


def test_factory_falls_back_to_mock_when_real_reads_disabled_even_with_config():
    provider = create_reply_tracking_provider(
        _connections(),
        _settings(
            REPLY_TRACKING_PROVIDER="gmail",
            GOOGLE_CLIENT_ID="client-id",
            GOOGLE_CLIENT_SECRET="client-secret",
            EMAIL_TOKEN_ENCRYPTION_KEY="a-test-key",
            REPLY_TRACKING_ENABLE_REAL_READS=False,
        ),
    )
    assert isinstance(provider, MockReplyTrackingProvider)


def test_factory_falls_back_to_mock_when_gmail_config_missing_even_if_enabled():
    provider = create_reply_tracking_provider(
        _connections(),
        _settings(
            REPLY_TRACKING_PROVIDER="gmail",
            REPLY_TRACKING_ENABLE_REAL_READS=True,
            EMAIL_TOKEN_ENCRYPTION_KEY="a-test-key",
        ),
    )
    assert isinstance(provider, MockReplyTrackingProvider)


def test_factory_falls_back_to_mock_when_encryption_key_missing_even_if_enabled():
    provider = create_reply_tracking_provider(
        _connections(),
        _settings(
            REPLY_TRACKING_PROVIDER="gmail",
            REPLY_TRACKING_ENABLE_REAL_READS=True,
            GOOGLE_CLIENT_ID="client-id",
            GOOGLE_CLIENT_SECRET="client-secret",
            EMAIL_TOKEN_ENCRYPTION_KEY=None,
        ),
    )
    assert isinstance(provider, MockReplyTrackingProvider)


def test_factory_returns_gmail_provider_only_when_fully_enabled():
    provider = create_reply_tracking_provider(
        _connections(),
        _settings(
            REPLY_TRACKING_PROVIDER="gmail",
            REPLY_TRACKING_ENABLE_REAL_READS=True,
            GOOGLE_CLIENT_ID="client-id",
            GOOGLE_CLIENT_SECRET="client-secret",
            EMAIL_TOKEN_ENCRYPTION_KEY="a-test-key",
        ),
    )
    assert isinstance(provider, GmailReplyTrackingProvider)
    assert provider.name == "gmail"


def test_factory_returns_outlook_provider_only_when_fully_enabled():
    provider = create_reply_tracking_provider(
        _connections(),
        _settings(
            REPLY_TRACKING_PROVIDER="outlook",
            REPLY_TRACKING_ENABLE_REAL_READS=True,
            MICROSOFT_CLIENT_ID="client-id",
            MICROSOFT_CLIENT_SECRET="client-secret",
            EMAIL_TOKEN_ENCRYPTION_KEY="a-test-key",
        ),
    )
    assert isinstance(provider, OutlookReplyTrackingProvider)
    assert provider.name == "outlook"


def test_factory_raises_for_unknown_provider():
    with pytest.raises(UnknownReplyTrackingProviderError):
        create_reply_tracking_provider(
            _connections(), _settings(REPLY_TRACKING_PROVIDER="yahoo")
        )
