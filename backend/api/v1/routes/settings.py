"""LLM provider settings: read-only status and an optional connectivity test.

Never returns, logs, or otherwise exposes ``ANTHROPIC_API_KEY`` — only
whether one is configured. The mock provider remains the default and never
incurs API cost; a real Anthropic call only ever happens when
``LLM_PROVIDER=anthropic`` and ``LLM_ENABLE_REAL_CALLS=true`` are both set
(see ``backend/infrastructure/llm/factory.py``).
"""

from dataclasses import asdict

from fastapi import APIRouter, Depends, Request

from backend.api.dependencies.auth import (
    RequireAdminUserDep,
    RequireSalesReviewerOrAdminDep,
)
from backend.api.v1.dependencies import (
    AuditLogServiceDep,
    LLMProviderDep,
    LLMSettingsServiceDep,
)
from backend.api.v1.schemas.settings import (
    LLMProviderStatusResponse,
    LLMProviderTestResponse,
)
from backend.shared.rate_limit import rate_limit

router = APIRouter(prefix="/settings", tags=["settings"])

_llm_test_rate_limit = rate_limit("llm_test", "rate_limit_llm_test_per_hour", 3600)


@router.get("/llm/status", response_model=LLMProviderStatusResponse)
async def get_llm_status(
    service: LLMSettingsServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> LLMProviderStatusResponse:
    """Report which LLM provider is active and whether Anthropic is configured.

    Read-only, any active admin, reviewer, or sales account. Never returns
    ``ANTHROPIC_API_KEY`` — only the boolean ``anthropic_configured``.
    """
    status = service.get_status()
    return LLMProviderStatusResponse(**asdict(status))


@router.post(
    "/llm/test",
    response_model=LLMProviderTestResponse,
    dependencies=[Depends(_llm_test_rate_limit)],
)
async def test_llm_provider(
    llm: LLMProviderDep,
    service: LLMSettingsServiceDep,
    current_user: RequireAdminUserDep,
    audit: AuditLogServiceDep,
    request: Request,
) -> LLMProviderTestResponse:
    """Exercise the configured LLM provider with a trivial prompt.

    Admin-only. In mock mode (the default) this only ever tests the mock
    provider at no cost. A real, billable Anthropic call happens only when
    ``LLM_PROVIDER=anthropic`` and ``LLM_ENABLE_REAL_CALLS=true`` are both
    set — otherwise this responds with a clear, non-billable explanation
    instead of attempting one. Rate-limited per user
    (``RATE_LIMIT_LLM_TEST_PER_HOUR``).
    """
    result = await service.test_provider(llm)
    await audit.record(
        action="llm_test_executed",
        result="success" if result.ok else "failed",
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        entity_type="llm_provider",
        entity_id=result.provider,
        request=request,
    )
    return LLMProviderTestResponse(
        provider=result.provider, ok=result.ok, message=result.message
    )
