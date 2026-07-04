from backend.infrastructure.llm.anthropic_provider import AnthropicLLMProvider
from backend.infrastructure.llm.base import LLMProvider, UnknownLLMProviderError
from backend.infrastructure.llm.mock_provider import MockLLMProvider
from backend.shared.config import Settings, get_settings


def create_llm_provider(settings: Settings | None = None) -> LLMProvider:
    """Build the configured LLM provider.

    Defaults to the :class:`MockLLMProvider` so the system runs without any
    external credentials. Set ``LLM_PROVIDER=anthropic`` to use the real backend.
    """
    settings = settings or get_settings()
    provider = settings.llm_provider.strip().lower()

    if provider == "mock":
        return MockLLMProvider()
    if provider == "anthropic":
        return AnthropicLLMProvider(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            max_tokens=settings.llm_max_tokens,
        )
    raise UnknownLLMProviderError(provider)
