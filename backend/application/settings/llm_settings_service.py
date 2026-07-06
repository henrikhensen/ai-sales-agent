"""LLM Settings Service: reports provider configuration and safely tests it.

Never returns, logs, or otherwise exposes ``ANTHROPIC_API_KEY`` — only
whether one is set (:attr:`LLMProviderStatus.anthropic_configured`). This
service never triggers a real (billable) API call unless ``LLM_PROVIDER``,
``ANTHROPIC_API_KEY``, and ``LLM_ENABLE_REAL_CALLS`` are all set — the same
guard :func:`backend.infrastructure.llm.factory.create_llm_provider` already
enforces when building the provider handed to :meth:`test_provider`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from backend.infrastructure.llm.base import LLMProvider
from backend.shared.config import Settings

logger = logging.getLogger("backend.llm")

_TEST_SCHEMA = {
    "type": "object",
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
}


@dataclass(frozen=True)
class LLMProviderStatus:
    """Read-only snapshot of the LLM provider configuration."""

    active_provider: str
    real_calls_enabled: bool
    anthropic_configured: bool
    anthropic_model: str | None
    safe_mode: bool
    mock_mode: bool
    message: str


@dataclass(frozen=True)
class LLMProviderTestResult:
    """Outcome of exercising the configured LLM provider once."""

    provider: str
    ok: bool
    message: str


class LLMSettingsService:
    """Reports the active LLM provider and can safely exercise it on demand."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get_status(self) -> LLMProviderStatus:
        settings = self._settings
        requested_provider = settings.llm_provider.strip().lower()
        anthropic_configured = bool(settings.anthropic_api_key)
        real_calls_enabled = settings.llm_enable_real_calls

        # Mirrors the exact condition backend/infrastructure/llm/factory.py
        # uses to decide whether it hands out a real AnthropicLLMProvider or
        # falls back to the mock provider — this must never drift from that.
        anthropic_actually_active = (
            requested_provider == "anthropic"
            and real_calls_enabled
            and anthropic_configured
        )
        active_provider = "anthropic" if anthropic_actually_active else "mock"

        if anthropic_actually_active:
            message = (
                f"Anthropic is active and real calls are enabled "
                f"(model={settings.anthropic_model}). Calls made via the "
                f"agents will incur real API cost."
            )
        elif requested_provider == "anthropic" and not real_calls_enabled:
            message = (
                "LLM_PROVIDER=anthropic but LLM_ENABLE_REAL_CALLS is not "
                "true, so the mock provider is used instead. No real API "
                "calls are made and no cost is incurred."
            )
        elif requested_provider == "anthropic" and not anthropic_configured:
            message = (
                "LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set, so "
                "the mock provider is used instead. No real API calls are "
                "made and no cost is incurred."
            )
        else:
            message = (
                "Mock provider is active. No real API calls are made and no "
                "cost is incurred."
            )

        return LLMProviderStatus(
            active_provider=active_provider,
            real_calls_enabled=real_calls_enabled,
            anthropic_configured=anthropic_configured,
            anthropic_model=settings.anthropic_model,
            safe_mode=not anthropic_actually_active,
            mock_mode=active_provider == "mock",
            message=message,
        )

    async def test_provider(self, llm: LLMProvider) -> LLMProviderTestResult:
        """Exercise ``llm`` with a trivial prompt to confirm it responds.

        ``llm`` is expected to come from
        :func:`backend.infrastructure.llm.factory.create_llm_provider`, which
        already refuses to hand out a real Anthropic provider unless real
        calls are explicitly enabled — so by the time this method runs,
        ``llm.name == "anthropic"`` can only happen when that was truly
        allowed. The one case this method still needs to detect itself is
        the user explicitly requesting an Anthropic test while real calls
        are disabled, so it can return the required clear message instead of
        silently testing the mock fallback without saying so.
        """
        requested_provider = self._settings.llm_provider.strip().lower()
        if requested_provider == "anthropic" and not self._settings.llm_enable_real_calls:
            return LLMProviderTestResult(
                provider="anthropic",
                ok=False,
                message=(
                    "Real LLM calls are disabled. Enable "
                    "LLM_ENABLE_REAL_CALLS=true in .env to test Anthropic."
                ),
            )

        try:
            await llm.generate_json(
                system="You are a connectivity test for the AI Sales Agent backend.",
                prompt=(
                    "Reply with a short JSON object containing a single "
                    "boolean field 'ok' set to true."
                ),
                schema=_TEST_SCHEMA,
                max_tokens=32,
            )
        except Exception:
            logger.exception("LLM provider test failed for provider=%s", llm.name)
            return LLMProviderTestResult(
                provider=llm.name,
                ok=False,
                message=f"Provider '{llm.name}' test failed. Check server logs for details.",
            )

        cost_note = (
            "No cost was incurred (mock provider)."
            if llm.name == "mock"
            else "This made a real, billable Anthropic API call."
        )
        return LLMProviderTestResult(
            provider=llm.name,
            ok=True,
            message=f"Provider '{llm.name}' responded successfully. {cost_note}",
        )
