import logging

from backend.infrastructure.llm.anthropic_provider import AnthropicLLMProvider
from backend.infrastructure.llm.base import (
    LLMConfigurationError,
    LLMProvider,
    UnknownLLMProviderError,
)
from backend.infrastructure.llm.mock_provider import MockLLMProvider
from backend.shared.config import Settings, get_settings

logger = logging.getLogger("backend.llm")


def create_llm_provider(settings: Settings | None = None) -> LLMProvider:
    """Build the configured LLM provider.

    Defaults to the :class:`MockLLMProvider` so the system runs without any
    external credentials. Set ``LLM_PROVIDER=anthropic`` to use the real
    backend — but even then, this only ever returns a provider that can make
    real (billable) calls when ALL of the following hold:

    - ``LLM_PROVIDER=anthropic``
    - ``ANTHROPIC_API_KEY`` is set
    - ``LLM_ENABLE_REAL_CALLS=true``

    If any of those is missing, this safely falls back to the mock provider
    instead of raising, so agent/workflow endpoints keep working exactly as
    before this safety guard existed — no request ever triggers a
    surprise-billable call just because ``LLM_PROVIDER`` was left set to
    ``anthropic``. Never logs the API key itself, only whether one is set.
    """
    settings = settings or get_settings()
    provider = settings.llm_provider.strip().lower()

    if provider == "mock":
        return MockLLMProvider()

    if provider == "anthropic":
        if not settings.llm_enable_real_calls:
            logger.warning(
                "LLM_PROVIDER=anthropic but LLM_ENABLE_REAL_CALLS is not true; "
                "falling back to the mock provider. No real API calls will be "
                "made. Set LLM_ENABLE_REAL_CALLS=true in .env to use Anthropic."
            )
            return MockLLMProvider()
        if not settings.anthropic_api_key:
            logger.warning(
                "LLM_PROVIDER=anthropic and LLM_ENABLE_REAL_CALLS=true but "
                "ANTHROPIC_API_KEY is not set; falling back to the mock "
                "provider. No real API calls will be made."
            )
            return MockLLMProvider()
        try:
            return AnthropicLLMProvider(
                api_key=settings.anthropic_api_key,
                model=settings.anthropic_model,
                max_tokens=settings.llm_max_tokens,
                timeout=settings.llm_timeout_seconds,
            )
        except LLMConfigurationError:
            logger.error(
                "failed to initialize the anthropic provider: missing or invalid "
                "configuration (model=%s)",
                settings.anthropic_model,
            )
            raise
    logger.error("unknown LLM provider requested: %s", provider)
    raise UnknownLLMProviderError(provider)
