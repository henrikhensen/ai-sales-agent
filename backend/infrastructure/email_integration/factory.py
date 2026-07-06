import logging

from backend.domain.repositories.email_provider_connection_repository import (
    EmailProviderConnectionRepository,
)
from backend.infrastructure.email_integration.base import (
    EmailDraftProvider,
    EmailIntegrationConfigError,
)
from backend.infrastructure.email_integration.gmail_provider import GmailDraftProvider
from backend.infrastructure.email_integration.mock_provider import (
    MockEmailDraftProvider,
)
from backend.infrastructure.email_integration.outlook_provider import (
    OutlookDraftProvider,
)
from backend.infrastructure.email_integration.token_crypto import TokenCipher
from backend.shared.config import Settings, get_settings

logger = logging.getLogger("backend.email_integration")


class UnknownEmailProviderError(Exception):
    """Raised when an unknown ``EMAIL_INTEGRATION_PROVIDER`` is requested."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Unknown email integration provider: '{name}'")


def create_email_draft_provider(
    connections: EmailProviderConnectionRepository,
    settings: Settings | None = None,
) -> EmailDraftProvider:
    """Build the configured email draft provider.

    Defaults to :class:`MockEmailDraftProvider` so external draft creation
    works without any OAuth credentials. Set ``EMAIL_INTEGRATION_PROVIDER``
    to ``gmail``/``outlook`` to use a real backend — but even then, this
    only ever returns a provider that can make a real provider call when
    ALL of the following hold:

    - ``EMAIL_INTEGRATION_PROVIDER`` is ``gmail`` or ``outlook``
    - The matching OAuth client id/secret (and encryption key) are set
    - ``EMAIL_INTEGRATION_ENABLE_REAL_DRAFTS=true``

    If any of those is missing, this safely falls back to the mock
    provider instead of raising, mirroring
    ``backend.infrastructure.llm.factory.create_llm_provider``. Never logs
    a secret — only whether one is set.
    """
    settings = settings or get_settings()
    provider = settings.email_integration_provider.strip().lower()

    if provider == "mock":
        return MockEmailDraftProvider(connections)

    if provider not in ("gmail", "outlook"):
        logger.error("unknown email integration provider requested: %s", provider)
        raise UnknownEmailProviderError(provider)

    if not settings.email_integration_enable_real_drafts:
        logger.warning(
            "EMAIL_INTEGRATION_PROVIDER=%s but "
            "EMAIL_INTEGRATION_ENABLE_REAL_DRAFTS is not true; falling back "
            "to the mock provider. No real draft will be created at %s. "
            "Set EMAIL_INTEGRATION_ENABLE_REAL_DRAFTS=true in .env to use "
            "it for real.",
            provider,
            provider,
        )
        return MockEmailDraftProvider(connections)

    try:
        token_cipher = TokenCipher(settings.email_token_encryption_key)
    except EmailIntegrationConfigError:
        logger.warning(
            "EMAIL_INTEGRATION_PROVIDER=%s and EMAIL_INTEGRATION_ENABLE_REAL_DRAFTS=true "
            "but EMAIL_TOKEN_ENCRYPTION_KEY is not set; falling back to the "
            "mock provider. No real draft will be created.",
            provider,
        )
        return MockEmailDraftProvider(connections)

    if provider == "gmail":
        try:
            return GmailDraftProvider(
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret,
                connections=connections,
                token_cipher=token_cipher,
            )
        except EmailIntegrationConfigError:
            logger.warning(
                "EMAIL_INTEGRATION_PROVIDER=gmail and "
                "EMAIL_INTEGRATION_ENABLE_REAL_DRAFTS=true but "
                "GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET are not set; falling "
                "back to the mock provider. No real draft will be created."
            )
            return MockEmailDraftProvider(connections)

    try:
        return OutlookDraftProvider(
            client_id=settings.microsoft_client_id,
            client_secret=settings.microsoft_client_secret,
            tenant_id=settings.microsoft_tenant_id,
            connections=connections,
            token_cipher=token_cipher,
        )
    except EmailIntegrationConfigError:
        logger.warning(
            "EMAIL_INTEGRATION_PROVIDER=outlook and "
            "EMAIL_INTEGRATION_ENABLE_REAL_DRAFTS=true but "
            "MICROSOFT_CLIENT_ID/MICROSOFT_CLIENT_SECRET are not set; "
            "falling back to the mock provider. No real draft will be created."
        )
        return MockEmailDraftProvider(connections)
