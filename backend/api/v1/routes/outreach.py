"""Outreach Campaign Queue: collects already-qualified leads into
prioritized, campaign-scoped queues for human review.

Pure queue-management and internal-preparation endpoints — nothing here
sends an email, contacts anyone, or creates an external (Gmail/Outlook)
draft. There is no send endpoint anywhere in this router.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from backend.api.dependencies.auth import (
    RequireSalesOrAdminDep,
    RequireSalesReviewerOrAdminDep,
)
from backend.api.v1.dependencies import AuditLogServiceDep, OutreachQueueServiceDep
from backend.application.outreach.schemas import (
    BuildOutreachQueueRequest,
    BuildOutreachQueueResponse,
    CreateOutreachCampaignRequest,
    OutreachCampaignListResponse,
    OutreachCampaignResponse,
    OutreachQueueDashboardResponse,
    OutreachQueueItemListResponse,
    OutreachQueueItemResponse,
    OutreachQueueStatusResponse,
    PrepareQueueBatchRequest,
    PrepareQueueBatchResponse,
    PrepareQueueItemWorkflowRequest,
    PrepareQueueItemWorkflowResponse,
    UpdateOutreachCampaignRequest,
    UpdateOutreachCampaignStatusRequest,
    UpdateQueueItemStatusRequest,
    UpdateQueueItemStatusResponse,
)
from backend.domain.exceptions import (
    InvalidOutreachQueueStatusTransitionError,
    OutreachCampaignNotFoundError,
    OutreachQueueItemBlockedError,
    OutreachQueueItemNotFoundError,
)
from backend.shared.rate_limit import rate_limit

router = APIRouter(prefix="/outreach", tags=["outreach"])

_queue_rate_limit = Depends(
    rate_limit("outreach_queue", "rate_limit_outreach_queue_per_hour", 3600)
)
_batch_rate_limit = Depends(
    rate_limit("outreach_batch_prep", "rate_limit_outreach_batch_prep_per_hour", 3600)
)


@router.get("/status", response_model=OutreachQueueStatusResponse)
async def get_status(
    service: OutreachQueueServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> OutreachQueueStatusResponse:
    return await service.get_status()


@router.get("/dashboard", response_model=OutreachQueueDashboardResponse)
async def get_dashboard(
    service: OutreachQueueServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> OutreachQueueDashboardResponse:
    return await service.get_dashboard()


# -- campaigns --------------------------------------------------------------------


@router.post("/campaigns", response_model=OutreachCampaignResponse)
async def create_campaign(
    payload: CreateOutreachCampaignRequest,
    service: OutreachQueueServiceDep,
    current_user: RequireSalesOrAdminDep,
    request: Request,
) -> OutreachCampaignResponse:
    """Create a campaign — only ever a named container/queue definition.
    Never contacts anyone by itself."""
    return await service.create_campaign(
        payload,
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        http_request=request,
    )


@router.get("/campaigns", response_model=OutreachCampaignListResponse)
async def list_campaigns(
    service: OutreachQueueServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    campaign_status: str | None = Query(default=None, alias="status"),
) -> OutreachCampaignListResponse:
    return await service.list_campaigns(limit=limit, offset=offset, status=campaign_status)


@router.get("/campaigns/{campaign_id}", response_model=OutreachCampaignResponse)
async def get_campaign(
    campaign_id: UUID,
    service: OutreachQueueServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> OutreachCampaignResponse:
    try:
        return await service.get_campaign(campaign_id)
    except OutreachCampaignNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/campaigns/{campaign_id}", response_model=OutreachCampaignResponse)
async def update_campaign(
    campaign_id: UUID,
    payload: UpdateOutreachCampaignRequest,
    service: OutreachQueueServiceDep,
    current_user: RequireSalesOrAdminDep,
    request: Request,
) -> OutreachCampaignResponse:
    try:
        return await service.update_campaign(
            campaign_id,
            payload,
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except OutreachCampaignNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch(
    "/campaigns/{campaign_id}/archive", response_model=OutreachCampaignResponse
)
async def archive_campaign(
    campaign_id: UUID,
    service: OutreachQueueServiceDep,
    current_user: RequireSalesOrAdminDep,
    request: Request,
) -> OutreachCampaignResponse:
    try:
        return await service.archive_campaign(
            campaign_id,
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except OutreachCampaignNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch(
    "/campaigns/{campaign_id}/status", response_model=OutreachCampaignResponse
)
async def set_campaign_status(
    campaign_id: UUID,
    payload: UpdateOutreachCampaignStatusRequest,
    service: OutreachQueueServiceDep,
    current_user: RequireSalesOrAdminDep,
    request: Request,
) -> OutreachCampaignResponse:
    """Change a campaign's lifecycle status. 'active' only ever means its
    queue may be built/prepared — it never triggers outreach by itself."""
    try:
        return await service.set_campaign_status(
            campaign_id,
            payload.status,
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except OutreachCampaignNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidOutreachQueueStatusTransitionError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/campaigns/{campaign_id}/build-queue",
    response_model=BuildOutreachQueueResponse,
    dependencies=[_queue_rate_limit],
)
async def build_queue(
    campaign_id: UUID,
    payload: BuildOutreachQueueRequest,
    service: OutreachQueueServiceDep,
    current_user: RequireSalesOrAdminDep,
    request: Request,
) -> BuildOutreachQueueResponse:
    """Build (or dry-run preview) a campaign's queue from existing Lead
    Qualification results. Never sends an email, contacts anyone, or starts
    a Sales Workflow — it only ever scores, filters, and sorts. Rate-limited
    per user (``RATE_LIMIT_OUTREACH_QUEUE_PER_HOUR``).
    """
    try:
        return await service.build_queue(
            campaign_id,
            payload,
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except OutreachCampaignNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/campaigns/{campaign_id}/prepare-batch",
    response_model=PrepareQueueBatchResponse,
    dependencies=[_batch_rate_limit],
)
async def prepare_batch(
    campaign_id: UUID,
    payload: PrepareQueueBatchRequest,
    service: OutreachQueueServiceDep,
    current_user: RequireSalesOrAdminDep,
    request: Request,
) -> PrepareQueueBatchResponse:
    """Prepare internal Sales Workflow runs/email drafts for several queue
    items at once. Never creates an external draft and never sends
    anything — reviewer accounts cannot start this (sales/admin only).
    Rate-limited per user (``RATE_LIMIT_OUTREACH_BATCH_PREP_PER_HOUR``).
    """
    try:
        return await service.prepare_batch(
            campaign_id,
            payload,
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except OutreachCampaignNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# -- queue ------------------------------------------------------------------------


@router.get("/queue", response_model=OutreachQueueItemListResponse)
async def list_queue_items(
    service: OutreachQueueServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    campaign_id: UUID | None = Query(default=None),
    queue_status: str | None = Query(default=None),
) -> OutreachQueueItemListResponse:
    return await service.list_queue_items(
        limit=limit, offset=offset, campaign_id=campaign_id, queue_status=queue_status
    )


@router.get("/queue/{queue_item_id}", response_model=OutreachQueueItemResponse)
async def get_queue_item(
    queue_item_id: UUID,
    service: OutreachQueueServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> OutreachQueueItemResponse:
    try:
        return await service.get_queue_item(queue_item_id)
    except OutreachQueueItemNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch(
    "/queue/{queue_item_id}/status", response_model=UpdateQueueItemStatusResponse
)
async def update_queue_item_status(
    queue_item_id: UUID,
    payload: UpdateQueueItemStatusRequest,
    service: OutreachQueueServiceDep,
    current_user: RequireSalesReviewerOrAdminDep,
    request: Request,
) -> UpdateQueueItemStatusResponse:
    """Manually move a queue item along a safe, validated transition.
    Leaving 'blocked' always re-verifies do-not-contact first and can never
    be bypassed; there is no 'sent' status."""
    try:
        return await service.update_queue_item_status(
            queue_item_id,
            payload,
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except OutreachQueueItemNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidOutreachQueueStatusTransitionError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except OutreachQueueItemBlockedError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/queue/{queue_item_id}/prepare-workflow",
    response_model=PrepareQueueItemWorkflowResponse,
    dependencies=[_queue_rate_limit],
)
async def prepare_queue_item_workflow(
    queue_item_id: UUID,
    payload: PrepareQueueItemWorkflowRequest,
    service: OutreachQueueServiceDep,
    current_user: RequireSalesOrAdminDep,
    request: Request,
) -> PrepareQueueItemWorkflowResponse:
    """Prepare an internal Sales Workflow run / email draft for one queue
    item. Never sends an email, never creates an external draft, and never
    bypasses do-not-contact. Rate-limited per user
    (``RATE_LIMIT_OUTREACH_QUEUE_PER_HOUR``).
    """
    try:
        return await service.prepare_queue_item_workflow(
            queue_item_id,
            payload,
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except OutreachQueueItemNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except OutreachQueueItemBlockedError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InvalidOutreachQueueStatusTransitionError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
