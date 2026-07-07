from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from backend.api.dependencies.auth import (
    RequireSalesOrAdminDep,
    RequireSalesReviewerOrAdminDep,
)
from backend.api.v1.dependencies import (
    EmailDraftIntegrationServiceDep,
    EmailDraftRepositoryDep,
    ReplyTrackingServiceDep,
)
from backend.api.v1.schemas.email_draft import EmailDraftRecordResponse
from backend.application.integrations.reply_schemas import SyncRepliesResponse
from backend.application.integrations.schemas import (
    CreateExternalEmailDraftResponse,
    ExternalEmailDraftStatusResponse,
)
from backend.domain.exceptions import EmailDraftNotFoundError

router = APIRouter(prefix="/email-drafts", tags=["email-drafts"])


@router.get("", response_model=list[EmailDraftRecordResponse])
async def list_email_drafts(
    repository: EmailDraftRepositoryDep,
    _current_user: RequireSalesReviewerOrAdminDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[EmailDraftRecordResponse]:
    """List saved email drafts, newest first.

    Read-only, any active admin, sales, or reviewer account: these are
    drafts awaiting human review only. No email is sent, and no status here
    ever represents that one was sent.
    """
    drafts = await repository.list(limit=limit, offset=offset)
    return [EmailDraftRecordResponse.model_validate(draft) for draft in drafts]


@router.post(
    "/{draft_id}/external-draft",
    response_model=CreateExternalEmailDraftResponse,
)
async def create_external_email_draft(
    draft_id: UUID,
    service: EmailDraftIntegrationServiceDep,
    current_user: RequireSalesOrAdminDep,
) -> CreateExternalEmailDraftResponse:
    """Create an external (Gmail/Outlook/Mock) draft for a saved email draft.

    Requires an active admin or sales account — reviewer accounts may not
    create external drafts. This is a conscious, one-draft-at-a-time
    action; it is never triggered automatically by the Sales Workflow.

    Refused before any provider is called if the draft is not
    ``approved``, or if its recipient/company matches an active
    do-not-contact entry — both checks happen in that order, and neither
    can be bypassed. Creating an external draft never sends anything: it
    only ever produces a draft sitting in the connected Gmail/Outlook
    account, exactly like the saved local draft.
    """
    try:
        return await service.create_external_draft(current_user.id, draft_id)
    except EmailDraftNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/{draft_id}/external-draft",
    response_model=ExternalEmailDraftStatusResponse,
)
async def get_external_email_draft_status(
    draft_id: UUID,
    service: EmailDraftIntegrationServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> ExternalEmailDraftStatusResponse:
    """Return the external draft metadata for a saved email draft, if any.

    Read-only, any active admin, sales, or reviewer account.
    """
    try:
        return await service.get_external_draft_status(draft_id)
    except EmailDraftNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/{draft_id}/replies/sync",
    response_model=SyncRepliesResponse,
)
async def sync_email_draft_replies(
    draft_id: UUID,
    service: ReplyTrackingServiceDep,
    current_user: RequireSalesOrAdminDep,
) -> SyncRepliesResponse:
    """Sync replies relevant to a single email draft's recipient.

    Requires an active admin or sales account. Only ever reads messages
    that already exist in the connected mailbox (Mock by default); never
    sends anything.
    """
    try:
        return await service.sync_replies_for_draft(current_user.id, draft_id)
    except EmailDraftNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
