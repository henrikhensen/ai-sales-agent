"""Beta Test Sessions: structured tracking of manual beta testing rounds.

A session never activates a real provider, sends an email, or creates an
external draft automatically — it exists purely to make manual testing
measurable.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from backend.api.dependencies.auth import (
    RequireAdminUserDep,
    RequireSalesOrAdminDep,
    RequireSalesReviewerOrAdminDep,
)
from backend.api.v1.dependencies import BetaTestServiceDep
from backend.application.quality.beta_test_schemas import (
    BetaTestDashboardResponse,
    BetaTestSessionListResponse,
    BetaTestSessionResponse,
    CreateBetaTestSessionRequest,
)
from backend.domain.exceptions import (
    BetaTestSessionNotFoundError,
    InvalidBetaTestSessionTransitionError,
)
from backend.shared.rate_limit import rate_limit

router = APIRouter(prefix="/beta-test", tags=["beta-test"])

_beta_session_rate_limit = Depends(
    rate_limit("beta_test_session", "rate_limit_default_per_minute", 60)
)


@router.post(
    "/sessions",
    response_model=BetaTestSessionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_beta_session_rate_limit],
)
async def create_beta_test_session(
    payload: CreateBetaTestSessionRequest,
    service: BetaTestServiceDep,
    current_user: RequireSalesOrAdminDep,
    request: Request,
) -> BetaTestSessionResponse:
    """Create a Beta Test Session. Admin or sales. Tracking only — never
    activates a real provider or sends anything."""
    return await service.create_session(
        payload,
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        http_request=request,
    )


@router.get("/sessions", response_model=BetaTestSessionListResponse)
async def list_beta_test_sessions(
    service: BetaTestServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
) -> BetaTestSessionListResponse:
    return await service.list_sessions(limit=limit, offset=offset, status=status_filter)


@router.get("/sessions/{session_id}", response_model=BetaTestSessionResponse)
async def get_beta_test_session(
    session_id: UUID,
    service: BetaTestServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> BetaTestSessionResponse:
    try:
        return await service.get_session(session_id)
    except BetaTestSessionNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch(
    "/sessions/{session_id}/start",
    response_model=BetaTestSessionResponse,
    dependencies=[_beta_session_rate_limit],
)
async def start_beta_test_session(
    session_id: UUID,
    service: BetaTestServiceDep,
    current_user: RequireSalesOrAdminDep,
    request: Request,
) -> BetaTestSessionResponse:
    try:
        return await service.start_session(
            session_id,
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except BetaTestSessionNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidBetaTestSessionTransitionError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch(
    "/sessions/{session_id}/complete",
    response_model=BetaTestSessionResponse,
    dependencies=[_beta_session_rate_limit],
)
async def complete_beta_test_session(
    session_id: UUID,
    service: BetaTestServiceDep,
    current_user: RequireSalesOrAdminDep,
    request: Request,
) -> BetaTestSessionResponse:
    try:
        return await service.complete_session(
            session_id,
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except BetaTestSessionNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidBetaTestSessionTransitionError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/dashboard", response_model=BetaTestDashboardResponse)
async def get_beta_test_dashboard(
    service: BetaTestServiceDep,
    _current_user: RequireAdminUserDep,
) -> BetaTestDashboardResponse:
    """Aggregated Beta Test dashboard. Admin only — aggregates
    cross-session/cross-user quality and feedback data."""
    return await service.get_dashboard()
