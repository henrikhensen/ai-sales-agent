"""Controlled Outreach Dispatch: processes a single, already-approved
Outreach Queue item into either a controlled external draft, or — only
when explicitly enabled and confirmed by a human — a manually confirmed
send.

There is no general send endpoint, no reply-send endpoint, and no batch
send endpoint anywhere in this router — every mutating action addresses
exactly one queue item / one dispatch attempt, and requires an existing
Human Review-approved email draft plus an explicit compliance
acknowledgement and final confirmation before any provider action runs.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from backend.api.dependencies.auth import (
    RequireSalesOrAdminDep,
    RequireSalesReviewerOrAdminDep,
)
from backend.api.v1.dependencies import OutreachDispatchServiceDep
from backend.application.outreach.dispatch_schemas import (
    CancelDispatchRequest,
    CancelDispatchResponse,
    ConfirmDispatchRequest,
    ConfirmDispatchResponse,
    CreateDispatchRequest,
    CreateDispatchResponse,
    DispatchComplianceAckRequest,
    DispatchComplianceAckResponse,
    DispatchDashboardResponse,
    DispatchReadinessCheckRequest,
    DispatchReadinessCheckResponse,
    OutreachDispatchListResponse,
    OutreachDispatchResponse,
)
from backend.domain.exceptions import (
    OutreachDispatchBlockedError,
    OutreachDispatchNotFoundError,
    OutreachDispatchNotReadyError,
    OutreachQueueItemNotFoundError,
)
from backend.shared.rate_limit import rate_limit

router = APIRouter(prefix="/outreach", tags=["outreach-dispatch"])

_dispatch_rate_limit = Depends(
    rate_limit("outreach_dispatch", "rate_limit_outreach_dispatch_per_hour", 3600)
)


@router.get("/dispatch/dashboard", response_model=DispatchDashboardResponse)
async def get_dispatch_dashboard(
    service: OutreachDispatchServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> DispatchDashboardResponse:
    return await service.get_dashboard()


@router.get("/dispatch", response_model=OutreachDispatchListResponse)
async def list_dispatches(
    service: OutreachDispatchServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    queue_item_id: UUID | None = Query(default=None),
    dispatch_status: str | None = Query(default=None),
) -> OutreachDispatchListResponse:
    return await service.list_dispatches(
        limit=limit, offset=offset, queue_item_id=queue_item_id, dispatch_status=dispatch_status
    )


@router.get("/dispatch/{dispatch_id}", response_model=OutreachDispatchResponse)
async def get_dispatch(
    dispatch_id: UUID,
    service: OutreachDispatchServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> OutreachDispatchResponse:
    try:
        return await service.get_dispatch(dispatch_id)
    except OutreachDispatchNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/queue/{queue_item_id}/dispatch/readiness",
    response_model=DispatchReadinessCheckResponse,
    dependencies=[_dispatch_rate_limit],
)
async def check_dispatch_readiness(
    queue_item_id: UUID,
    payload: DispatchReadinessCheckRequest,
    service: OutreachDispatchServiceDep,
    current_user: RequireSalesOrAdminDep,
) -> DispatchReadinessCheckResponse:
    """Report whether a queue item is ready for dispatch. Pure check —
    never calls a provider's draft/send action and never persists
    anything."""
    try:
        return await service.check_readiness(
            queue_item_id, payload, actor_user_id=current_user.id
        )
    except OutreachQueueItemNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/queue/{queue_item_id}/dispatch",
    response_model=CreateDispatchResponse,
    dependencies=[_dispatch_rate_limit],
)
async def create_dispatch(
    queue_item_id: UUID,
    payload: CreateDispatchRequest,
    service: OutreachDispatchServiceDep,
    current_user: RequireSalesOrAdminDep,
    request: Request,
) -> CreateDispatchResponse:
    """Create a controlled dispatch attempt for one queue item (idempotent
    — reuses an existing in-flight attempt rather than duplicating it).
    Never creates an external draft or sends anything by itself; that only
    ever happens after ``/compliance-ack`` and ``/confirm``.
    """
    try:
        return await service.create_dispatch(
            queue_item_id,
            payload,
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except OutreachQueueItemNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/dispatch/{dispatch_id}/compliance-ack",
    response_model=DispatchComplianceAckResponse,
)
async def acknowledge_dispatch_compliance(
    dispatch_id: UUID,
    payload: DispatchComplianceAckRequest,
    service: OutreachDispatchServiceDep,
    current_user: RequireSalesOrAdminDep,
    request: Request,
) -> DispatchComplianceAckResponse:
    try:
        return await service.acknowledge_compliance(
            dispatch_id,
            payload,
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except OutreachDispatchNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except OutreachDispatchNotReadyError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except OutreachDispatchBlockedError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/dispatch/{dispatch_id}/confirm",
    response_model=ConfirmDispatchResponse,
    dependencies=[_dispatch_rate_limit],
)
async def confirm_dispatch(
    dispatch_id: UUID,
    payload: ConfirmDispatchRequest,
    service: OutreachDispatchServiceDep,
    current_user: RequireSalesOrAdminDep,
    request: Request,
) -> ConfirmDispatchResponse:
    """Record final confirmation and — only if every gate still passes —
    trigger the single controlled action (external draft creation, or a
    manually confirmed send strictly gated behind
    ``OUTREACH_DISPATCH_ENABLE_REAL_SEND``). Never bypasses do-not-contact
    or Human Review approval; reviewer accounts cannot call this endpoint.
    """
    try:
        return await service.confirm(
            dispatch_id,
            payload,
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except OutreachDispatchNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except OutreachQueueItemNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except OutreachDispatchNotReadyError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except OutreachDispatchBlockedError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/dispatch/{dispatch_id}/cancel", response_model=CancelDispatchResponse)
async def cancel_dispatch(
    dispatch_id: UUID,
    payload: CancelDispatchRequest,
    service: OutreachDispatchServiceDep,
    current_user: RequireSalesOrAdminDep,
    request: Request,
) -> CancelDispatchResponse:
    try:
        return await service.cancel(
            dispatch_id,
            payload,
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except OutreachDispatchNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except OutreachDispatchNotReadyError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
