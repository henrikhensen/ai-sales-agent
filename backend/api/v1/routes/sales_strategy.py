"""ICP (Ideal Customer Profile) and Offer profile management.

Pure definition and scoring endpoints — nothing here sends an email,
contacts anyone, or scrapes external data (no LinkedIn scraping, no new
website fetches). Fit checks and offer previews only ever evaluate data
already supplied in the request.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status

from backend.api.dependencies.auth import (
    RequireAdminUserDep,
    RequireSalesOrAdminDep,
    RequireSalesReviewerOrAdminDep,
)
from backend.api.v1.dependencies import AuditLogServiceDep, ICPServiceDep, OfferServiceDep
from backend.application.sales_strategy.schemas import (
    CreateICPProfileRequest,
    CreateOfferProfileRequest,
    ICPFitCheckRequest,
    ICPFitCheckResponse,
    ICPProfileListResponse,
    ICPProfileResponse,
    OfferPreviewRequest,
    OfferPreviewResponse,
    OfferProfileListResponse,
    OfferProfileResponse,
    UpdateICPProfileRequest,
    UpdateOfferProfileRequest,
)
from backend.domain.exceptions import ICPProfileNotFoundError, OfferProfileNotFoundError

router = APIRouter(prefix="/sales-strategy", tags=["sales-strategy"])


# -- ICP ------------------------------------------------------------------------


@router.get("/icp", response_model=ICPProfileListResponse)
async def list_icp_profiles(
    service: ICPServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    active_only: bool = Query(default=False),
) -> ICPProfileListResponse:
    """List ICP profiles, newest first. Read-only, any active admin, sales,
    or reviewer account."""
    return await service.list(limit=limit, offset=offset, active_only=active_only)


@router.post(
    "/icp", response_model=ICPProfileResponse, status_code=status.HTTP_201_CREATED
)
async def create_icp_profile(
    payload: CreateICPProfileRequest,
    service: ICPServiceDep,
    current_user: RequireSalesOrAdminDep,
    audit: AuditLogServiceDep,
    request: Request,
) -> ICPProfileResponse:
    """Create a new ICP profile. Requires an active admin or sales account."""
    created = await service.create(payload, created_by_user_id=current_user.id)
    await audit.record(
        action="icp_profile_created",
        result="success",
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        entity_type="icp_profile",
        entity_id=created.id,
        request=request,
    )
    return created


@router.get("/icp/{icp_id}", response_model=ICPProfileResponse)
async def get_icp_profile(
    icp_id: UUID,
    service: ICPServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> ICPProfileResponse:
    """Return a single ICP profile. Read-only, any active admin, sales, or
    reviewer account."""
    try:
        return await service.get(icp_id)
    except ICPProfileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/icp/{icp_id}", response_model=ICPProfileResponse)
async def update_icp_profile(
    icp_id: UUID,
    payload: UpdateICPProfileRequest,
    service: ICPServiceDep,
    current_user: RequireSalesOrAdminDep,
    audit: AuditLogServiceDep,
    request: Request,
) -> ICPProfileResponse:
    """Partially update an ICP profile. Requires an active admin or sales
    account. Only fields present in the request body are changed."""
    try:
        updated = await service.update(icp_id, payload)
    except ICPProfileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await audit.record(
        action="icp_profile_updated",
        result="success",
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        entity_type="icp_profile",
        entity_id=icp_id,
        request=request,
    )
    return updated


@router.patch("/icp/{icp_id}/deactivate", response_model=ICPProfileResponse)
async def deactivate_icp_profile(
    icp_id: UUID,
    service: ICPServiceDep,
    current_user: RequireAdminUserDep,
    audit: AuditLogServiceDep,
    request: Request,
) -> ICPProfileResponse:
    """Deactivate an ICP profile. Admin only."""
    try:
        updated = await service.deactivate(icp_id)
    except ICPProfileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await audit.record(
        action="icp_profile_deactivated",
        result="success",
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        entity_type="icp_profile",
        entity_id=icp_id,
        request=request,
    )
    return updated


@router.post("/icp/check-fit", response_model=ICPFitCheckResponse)
async def check_icp_fit(
    payload: ICPFitCheckRequest,
    service: ICPServiceDep,
    current_user: RequireSalesReviewerOrAdminDep,
    audit: AuditLogServiceDep,
    request: Request,
) -> ICPFitCheckResponse:
    """Score ad-hoc company/lead data against one ICP profile.

    Read-only, any active admin, sales, or reviewer account. Only ever
    evaluates the data supplied in the request — never fetches or scrapes
    anything new.
    """
    try:
        result = await service.check_fit(payload)
    except ICPProfileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await audit.record(
        action="icp_fit_check_executed",
        result="success",
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        entity_type="icp_profile",
        entity_id=payload.icp_profile_id,
        metadata={"fit_score": result.fit_score, "fit_level": result.fit_level},
        request=request,
    )
    return result


# -- Offer ------------------------------------------------------------------------


@router.get("/offers", response_model=OfferProfileListResponse)
async def list_offer_profiles(
    service: OfferServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    active_only: bool = Query(default=False),
) -> OfferProfileListResponse:
    """List offer profiles, newest first. Read-only, any active admin,
    sales, or reviewer account."""
    return await service.list(limit=limit, offset=offset, active_only=active_only)


@router.post(
    "/offers",
    response_model=OfferProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_offer_profile(
    payload: CreateOfferProfileRequest,
    service: OfferServiceDep,
    current_user: RequireSalesOrAdminDep,
    audit: AuditLogServiceDep,
    request: Request,
) -> OfferProfileResponse:
    """Create a new offer profile. Requires an active admin or sales account."""
    created = await service.create(payload, created_by_user_id=current_user.id)
    await audit.record(
        action="offer_profile_created",
        result="success",
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        entity_type="offer_profile",
        entity_id=created.id,
        request=request,
    )
    return created


@router.get("/offers/{offer_id}", response_model=OfferProfileResponse)
async def get_offer_profile(
    offer_id: UUID,
    service: OfferServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> OfferProfileResponse:
    """Return a single offer profile. Read-only, any active admin, sales,
    or reviewer account."""
    try:
        return await service.get(offer_id)
    except OfferProfileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/offers/{offer_id}", response_model=OfferProfileResponse)
async def update_offer_profile(
    offer_id: UUID,
    payload: UpdateOfferProfileRequest,
    service: OfferServiceDep,
    current_user: RequireSalesOrAdminDep,
    audit: AuditLogServiceDep,
    request: Request,
) -> OfferProfileResponse:
    """Partially update an offer profile. Requires an active admin or
    sales account. Only fields present in the request body are changed."""
    try:
        updated = await service.update(offer_id, payload)
    except OfferProfileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await audit.record(
        action="offer_profile_updated",
        result="success",
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        entity_type="offer_profile",
        entity_id=offer_id,
        request=request,
    )
    return updated


@router.patch("/offers/{offer_id}/deactivate", response_model=OfferProfileResponse)
async def deactivate_offer_profile(
    offer_id: UUID,
    service: OfferServiceDep,
    current_user: RequireAdminUserDep,
    audit: AuditLogServiceDep,
    request: Request,
) -> OfferProfileResponse:
    """Deactivate an offer profile. Admin only."""
    try:
        updated = await service.deactivate(offer_id)
    except OfferProfileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await audit.record(
        action="offer_profile_deactivated",
        result="success",
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        entity_type="offer_profile",
        entity_id=offer_id,
        request=request,
    )
    return updated


@router.post("/offers/preview", response_model=OfferPreviewResponse)
async def preview_offer(
    payload: OfferPreviewRequest,
    service: OfferServiceDep,
    current_user: RequireSalesReviewerOrAdminDep,
    audit: AuditLogServiceDep,
    request: Request,
) -> OfferPreviewResponse:
    """Preview how an offer would be positioned in an email draft.

    Read-only, any active admin, sales, or reviewer account. Never
    fabricates a case study, guarantees an outcome, or hides a missing
    proof point.
    """
    try:
        result = await service.preview(payload.offer_profile_id)
    except OfferProfileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await audit.record(
        action="offer_preview_executed",
        result="success",
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        entity_type="offer_profile",
        entity_id=payload.offer_profile_id,
        request=request,
    )
    return result
