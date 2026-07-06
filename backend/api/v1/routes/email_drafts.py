from fastapi import APIRouter, Query

from backend.api.dependencies.auth import RequireSalesReviewerOrAdminDep
from backend.api.v1.dependencies import EmailDraftRepositoryDep
from backend.api.v1.schemas.email_draft import EmailDraftRecordResponse

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
