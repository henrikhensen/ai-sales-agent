from abc import ABC, abstractmethod
from typing import Any


class LLMError(Exception):
    """Base class for LLM provider errors."""


class LLMConfigurationError(LLMError):
    """Raised when a provider is misconfigured (e.g. missing API key)."""


class LLMResponseError(LLMError):
    """Raised when a provider returns an unusable response."""


class LLMRateLimitError(LLMError):
    """Raised when the provider reports its rate limit was exceeded."""


class LLMTimeoutError(LLMError):
    """Raised when a request to the provider times out."""


class LLMConnectionError(LLMError):
    """Raised when the provider cannot be reached (network failure)."""


class LLMProviderError(LLMError):
    """Raised for any other provider-side error (invalid model, auth,
    malformed request, or an internal error reported by the provider)."""


class UnknownLLMProviderError(LLMError):
    """Raised when an unknown provider name is requested."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Unknown LLM provider: '{name}'")


class LLMProvider(ABC):
    """Port for a large language model backend.

    Concrete providers (mock, Anthropic, ...) implement :meth:`generate_json`,
    which returns a JSON object conforming to the supplied JSON Schema.
    """

    #: Stable identifier for the provider, surfaced in agent run results.
    name: str

    @abstractmethod
    async def generate_json(
        self,
        *,
        system: str,
        prompt: str,
        schema: dict[str, Any],
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Generate a JSON object that conforms to ``schema``.

        Args:
            system: System prompt describing the model's role.
            prompt: The user prompt / task input.
            schema: JSON Schema the returned object must conform to.
            max_tokens: Optional override for the response token budget.

        Returns:
            A dictionary matching ``schema``.
        """
