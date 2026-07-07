import logging

from backend.domain.repositories.email_provider_connection_repository import (
    EmailProviderConnectionRepository,
)
from backend.infrastructure.email_integration.base import EmailIntegrationConfigError
from backend.infrastructure.email_integration.token_crypto import TokenCipher
from backend.infrastructure.reply_tracking.base import (
    ReplyTrackingConfigError,
    ReplyTrackingProvider,
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
from backend.shared.config import Settings, get_settings

logger = logging.getLogger("backend.reply_tracking")


class UnknownReplyTrackingProviderError(Exception):
    """Raised when an unknown ``REPLY_TRACKING_PROVIDER`` is requested."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Unknown reply tracking provider: '{name}'")


def create_reply_tracking_provider(
    connections: EmailProviderConnectionRepository,
    settings: Settings | None = None,
) -> ReplyTrackingProvider:
    """Build the configured reply tracking provider.

    Defaults to :class:`MockReplyTrackingProvider` so reply tracking works
    without any OAuth credentials. Set ``REPLY_TRACKING_PROVIDER`` to
    ``gmail``/``outlook`` to use a real backend — but even then, this only
    ever returns a provider that can make a real read call when ALL of the
    following hold:

    - ``REPLY_TRACKING_PROVIDER`` is ``gmail`` or ``outlook``
    - The matching OAuth client id/secret (and encryption key) are set
    - ``REPLY_TRACKING_ENABLE_REAL_READS=true``

    If any of those is missing, this safely falls back to the mock
    provider instead of raising, mirroring
    ``backend.infrastructure.email_integration.factory.create_email_draft_provider``.
    Never logs a secret — only whether one is set.
    """
    settings = settings or get_settings()
    provider = settings.reply_tracking_provider.strip().lower()

    if provider == "mock":
        return MockReplyTrackingProvider(connections)

    if provider not in ("gmail", "outlook"):
        logger.error("unknown reply tracking provider requested: %s", provider)
        raise UnknownReplyTrackingProviderError(provider)

    if not settings.reply_tracking_enable_real_reads:
        logger.warning(
            "REPLY_TRACKING_PROVIDER=%s but REPLY_TRACKING_ENABLE_REAL_READS "
            "is not true; falling back to the mock provider. No real "
            "mailbox will be read at %s. Set "
            "REPLY_TRACKING_ENABLE_REAL_READS=true in .env to use it for real.",
            provider,
            provider,
        )
        return MockReplyTrackingProvider(connections)

    try:
        token_cipher = TokenCipher(settings.email_token_encryption_key)
    except EmailIntegrationConfigError:
        logger.warning(
            "REPLY_TRACKING_PROVIDER=%s and REPLY_TRACKING_ENABLE_REAL_READS=true "
            "but EMAIL_TOKEN_ENCRYPTION_KEY is not set; falling back to the "
            "mock provider. No real mailbox will be read.",
            provider,
        )
        return MockReplyTrackingProvider(connections)

    if provider == "gmail":
        try:
            return GmailReplyTrackingProvider(
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret,
                connections=connections,
                token_cipher=token_cipher,
                timeout=settings.reply_tracking_timeout_seconds,
            )
        except ReplyTrackingConfigError:
            logger.warning(
                "REPLY_TRACKING_PROVIDER=gmail and "
                "REPLY_TRACKING_ENABLE_REAL_READS=true but "
                "GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET are not set; falling "
                "back to the mock provider. No real mailbox will be read."
            )
            return MockReplyTrackingProvider(connections)

    try:
        return OutlookReplyTrackingProvider(
            client_id=settings.microsoft_client_id,
            client_secret=settings.microsoft_client_secret,
            tenant_id=settings.microsoft_tenant_id,
            connections=connections,
            token_cipher=token_cipher,
            timeout=settings.reply_tracking_timeout_seconds,
        )
    except ReplyTrackingConfigError:
        logger.warning(
            "REPLY_TRACKING_PROVIDER=outlook and "
            "REPLY_TRACKING_ENABLE_REAL_READS=true but "
            "MICROSOFT_CLIENT_ID/MICROSOFT_CLIENT_SECRET are not set; "
            "falling back to the mock provider. No real mailbox will be read."
        )
        return MockReplyTrackingProvider(connections)
