from pydantic import BaseModel, Field


class LLMProviderStatusResponse(BaseModel):
    """Read-only snapshot of the LLM provider configuration.

    Never includes ``ANTHROPIC_API_KEY`` or any other secret — only whether
    one is configured (:attr:`anthropic_configured`).
    """

    active_provider: str = Field(
        description="Provider actually in effect after safety checks: 'mock' or 'anthropic'."
    )
    real_calls_enabled: bool = Field(
        description="Raw value of LLM_ENABLE_REAL_CALLS."
    )
    anthropic_configured: bool = Field(
        description="Whether ANTHROPIC_API_KEY is set. Never the key itself."
    )
    anthropic_model: str | None = Field(
        description="Configured ANTHROPIC_MODEL, regardless of whether Anthropic is active."
    )
    safe_mode: bool = Field(
        description="True when no billable API call can currently occur."
    )
    mock_mode: bool = Field(
        description="True when the mock provider is the one actually in effect."
    )
    message: str = Field(description="Human-readable summary of the above.")


class LLMProviderTestResponse(BaseModel):
    """Result of exercising the configured LLM provider once.

    Never includes any secret. In mock mode (the default) this only ever
    tests the mock provider — a real, billable Anthropic call happens only
    when LLM_PROVIDER=anthropic and LLM_ENABLE_REAL_CALLS=true are both set.
    """

    provider: str
    ok: bool
    message: str
