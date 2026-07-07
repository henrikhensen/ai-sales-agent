from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from backend.api.dependencies.auth import (
    RequireSalesOrAdminDep,
    RequireSalesReviewerOrAdminDep,
)
from backend.api.v1.dependencies import (
    CreateLeadUseCaseDep,
    LeadRepositoryDep,
    ReplyTrackingServiceDep,
    UpdateLeadStatusUseCaseDep,
)
from backend.api.v1.schemas.lead import LeadCreate, LeadResponse, LeadStatusUpdate
from backend.application.integrations.reply_schemas import (
    ReplyListResponse,
    SyncRepliesResponse,
)
from backend.application.use_cases.create_lead import CreateLeadCommand
from backend.application.use_cases.update_lead_status import UpdateLeadStatusCommand
from backend.domain.exceptions import CompanyNotFoundError, LeadNotFoundError

router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    payload: LeadCreate,
    use_case: CreateLeadUseCaseDep,
    _current_user: RequireSalesOrAdminDep,
) -> LeadResponse:
    """Create a new lead for an existing company. Requires an active sales
    or admin account — reviewer accounts may read CRM data but not write it.
    """
    command = CreateLeadCommand(
        company_id=payload.company_id,
        source=payload.source,
        score=payload.score,
    )
    try:
        lead = await use_case.execute(command)
    except CompanyNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return LeadResponse.model_validate(lead)


@router.get("", response_model=list[LeadResponse])
async def list_leads(
    repository: LeadRepositoryDep,
    _current_user: RequireSalesReviewerOrAdminDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[LeadResponse]:
    """List leads, newest first. Read-only, any active admin, sales, or
    reviewer account.
    """
    leads = await repository.list(limit=limit, offset=offset)
    return [LeadResponse.model_validate(lead) for lead in leads]


@router.patch("/{lead_id}", response_model=LeadResponse)
async def update_lead_status(
    lead_id: UUID,
    payload: LeadStatusUpdate,
    use_case: UpdateLeadStatusUseCaseDep,
    _current_user: RequireSalesOrAdminDep,
) -> LeadResponse:
    """Update the status of an existing lead. Requires an active sales or
    admin account.
    """
    command = UpdateLeadStatusCommand(lead_id=lead_id, status=payload.status)
    try:
        lead = await use_case.execute(command)
    except LeadNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return LeadResponse.model_validate(lead)


@router.get("/{lead_id}/replies", response_model=ReplyListResponse)
async def list_lead_replies(
    lead_id: UUID,
    service: ReplyTrackingServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> ReplyListResponse:
    """List replies stored for a single lead, newest first.

    Read-only, any active admin, sales, or reviewer account.
    """
    return await service.list_lead_replies(lead_id, limit=limit, offset=offset)


@router.post("/{lead_id}/replies/sync", response_model=SyncRepliesResponse)
async def sync_lead_replies(
    lead_id: UUID,
    service: ReplyTrackingServiceDep,
    current_user: RequireSalesOrAdminDep,
) -> SyncRepliesResponse:
    """Sync replies for a single lead's known contact emails.

    Requires an active admin or sales account. Only ever reads messages
    that already exist in the connected mailbox (Mock by default); never
    sends anything.
    """
    try:
        return await service.sync_replies_for_lead(current_user.id, lead_id)
    except LeadNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
