"""Do-not-contact (opt-out) compliance: create, list, update, deactivate, and
check entries.

No endpoint here ever sends an email or contacts anyone — this only ever
manages opt-out records and reports whether a target is blocked. See
``backend.application.workflows.sales_workflow.SalesWorkflowService`` and
``backend.application.reviews.review_service.ReviewService`` for where a
positive check result actually stops outreach preparation and review
approval.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from backend.api.dependencies.auth import (
    RequireAdminUserDep,
    RequireSalesOrAdminDep,
    RequireSalesReviewerOrAdminDep,
)
from backend.api.v1.dependencies import DoNotContactServiceDep
from backend.application.compliance.schemas import (
    CreateDoNotContactRequest,
    DoNotContactCheckRequest,
    DoNotContactCheckResponse,
    DoNotContactEntryResponse,
    DoNotContactListResponse,
    UpdateDoNotContactRequest,
)
from backend.domain.exceptions import DoNotContactEntryNotFoundError

router = APIRouter(prefix="/compliance", tags=["compliance"])


@router.get("/do-not-contact", response_model=DoNotContactListResponse)
async def list_do_not_contact_entries(
    service: DoNotContactServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> DoNotContactListResponse:
    """List do-not-contact entries, newest first (active and inactive).

    Read-only, any active admin, sales, or reviewer account.
    """
    return await service.list_entries(limit=limit, offset=offset)


@router.post(
    "/do-not-contact",
    response_model=DoNotContactEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_do_not_contact_entry(
    payload: CreateDoNotContactRequest,
    service: DoNotContactServiceDep,
    current_user: RequireSalesOrAdminDep,
) -> DoNotContactEntryResponse:
    """Create a new do-not-contact entry.

    Requires an active admin or sales account. At least one of ``email``,
    ``domain``, or ``company_name`` is required. Creating an entry never
    sends an email or contacts anyone by itself — it only ever blocks
    future outreach preparation and review approval for the target.
    """
    return await service.create_entry(payload, created_by_user_id=current_user.id)


@router.patch(
    "/do-not-contact/{entry_id}",
    response_model=DoNotContactEntryResponse,
)
async def update_do_not_contact_entry(
    entry_id: UUID,
    payload: UpdateDoNotContactRequest,
    service: DoNotContactServiceDep,
    _current_user: RequireAdminUserDep,
) -> DoNotContactEntryResponse:
    """Partially update a do-not-contact entry. Admin only.

    Only fields present in the request body are changed.
    """
    try:
        return await service.update_entry(entry_id, payload)
    except DoNotContactEntryNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch(
    "/do-not-contact/{entry_id}/deactivate",
    response_model=DoNotContactEntryResponse,
)
async def deactivate_do_not_contact_entry(
    entry_id: UUID,
    service: DoNotContactServiceDep,
    _current_user: RequireAdminUserDep,
) -> DoNotContactEntryResponse:
    """Deactivate a do-not-contact entry. Admin only.

    An inactive entry no longer blocks anything — it is kept only for audit
    history. This never re-enables outreach automatically; it only stops
    this specific entry from blocking future checks.
    """
    try:
        return await service.deactivate_entry(entry_id)
    except DoNotContactEntryNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/do-not-contact/check", response_model=DoNotContactCheckResponse)
async def check_do_not_contact(
    payload: DoNotContactCheckRequest,
    service: DoNotContactServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> DoNotContactCheckResponse:
    """Check an email/domain/company_name against active opt-out entries.

    Read-only, any active admin, sales, or reviewer account. At least one
    of ``email``, ``domain``, or ``company_name`` is required. Never sends
    an email or contacts anyone by itself — it only ever reports whether a
    target is currently blocked.
    """
    return await service.check(
        email=payload.email, domain=payload.domain, company_name=payload.company_name
    )
