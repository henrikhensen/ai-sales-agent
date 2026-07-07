from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from backend.api.dependencies.auth import (
    RequireSalesOrAdminDep,
    RequireSalesReviewerOrAdminDep,
)
from backend.api.v1.dependencies import (
    AuditLogServiceDep,
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
from backend.shared.rate_limit import rate_limit

router = APIRouter(prefix="/email-drafts", tags=["email-drafts"])

_external_draft_rate_limit = rate_limit(
    "external_draft", "rate_limit_external_draft_per_hour", 3600
)
_reply_sync_rate_limit = rate_limit(
    "reply_sync", "rate_limit_reply_sync_per_hour", 3600
)


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
    dependencies=[Depends(_external_draft_rate_limit)],
)
async def create_external_email_draft(
    draft_id: UUID,
    service: EmailDraftIntegrationServiceDep,
    current_user: RequireSalesOrAdminDep,
    audit: AuditLogServiceDep,
    request: Request,
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
    account, exactly like the saved local draft. Rate-limited per user
    (``RATE_LIMIT_EXTERNAL_DRAFT_PER_HOUR``).
    """
    await audit.record(
        action="external_draft_creation_started",
        result="started",
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        entity_type="email_draft",
        entity_id=draft_id,
        request=request,
    )
    try:
        result = await service.create_external_draft(current_user.id, draft_id)
    except EmailDraftNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if result.blocked:
        await audit.record(
            action="external_draft_creation_blocked",
            result="blocked",
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            entity_type="email_draft",
            entity_id=draft_id,
            reason=result.block_reason,
            request=request,
        )
    elif result.external_draft and result.external_draft.provider_status == "failed":
        await audit.record(
            action="external_draft_creation_failed",
            result="failed",
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            entity_type="email_draft",
            entity_id=draft_id,
            reason=result.external_draft.last_error,
            request=request,
        )
    else:
        await audit.record(
            action="external_draft_creation_succeeded",
            result="success",
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            entity_type="email_draft",
            entity_id=draft_id,
            metadata={"provider": result.external_draft.provider}
            if result.external_draft
            else None,
            request=request,
        )
    return result


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
    dependencies=[Depends(_reply_sync_rate_limit)],
)
async def sync_email_draft_replies(
    draft_id: UUID,
    service: ReplyTrackingServiceDep,
    current_user: RequireSalesOrAdminDep,
    audit: AuditLogServiceDep,
    request: Request,
) -> SyncRepliesResponse:
    """Sync replies relevant to a single email draft's recipient.

    Requires an active admin or sales account. Only ever reads messages
    that already exist in the connected mailbox (Mock by default); never
    sends anything. Rate-limited per user
    (``RATE_LIMIT_REPLY_SYNC_PER_HOUR``).
    """
    await audit.record(
        action="reply_sync_started",
        result="started",
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        entity_type="email_draft",
        entity_id=draft_id,
        request=request,
    )
    try:
        result = await service.sync_replies_for_draft(current_user.id, draft_id)
    except EmailDraftNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    await audit.record(
        action="reply_sync_completed",
        result="failed" if result.error else "success",
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        entity_type="email_draft",
        entity_id=draft_id,
        reason=result.error,
        metadata={"new_count": result.new_count, "duplicate_count": result.duplicate_count},
        request=request,
    )
    if result.do_not_contact_signals > 0:
        await audit.record(
            action="reply_unsubscribe_signal_detected",
            result="detected",
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            entity_type="email_draft",
            entity_id=draft_id,
            metadata={"count": result.do_not_contact_signals},
            request=request,
        )
    return result
