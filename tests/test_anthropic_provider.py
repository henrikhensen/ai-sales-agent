"""Unit tests for AnthropicLLMProvider's safety behavior: refusal to
construct without a key, input truncation, and clean translation of every
known SDK failure mode into this package's own LLMError subclasses — never
leaking the API key in any raised error. No real network calls: the SDK
client's ``messages.create`` is monkeypatched in every test.
"""

import anthropic
import httpx
import pytest

from backend.infrastructure.llm.anthropic_provider import AnthropicLLMProvider
from backend.infrastructure.llm.base import (
    LLMConfigurationError,
    LLMConnectionError,
    LLMProviderError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
)

_SCHEMA = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}
_SECRET_KEY = "sk-ant-super-secret-value-should-never-leak"


def _request() -> httpx.Request:
    return httpx.Request("POST", "https://api.anthropic.com/v1/messages")


def _response(status_code: int) -> httpx.Response:
    return httpx.Response(status_code, request=_request())


class _ToolUseBlock:
    type = "tool_use"
    name = "emit_result"

    def __init__(self, input: dict) -> None:
        self.input = input


class _Message:
    def __init__(self, content: list) -> None:
        self.content = content


def test_constructor_rejects_missing_api_key():
    with pytest.raises(LLMConfigurationError):
        AnthropicLLMProvider(api_key=None, model="claude-opus-4-8")


def test_constructor_rejects_empty_api_key():
    with pytest.raises(LLMConfigurationError):
        AnthropicLLMProvider(api_key="", model="claude-opus-4-8")


async def test_prompt_is_truncated_to_max_input_chars(monkeypatch):
    provider = AnthropicLLMProvider(
        api_key=_SECRET_KEY, model="claude-opus-4-8", max_input_chars=10
    )
    captured: dict = {}

    async def fake_create(**kwargs):
        captured.update(kwargs)
        return _Message([_ToolUseBlock({"ok": True})])

    monkeypatch.setattr(provider._client.messages, "create", fake_create)

    await provider.generate_json(system="sys", prompt="x" * 100, schema=_SCHEMA)

    sent_prompt = captured["messages"][0]["content"]
    assert len(sent_prompt) == 10


async def test_short_prompt_is_not_truncated(monkeypatch):
    provider = AnthropicLLMProvider(
        api_key=_SECRET_KEY, model="claude-opus-4-8", max_input_chars=1000
    )
    captured: dict = {}

    async def fake_create(**kwargs):
        captured.update(kwargs)
        return _Message([_ToolUseBlock({"ok": True})])

    monkeypatch.setattr(provider._client.messages, "create", fake_create)

    await provider.generate_json(system="sys", prompt="hello", schema=_SCHEMA)

    assert captured["messages"][0]["content"] == "hello"


async def test_successful_call_returns_the_tool_input(monkeypatch):
    provider = AnthropicLLMProvider(api_key=_SECRET_KEY, model="claude-opus-4-8")

    async def fake_create(**kwargs):
        return _Message([_ToolUseBlock({"ok": True})])

    monkeypatch.setattr(provider._client.messages, "create", fake_create)

    result = await provider.generate_json(system="sys", prompt="hello", schema=_SCHEMA)

    assert result == {"ok": True}


async def test_missing_tool_use_block_raises_response_error(monkeypatch):
    provider = AnthropicLLMProvider(api_key=_SECRET_KEY, model="claude-opus-4-8")

    async def fake_create(**kwargs):
        return _Message([])

    monkeypatch.setattr(provider._client.messages, "create", fake_create)

    with pytest.raises(LLMResponseError):
        await provider.generate_json(system="sys", prompt="hello", schema=_SCHEMA)


async def test_rate_limit_error_is_translated_and_never_leaks_the_key(monkeypatch):
    provider = AnthropicLLMProvider(api_key=_SECRET_KEY, model="claude-opus-4-8")

    async def fake_create(**kwargs):
        raise anthropic.RateLimitError("rate limited", response=_response(429), body=None)

    monkeypatch.setattr(provider._client.messages, "create", fake_create)

    with pytest.raises(LLMRateLimitError) as exc_info:
        await provider.generate_json(system="sys", prompt="hello", schema=_SCHEMA)
    assert _SECRET_KEY not in str(exc_info.value)


async def test_timeout_error_is_translated_and_never_leaks_the_key(monkeypatch):
    provider = AnthropicLLMProvider(api_key=_SECRET_KEY, model="claude-opus-4-8")

    async def fake_create(**kwargs):
        raise anthropic.APITimeoutError(request=_request())

    monkeypatch.setattr(provider._client.messages, "create", fake_create)

    with pytest.raises(LLMTimeoutError) as exc_info:
        await provider.generate_json(system="sys", prompt="hello", schema=_SCHEMA)
    assert _SECRET_KEY not in str(exc_info.value)


async def test_connection_error_is_translated_and_never_leaks_the_key(monkeypatch):
    provider = AnthropicLLMProvider(api_key=_SECRET_KEY, model="claude-opus-4-8")

    async def fake_create(**kwargs):
        raise anthropic.APIConnectionError(request=_request())

    monkeypatch.setattr(provider._client.messages, "create", fake_create)

    with pytest.raises(LLMConnectionError) as exc_info:
        await provider.generate_json(system="sys", prompt="hello", schema=_SCHEMA)
    assert _SECRET_KEY not in str(exc_info.value)


async def test_authentication_error_is_translated_and_never_leaks_the_key(monkeypatch):
    provider = AnthropicLLMProvider(api_key=_SECRET_KEY, model="claude-opus-4-8")

    async def fake_create(**kwargs):
        raise anthropic.AuthenticationError(
            "invalid x-api-key", response=_response(401), body=None
        )

    monkeypatch.setattr(provider._client.messages, "create", fake_create)

    with pytest.raises(LLMProviderError) as exc_info:
        await provider.generate_json(system="sys", prompt="hello", schema=_SCHEMA)
    assert _SECRET_KEY not in str(exc_info.value)


async def test_model_not_found_error_is_translated_and_never_leaks_the_key(monkeypatch):
    provider = AnthropicLLMProvider(api_key=_SECRET_KEY, model="not-a-real-model")

    async def fake_create(**kwargs):
        raise anthropic.NotFoundError(
            "model not found", response=_response(404), body=None
        )

    monkeypatch.setattr(provider._client.messages, "create", fake_create)

    with pytest.raises(LLMProviderError) as exc_info:
        await provider.generate_json(system="sys", prompt="hello", schema=_SCHEMA)
    assert _SECRET_KEY not in str(exc_info.value)
    assert "not-a-real-model" in str(exc_info.value)


async def test_generic_api_status_error_is_translated_and_never_leaks_the_key(
    monkeypatch,
):
    provider = AnthropicLLMProvider(api_key=_SECRET_KEY, model="claude-opus-4-8")

    async def fake_create(**kwargs):
        raise anthropic.InternalServerError(
            "upstream error", response=_response(500), body=None
        )

    monkeypatch.setattr(provider._client.messages, "create", fake_create)

    with pytest.raises(LLMProviderError) as exc_info:
        await provider.generate_json(system="sys", prompt="hello", schema=_SCHEMA)
    assert _SECRET_KEY not in str(exc_info.value)
