"""Tests for the LLM provider safety guard in backend/infrastructure/llm/factory.py.

The guard must ensure a real (billable) Anthropic call can only ever happen
when LLM_PROVIDER=anthropic, ANTHROPIC_API_KEY is set, AND
LLM_ENABLE_REAL_CALLS=true all hold at once — any one missing falls back to
the free, offline mock provider instead of raising.
"""

import pytest

from backend.infrastructure.llm.base import UnknownLLMProviderError
from backend.infrastructure.llm.factory import create_llm_provider
from backend.infrastructure.llm.mock_provider import MockLLMProvider
from backend.shared.config import Settings


def _settings(**overrides) -> Settings:
    # Settings fields declare an explicit env-var alias (e.g. LLM_PROVIDER)
    # and pydantic only accepts that alias as a constructor keyword by
    # default (not the snake_case Python attribute name) — using the
    # attribute name here would silently be dropped by extra="ignore" and
    # fall through to whatever the real environment/.env file has.
    defaults: dict = dict(
        LLM_PROVIDER="mock",
        ANTHROPIC_API_KEY=None,
        ANTHROPIC_MODEL="claude-opus-4-8",
        LLM_MAX_TOKENS=1024,
        LLM_ENABLE_REAL_CALLS=False,
        LLM_TIMEOUT_SECONDS=30,
    )
    defaults.update(overrides)
    return Settings(**defaults)


def test_factory_returns_mock_provider_by_default():
    provider = create_llm_provider(_settings())
    assert isinstance(provider, MockLLMProvider)


def test_factory_falls_back_to_mock_when_real_calls_disabled_even_with_key():
    provider = create_llm_provider(
        _settings(
            LLM_PROVIDER="anthropic",
            ANTHROPIC_API_KEY="sk-test-not-a-real-key",
            LLM_ENABLE_REAL_CALLS=False,
        )
    )
    assert isinstance(provider, MockLLMProvider)


def test_factory_falls_back_to_mock_when_api_key_missing_even_if_enabled():
    provider = create_llm_provider(
        _settings(
            LLM_PROVIDER="anthropic",
            ANTHROPIC_API_KEY=None,
            LLM_ENABLE_REAL_CALLS=True,
        )
    )
    assert isinstance(provider, MockLLMProvider)


def test_factory_returns_anthropic_provider_only_when_fully_enabled():
    provider = create_llm_provider(
        _settings(
            LLM_PROVIDER="anthropic",
            ANTHROPIC_API_KEY="sk-test-not-a-real-key",
            LLM_ENABLE_REAL_CALLS=True,
        )
    )
    assert provider.name == "anthropic"


def test_factory_raises_for_unknown_provider():
    with pytest.raises(UnknownLLMProviderError):
        create_llm_provider(_settings(LLM_PROVIDER="something-else"))
