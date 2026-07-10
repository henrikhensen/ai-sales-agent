"""Real-World Test Mode (Phase 34): controlled test runs against real
leads/websites and, optionally, real LLM output.

This never sends an email, never creates an external draft automatically,
and never bypasses Do-not-contact or Human Review — it only ever wraps
the existing Sales Workflow with extra bookkeeping/auditing. There is no
send endpoint anywhere in this router.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from backend.api.dependencies.auth import (
    RequireAdminUserDep,
    RequireSalesOrAdminDep,
    RequireSalesReviewerOrAdminDep,
)
from backend.api.v1.dependencies import RealWorldTestRunServiceDep
from backend.application.real_world_test.schemas import (
    CreateRealWorldTestRunRequest,
    RealWorldTestRunListResponse,
    RealWorldTestRunResponse,
)
from backend.domain.exceptions import (
    InvalidRealWorldTestRunTransitionError,
    RealWorldTestModeNotAllowedError,
    RealWorldTestRunNotFoundError,
)
from backend.shared.rate_limit import rate_limit

router = APIRouter(prefix="/real-world-test-runs", tags=["real-world-test"])

_real_world_test_rate_limit = Depends(
    rate_limit("real_world_test_run", "rate_limit_workflow_per_hour", 3600)
)


@router.post(
    "",
    response_model=RealWorldTestRunResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_real_world_test_rate_limit],
)
async def create_real_world_test_run(
    payload: CreateRealWorldTestRunRequest,
    service: RealWorldTestRunServiceDep,
    current_user: RequireSalesOrAdminDep,
    request: Request,
) -> RealWorldTestRunResponse:
    """Start a controlled Real-World Test Run. Admin or sales. Safe/mock
    mode by default; never sends an email or contacts anyone."""
    try:
        return await service.create_run(
            payload,
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except RealWorldTestModeNotAllowedError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=RealWorldTestRunListResponse)
async def list_real_world_test_runs(
    service: RealWorldTestRunServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
) -> RealWorldTestRunListResponse:
    return await service.list_runs(limit=limit, offset=offset, status=status_filter)


@router.get("/{run_id}", response_model=RealWorldTestRunResponse)
async def get_real_world_test_run(
    run_id: UUID,
    service: RealWorldTestRunServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> RealWorldTestRunResponse:
    try:
        return await service.get_run(run_id)
    except RealWorldTestRunNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{run_id}/abort", response_model=RealWorldTestRunResponse)
async def abort_real_world_test_run(
    run_id: UUID,
    service: RealWorldTestRunServiceDep,
    current_user: RequireAdminUserDep,
    request: Request,
) -> RealWorldTestRunResponse:
    """Abort a Real-World Test Run that has not yet reached a terminal
    status. Admin only."""
    try:
        return await service.abort_run(
            run_id,
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except RealWorldTestRunNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidRealWorldTestRunTransitionError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
