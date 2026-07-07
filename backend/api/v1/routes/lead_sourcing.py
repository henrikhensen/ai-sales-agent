"""Lead Sourcing Engine: finds, scores, and stages candidates for review.

Pure discovery and scoring endpoints — nothing here sends an email,
contacts anyone, starts a Sales Workflow, or creates an external draft. No
LinkedIn scraping, no scraping behind a login, no CAPTCHA bypass. A
candidate only ever becomes a CRM Company/Lead through an explicit
``/approve`` call.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from backend.api.dependencies.auth import (
    RequireAdminUserDep,
    RequireSalesOrAdminDep,
    RequireSalesReviewerOrAdminDep,
)
from backend.api.v1.dependencies import AuditLogServiceDep, LeadSourcingServiceDep
from backend.application.lead_sourcing.schemas import (
    ApproveLeadCandidateRequest,
    ApproveLeadCandidateResponse,
    CreateLeadSourcingCampaignRequest,
    ImportLeadCandidatesRequest,
    ImportLeadCandidatesResponse,
    LeadCandidateListResponse,
    LeadCandidateResponse,
    LeadSourcingCampaignListResponse,
    LeadSourcingCampaignResponse,
    LeadSourcingProviderStatusResponse,
    LeadSourcingRunListResponse,
    LeadSourcingRunResponse,
    RejectLeadCandidateRequest,
    RejectLeadCandidateResponse,
    StartLeadSourcingRunRequest,
    StartLeadSourcingRunResponse,
    UpdateLeadSourcingCampaignRequest,
)
from backend.domain.exceptions import (
    LeadCandidateBlockedError,
    LeadCandidateNotFoundError,
    LeadSourcingCampaignNotFoundError,
    LeadSourcingProviderNotConfiguredError,
    LeadSourcingRunNotFoundError,
)
from backend.shared.rate_limit import rate_limit

router = APIRouter(prefix="/lead-sourcing", tags=["lead-sourcing"])


@router.get("/status", response_model=LeadSourcingProviderStatusResponse)
async def get_lead_sourcing_status(
    service: LeadSourcingServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> LeadSourcingProviderStatusResponse:
    """Report the configured provider, safe-mode status, and current
    limits. Read-only, any active admin, sales, or reviewer account."""
    return await service.get_provider_status()


# -- campaigns ------------------------------------------------------------------


@router.get("/campaigns", response_model=LeadSourcingCampaignListResponse)
async def list_campaigns(
    service: LeadSourcingServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
) -> LeadSourcingCampaignListResponse:
    return await service.list_campaigns(limit=limit, offset=offset, status=status_filter)


@router.post(
    "/campaigns",
    response_model=LeadSourcingCampaignResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_campaign(
    payload: CreateLeadSourcingCampaignRequest,
    service: LeadSourcingServiceDep,
    current_user: RequireSalesOrAdminDep,
    audit: AuditLogServiceDep,
    request: Request,
) -> LeadSourcingCampaignResponse:
    created = await service.create_campaign(payload, created_by_user_id=current_user.id)
    await audit.record(
        action="lead_sourcing_campaign_created",
        result="success",
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        entity_type="lead_sourcing_campaign",
        entity_id=created.id,
        request=request,
    )
    return created


@router.get("/campaigns/{campaign_id}", response_model=LeadSourcingCampaignResponse)
async def get_campaign(
    campaign_id: UUID,
    service: LeadSourcingServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> LeadSourcingCampaignResponse:
    try:
        return await service.get_campaign(campaign_id)
    except LeadSourcingCampaignNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/campaigns/{campaign_id}", response_model=LeadSourcingCampaignResponse)
async def update_campaign(
    campaign_id: UUID,
    payload: UpdateLeadSourcingCampaignRequest,
    service: LeadSourcingServiceDep,
    current_user: RequireSalesOrAdminDep,
    audit: AuditLogServiceDep,
    request: Request,
) -> LeadSourcingCampaignResponse:
    try:
        updated = await service.update_campaign(campaign_id, payload)
    except LeadSourcingCampaignNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await audit.record(
        action="lead_sourcing_campaign_updated",
        result="success",
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        entity_type="lead_sourcing_campaign",
        entity_id=campaign_id,
        request=request,
    )
    return updated


@router.patch(
    "/campaigns/{campaign_id}/archive", response_model=LeadSourcingCampaignResponse
)
async def archive_campaign(
    campaign_id: UUID,
    service: LeadSourcingServiceDep,
    current_user: RequireAdminUserDep,
    audit: AuditLogServiceDep,
    request: Request,
) -> LeadSourcingCampaignResponse:
    try:
        updated = await service.archive_campaign(campaign_id)
    except LeadSourcingCampaignNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await audit.record(
        action="lead_sourcing_campaign_archived",
        result="success",
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        entity_type="lead_sourcing_campaign",
        entity_id=campaign_id,
        request=request,
    )
    return updated


# -- runs ------------------------------------------------------------------------


@router.post(
    "/campaigns/{campaign_id}/runs",
    response_model=StartLeadSourcingRunResponse,
    dependencies=[
        Depends(rate_limit("lead_sourcing_run", "rate_limit_lead_sourcing_runs_per_hour", 3600))
    ],
)
async def start_run(
    campaign_id: UUID,
    payload: StartLeadSourcingRunRequest,
    service: LeadSourcingServiceDep,
    current_user: RequireSalesOrAdminDep,
    request: Request,
) -> StartLeadSourcingRunResponse:
    """Start (or dry-run) a lead sourcing run for this campaign.

    Never sends an email, contacts anyone, starts a Sales Workflow, or
    creates an external draft — it only ever finds and scores candidates
    for later human review. Rate-limited per user
    (``RATE_LIMIT_LEAD_SOURCING_RUNS_PER_HOUR``).
    """
    if payload.campaign_id != campaign_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="campaign_id in the URL and request body must match.",
        )
    try:
        return await service.start_run(
            payload,
            started_by_user_id=current_user.id,
            started_by_role=current_user.role.value,
            http_request=request,
        )
    except LeadSourcingCampaignNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LeadSourcingProviderNotConfiguredError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/runs", response_model=LeadSourcingRunListResponse)
async def list_runs(
    service: LeadSourcingServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    campaign_id: UUID | None = Query(default=None),
) -> LeadSourcingRunListResponse:
    return await service.list_runs(limit=limit, offset=offset, campaign_id=campaign_id)


@router.get("/runs/{run_id}", response_model=LeadSourcingRunResponse)
async def get_run(
    run_id: UUID,
    service: LeadSourcingServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> LeadSourcingRunResponse:
    try:
        return await service.get_run(run_id)
    except LeadSourcingRunNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# -- candidates ----------------------------------------------------------------


@router.get("/candidates", response_model=LeadCandidateListResponse)
async def list_candidates(
    service: LeadSourcingServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    campaign_id: UUID | None = Query(default=None),
    sourcing_run_id: UUID | None = Query(default=None),
    review_status: str | None = Query(default=None),
) -> LeadCandidateListResponse:
    return await service.list_candidates(
        limit=limit,
        offset=offset,
        campaign_id=campaign_id,
        sourcing_run_id=sourcing_run_id,
        review_status=review_status,
    )


@router.get("/candidates/{candidate_id}", response_model=LeadCandidateResponse)
async def get_candidate(
    candidate_id: UUID,
    service: LeadSourcingServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> LeadCandidateResponse:
    try:
        return await service.get_candidate(candidate_id)
    except LeadCandidateNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/candidates/import",
    response_model=ImportLeadCandidatesResponse,
    dependencies=[
        Depends(rate_limit("lead_import", "rate_limit_lead_import_per_hour", 3600))
    ],
)
async def import_candidates(
    payload: ImportLeadCandidatesRequest,
    service: LeadSourcingServiceDep,
    current_user: RequireSalesOrAdminDep,
    request: Request,
) -> ImportLeadCandidatesResponse:
    """Import candidates from manually entered text (one per line:
    ``company_name, domain, website_url, notes``). Rate-limited per user
    (``RATE_LIMIT_LEAD_IMPORT_PER_HOUR``)."""
    try:
        return await service.import_candidates(
            payload,
            imported_by_user_id=current_user.id,
            imported_by_role=current_user.role.value,
            http_request=request,
        )
    except LeadSourcingCampaignNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/candidates/{candidate_id}/approve", response_model=ApproveLeadCandidateResponse
)
async def approve_candidate(
    candidate_id: UUID,
    payload: ApproveLeadCandidateRequest,
    service: LeadSourcingServiceDep,
    current_user: RequireSalesReviewerOrAdminDep,
    request: Request,
) -> ApproveLeadCandidateResponse:
    """Approve a candidate, creating (or linking) its CRM Company/Lead.

    Do-not-contact can never be bypassed: a blocked candidate cannot be
    approved. This never sends an email, starts a Sales Workflow, or
    creates an external draft.
    """
    try:
        return await service.approve_candidate(
            candidate_id,
            payload,
            approved_by_user_id=current_user.id,
            approved_by_role=current_user.role.value,
            http_request=request,
        )
    except LeadCandidateNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LeadCandidateBlockedError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/candidates/{candidate_id}/reject", response_model=RejectLeadCandidateResponse
)
async def reject_candidate(
    candidate_id: UUID,
    payload: RejectLeadCandidateRequest,
    service: LeadSourcingServiceDep,
    current_user: RequireSalesReviewerOrAdminDep,
    request: Request,
) -> RejectLeadCandidateResponse:
    try:
        return await service.reject_candidate(
            candidate_id,
            payload,
            rejected_by_user_id=current_user.id,
            rejected_by_role=current_user.role.value,
            http_request=request,
        )
    except LeadCandidateNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
