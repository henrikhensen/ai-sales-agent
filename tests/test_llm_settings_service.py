"""Tests for LLMSettingsService: status reporting and the safe test-call path.

These must never leak ANTHROPIC_API_KEY — only a boolean
``anthropic_configured`` derived from whether one is set.
"""

from backend.application.settings.llm_settings_service import LLMSettingsService
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


# -- get_status ---------------------------------------------------------------

def test_status_reports_mock_active_by_default():
    status = LLMSettingsService(_settings()).get_status()
    assert status.active_provider == "mock"
    assert status.mock_mode is True
    assert status.safe_mode is True
    assert status.real_calls_enabled is False
    assert status.anthropic_configured is False


def test_status_anthropic_not_configured_without_key():
    status = LLMSettingsService(
        _settings(LLM_PROVIDER="anthropic", ANTHROPIC_API_KEY=None)
    ).get_status()
    assert status.anthropic_configured is False
    # No key, no real calls enabled -> still safely mock underneath.
    assert status.active_provider == "mock"


def test_status_anthropic_configured_true_with_key_but_key_never_present():
    real_key = "sk-ant-super-secret-value-should-never-leak"
    status = LLMSettingsService(
        _settings(LLM_PROVIDER="anthropic", ANTHROPIC_API_KEY=real_key)
    ).get_status()

    assert status.anthropic_configured is True
    # The dataclass has no field carrying the raw key, and none of the
    # human-readable fields may ever contain it either.
    assert not hasattr(status, "anthropic_api_key")
    for value in (status.message, status.active_provider, status.anthropic_model):
        assert value is None or real_key not in str(value)


def test_status_real_calls_disabled_keeps_provider_mock_even_with_key():
    status = LLMSettingsService(
        _settings(
            LLM_PROVIDER="anthropic",
            ANTHROPIC_API_KEY="sk-test-not-a-real-key",
            LLM_ENABLE_REAL_CALLS=False,
        )
    ).get_status()

    assert status.real_calls_enabled is False
    assert status.active_provider == "mock"
    assert status.mock_mode is True
    assert status.safe_mode is True


def test_status_anthropic_active_only_when_all_three_conditions_met():
    status = LLMSettingsService(
        _settings(
            LLM_PROVIDER="anthropic",
            ANTHROPIC_API_KEY="sk-test-not-a-real-key",
            LLM_ENABLE_REAL_CALLS=True,
        )
    ).get_status()

    assert status.active_provider == "anthropic"
    assert status.mock_mode is False
    assert status.safe_mode is False
    assert status.anthropic_model == "claude-opus-4-8"


# -- test_provider --------------------------------------------------------------

async def test_test_provider_runs_mock_successfully():
    service = LLMSettingsService(_settings())
    result = await service.test_provider(MockLLMProvider())

    assert result.ok is True
    assert result.provider == "mock"
    assert "No cost was incurred" in result.message


async def test_test_provider_blocks_anthropic_when_real_calls_disabled():
    service = LLMSettingsService(
        _settings(
            LLM_PROVIDER="anthropic",
            ANTHROPIC_API_KEY="sk-test-not-a-real-key",
            LLM_ENABLE_REAL_CALLS=False,
        )
    )
    # Even though a MockLLMProvider is what the factory would actually hand
    # back in this configuration, test_provider must recognise the request
    # was for anthropic specifically and return the required message
    # without attempting any call.
    result = await service.test_provider(MockLLMProvider())

    assert result.ok is False
    assert result.provider == "anthropic"
    assert result.message == (
        "Real LLM calls are disabled. Enable LLM_ENABLE_REAL_CALLS=true in "
        ".env to test Anthropic."
    )
