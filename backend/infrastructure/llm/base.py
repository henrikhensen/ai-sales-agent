from abc import ABC, abstractmethod
from typing import Any


class LLMError(Exception):
    """Base class for LLM provider errors."""


class LLMConfigurationError(LLMError):
    """Raised when a provider is misconfigured (e.g. missing API key)."""


class LLMResponseError(LLMError):
    """Raised when a provider returns an unusable response."""


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
