"""Customer Onboarding: tracks one user's progress through a fixed
sequence of guided setup steps, plus a system-wide readiness report.

Read-only and bookkeeping-only endpoints — nothing here ever enables a
real provider, sends an email, or contacts anyone.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend.api.dependencies.auth import (
    RequireSalesOrAdminDep,
    RequireSalesReviewerOrAdminDep,
)
from backend.api.v1.dependencies import OnboardingServiceDep
from backend.application.onboarding.schemas import (
    OnboardingReadinessResponse,
    OnboardingStatusResponse,
    OnboardingStepUpdateRequest,
    OnboardingStepUpdateResponse,
)
from backend.domain.exceptions import InvalidOnboardingStepError
from backend.shared.rate_limit import rate_limit

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

_onboarding_update_rate_limit = Depends(
    rate_limit("onboarding_update", "rate_limit_default_per_minute", 60)
)


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    service: OnboardingServiceDep,
    current_user: RequireSalesReviewerOrAdminDep,
) -> OnboardingStatusResponse:
    """Return the current user's own onboarding progress."""
    return await service.get_status(current_user.id)


@router.patch(
    "/steps/{step_name}/complete",
    response_model=OnboardingStepUpdateResponse,
    dependencies=[_onboarding_update_rate_limit],
)
async def complete_onboarding_step(
    step_name: str,
    _payload: OnboardingStepUpdateRequest,
    service: OnboardingServiceDep,
    current_user: RequireSalesOrAdminDep,
    request: Request,
) -> OnboardingStepUpdateResponse:
    try:
        return await service.complete_step(
            current_user.id,
            step_name,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except InvalidOnboardingStepError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch(
    "/steps/{step_name}/skip",
    response_model=OnboardingStepUpdateResponse,
    dependencies=[_onboarding_update_rate_limit],
)
async def skip_onboarding_step(
    step_name: str,
    _payload: OnboardingStepUpdateRequest,
    service: OnboardingServiceDep,
    current_user: RequireSalesOrAdminDep,
    request: Request,
) -> OnboardingStepUpdateResponse:
    try:
        return await service.skip_step(
            current_user.id,
            step_name,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except InvalidOnboardingStepError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/complete", response_model=OnboardingStepUpdateResponse)
async def complete_onboarding(
    service: OnboardingServiceDep,
    current_user: RequireSalesOrAdminDep,
    request: Request,
) -> OnboardingStepUpdateResponse:
    return await service.complete_onboarding(
        current_user.id, actor_role=current_user.role.value, http_request=request
    )


@router.get("/readiness", response_model=OnboardingReadinessResponse)
async def get_onboarding_readiness(
    service: OnboardingServiceDep,
    current_user: RequireSalesReviewerOrAdminDep,
    request: Request,
) -> OnboardingReadinessResponse:
    """System-wide readiness snapshot — not scoped to a single user.

    'beta_ready' is a technical signal only; it never means real outreach
    use has been legally cleared.
    """
    return await service.get_readiness(
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        http_request=request,
    )
