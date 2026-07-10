"""Lead Finder / Lead Discovery Run: a guided pipeline that finds
candidate companies for a target customer/region/offer, analyzes their
public websites, and scores fit — reusing the existing Lead Sourcing,
Lead Qualification, and Outreach Queue services rather than duplicating
any of their logic.

This never sends an email, never contacts anyone automatically, and
never bypasses Do-not-contact or Human Review. There is no send endpoint
anywhere in this router; draft creation is a separate, explicit action
that only ever prepares a draft for Human Review, exactly like the
existing Outreach Queue batch preparation it wraps.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from backend.api.dependencies.auth import (
    RequireSalesOrAdminDep,
    RequireSalesReviewerOrAdminDep,
)
from backend.api.v1.dependencies import LeadDiscoveryServiceDep
from backend.application.lead_discovery.schemas import (
    AddCandidateToQueueResponse,
    CreateLeadDiscoveryRunRequest,
    LeadDiscoveryRunDetailResponse,
    LeadDiscoveryRunListResponse,
    LeadDiscoveryRunResponse,
)
from backend.domain.exceptions import (
    ICPProfileNotFoundError,
    InvalidLeadDiscoveryRunTransitionError,
    LeadDiscoveryModeNotAllowedError,
    LeadDiscoveryRunNotFoundError,
    OfferProfileNotFoundError,
)
from backend.shared.rate_limit import rate_limit

router = APIRouter(prefix="/lead-discovery", tags=["lead-discovery"])

_lead_discovery_rate_limit = Depends(
    rate_limit("lead_discovery_run", "rate_limit_workflow_per_hour", 3600)
)


@router.post(
    "/runs",
    response_model=LeadDiscoveryRunResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_lead_discovery_rate_limit],
)
async def create_lead_discovery_run(
    payload: CreateLeadDiscoveryRunRequest,
    service: LeadDiscoveryServiceDep,
    current_user: RequireSalesOrAdminDep,
    request: Request,
) -> LeadDiscoveryRunResponse:
    """Create a new Lead Finder run. Admin or sales. Safe/mock mode by
    default; never sends an email or contacts anyone."""
    try:
        return await service.create_run(
            payload,
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except LeadDiscoveryModeNotAllowedError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except (OfferProfileNotFoundError, ICPProfileNotFoundError) as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/runs", response_model=LeadDiscoveryRunListResponse)
async def list_lead_discovery_runs(
    service: LeadDiscoveryServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
) -> LeadDiscoveryRunListResponse:
    return await service.list_runs(limit=limit, offset=offset, status=status_filter)


@router.get("/runs/{run_id}", response_model=LeadDiscoveryRunDetailResponse)
async def get_lead_discovery_run(
    run_id: UUID,
    service: LeadDiscoveryServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> LeadDiscoveryRunDetailResponse:
    try:
        return await service.get_run(run_id)
    except LeadDiscoveryRunNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/runs/{run_id}/run",
    response_model=LeadDiscoveryRunDetailResponse,
    dependencies=[_lead_discovery_rate_limit],
)
async def run_lead_discovery_pipeline(
    run_id: UUID,
    service: LeadDiscoveryServiceDep,
    current_user: RequireSalesOrAdminDep,
    request: Request,
) -> LeadDiscoveryRunDetailResponse:
    """Find candidates, analyze their websites, and score fit. Does not
    create any drafts — see the separate ``/create-drafts`` action."""
    try:
        return await service.run_pipeline(
            run_id,
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except LeadDiscoveryRunNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidLeadDiscoveryRunTransitionError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/runs/{run_id}/create-drafts",
    response_model=LeadDiscoveryRunDetailResponse,
    dependencies=[_lead_discovery_rate_limit],
)
async def create_drafts_for_qualified_candidates(
    run_id: UUID,
    service: LeadDiscoveryServiceDep,
    current_user: RequireSalesOrAdminDep,
    request: Request,
) -> LeadDiscoveryRunDetailResponse:
    """Prepare (never send) an email draft for every qualified candidate
    still awaiting one. A separate, explicit action from running the
    pipeline — the user reviews qualified leads first."""
    try:
        return await service.create_drafts_for_qualified_candidates(
            run_id,
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except LeadDiscoveryRunNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidLeadDiscoveryRunTransitionError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/runs/{run_id}/candidates/{candidate_id}/add-to-queue",
    response_model=AddCandidateToQueueResponse,
)
async def add_candidate_to_queue(
    run_id: UUID,
    candidate_id: UUID,
    service: LeadDiscoveryServiceDep,
    current_user: RequireSalesOrAdminDep,
    request: Request,
) -> AddCandidateToQueueResponse:
    """Manually add one specific (already-qualified) candidate to this
    run's review queue — a human override for a candidate that did not
    cross the automatic threshold. Do-not-contact/duplicate checks still
    apply; this can never queue a blocked candidate."""
    try:
        return await service.add_candidate_to_queue(
            run_id,
            candidate_id,
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except LeadDiscoveryRunNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
