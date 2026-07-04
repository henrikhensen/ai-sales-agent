from typing import Any

from backend.infrastructure.llm.base import (
    LLMConfigurationError,
    LLMProvider,
    LLMResponseError,
)

#: Name of the synthetic tool used to force structured JSON output.
_RESULT_TOOL_NAME = "emit_result"


class AnthropicLLMProvider(LLMProvider):
    """Anthropic-backed provider that returns structured JSON via forced tool use.

    Prepared for real use but never invoked unless ``LLM_PROVIDER=anthropic`` and
    a valid ``ANTHROPIC_API_KEY`` is supplied via the environment. The API key is
    never hard-coded — it is passed in from configuration.
    """

    name = "anthropic"

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        max_tokens: int = 1024,
    ) -> None:
        if not api_key:
            raise LLMConfigurationError(
                "ANTHROPIC_API_KEY is not set; cannot use the anthropic provider."
            )
        # Imported lazily so the package is only required when this provider is used.
        from anthropic import AsyncAnthropic

        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    async def generate_json(
        self,
        *,
        system: str,
        prompt: str,
        schema: dict[str, Any],
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        tool = {
            "name": _RESULT_TOOL_NAME,
            "description": "Return the structured result for this task.",
            "input_schema": schema,
        }

        message = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens or self._max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            tools=[tool],
            tool_choice={"type": "tool", "name": _RESULT_TOOL_NAME},
        )

        for block in message.content:
            if block.type == "tool_use" and block.name == _RESULT_TOOL_NAME:
                return dict(block.input)

        raise LLMResponseError(
            "Anthropic response did not contain the expected tool_use block."
        )
