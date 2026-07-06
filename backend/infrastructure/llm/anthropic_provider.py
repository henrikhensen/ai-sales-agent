import logging
from typing import Any

from backend.infrastructure.llm.base import (
    LLMConfigurationError,
    LLMConnectionError,
    LLMProvider,
    LLMProviderError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
)

#: Name of the synthetic tool used to force structured JSON output.
_RESULT_TOOL_NAME = "emit_result"

logger = logging.getLogger("backend.llm")


class AnthropicLLMProvider(LLMProvider):
    """Anthropic-backed provider that returns structured JSON via forced tool use.

    Prepared for real use but never invoked unless ``LLM_PROVIDER=anthropic``,
    ``LLM_ENABLE_REAL_CALLS=true``, and a valid ``ANTHROPIC_API_KEY`` are all
    supplied via the environment (enforced by
    :func:`backend.infrastructure.llm.factory.create_llm_provider`, not by
    this class). The API key is never hard-coded, never logged, and never
    included in any error message this class raises.

    Applies three safety caps, all configurable via ``Settings``: the input
    prompt is truncated to ``max_input_chars``, the response is capped at
    ``max_output_tokens``, and every request uses ``timeout`` seconds. Every
    known failure mode (missing key, rate limit, timeout, invalid model,
    other API errors, network errors) is translated into one of this
    package's own :class:`~backend.infrastructure.llm.base.LLMError`
    subclasses with a clean, secret-free message — callers never need to
    know about the ``anthropic`` SDK's own exception types.
    """

    name = "anthropic"

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        max_output_tokens: int = 1200,
        max_input_chars: int = 12_000,
        timeout: float = 30,
    ) -> None:
        if not api_key:
            raise LLMConfigurationError(
                "ANTHROPIC_API_KEY is not set; cannot use the anthropic provider."
            )
        # Imported lazily so the package is only required when this provider is used.
        from anthropic import AsyncAnthropic

        self._client = AsyncAnthropic(api_key=api_key, timeout=timeout)
        self._model = model
        self._max_output_tokens = max_output_tokens
        self._max_input_chars = max_input_chars

    async def generate_json(
        self,
        *,
        system: str,
        prompt: str,
        schema: dict[str, Any],
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        if len(prompt) > self._max_input_chars:
            logger.warning(
                "truncating anthropic prompt from %d to %d characters",
                len(prompt),
                self._max_input_chars,
            )
            prompt = prompt[: self._max_input_chars]

        tool = {
            "name": _RESULT_TOOL_NAME,
            "description": "Return the structured result for this task.",
            "input_schema": schema,
        }

        # Imported lazily, same reason as the client itself: only required
        # when this provider is actually constructed and used.
        import anthropic

        try:
            message = await self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens or self._max_output_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                tools=[tool],
                tool_choice={"type": "tool", "name": _RESULT_TOOL_NAME},
            )
        except anthropic.RateLimitError as exc:
            logger.warning("anthropic rate limit exceeded")
            raise LLMRateLimitError(
                "The LLM provider's rate limit was exceeded. Try again later."
            ) from exc
        except anthropic.APITimeoutError as exc:
            logger.warning("anthropic request timed out")
            raise LLMTimeoutError(
                "The request to the LLM provider timed out."
            ) from exc
        except anthropic.APIConnectionError as exc:
            logger.warning("could not reach anthropic (network error)")
            raise LLMConnectionError(
                "Could not reach the LLM provider (network error)."
            ) from exc
        except anthropic.AuthenticationError as exc:
            logger.error("anthropic authentication failed")
            raise LLMProviderError(
                "Authentication with the LLM provider failed. Check "
                "ANTHROPIC_API_KEY."
            ) from exc
        except anthropic.NotFoundError as exc:
            logger.error("anthropic model not found: %s", self._model)
            raise LLMProviderError(
                f"The configured model ('{self._model}') was not found by "
                "the provider. Check ANTHROPIC_MODEL."
            ) from exc
        except anthropic.APIStatusError as exc:
            logger.error(
                "anthropic returned an error status: %s", exc.status_code
            )
            raise LLMProviderError(
                f"The LLM provider returned an error (status {exc.status_code})."
            ) from exc
        except anthropic.AnthropicError as exc:
            logger.error("unexpected anthropic SDK error: %s", type(exc).__name__)
            raise LLMProviderError(
                "An unexpected error occurred while contacting the LLM provider."
            ) from exc

        for block in message.content:
            if block.type == "tool_use" and block.name == _RESULT_TOOL_NAME:
                return dict(block.input)

        raise LLMResponseError(
            "Anthropic response did not contain the expected tool_use block."
        )
