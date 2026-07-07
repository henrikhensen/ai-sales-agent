from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from backend.api.dependencies.auth import (
    RequireReviewerOrAdminDep,
    RequireSalesReviewerOrAdminDep,
)
from backend.api.v1.dependencies import AuditLogServiceDep, ReviewServiceDep
from backend.api.v1.schemas.review import (
    EmailDraftReviewStatusResponse,
    EmailDraftReviewStatusUpdateRequest,
    ReviewEventListResponse,
    ReviewEventResponse,
    WorkflowCommentRequest,
    WorkflowCommentResponse,
)
from backend.domain.entities.user import User
from backend.domain.exceptions import (
    DoNotContactBlockedError,
    EmailDraftNotFoundError,
    WorkflowRunNotFoundError,
)

router = APIRouter(prefix="/reviews", tags=["reviews"])


def _resolve_reviewer_name(reviewer_name: str | None, current_user: User) -> str | None:
    """Default ``reviewer_name`` to the logged-in user's name or email.

    Purely a convenience: an explicit ``reviewer_name`` in the request
    always wins over the caller's own identity.
    """
    if reviewer_name is not None:
        return reviewer_name
    return current_user.full_name or current_user.email


@router.post(
    "/email-drafts/{email_draft_id}/status",
    response_model=EmailDraftReviewStatusResponse,
)
async def update_email_draft_review_status(
    email_draft_id: UUID,
    payload: EmailDraftReviewStatusUpdateRequest,
    service: ReviewServiceDep,
    current_user: RequireReviewerOrAdminDep,
    audit: AuditLogServiceDep,
    request: Request,
) -> EmailDraftReviewStatusResponse:
    """Change an email draft's internal review status.

    Requires an active reviewer or admin account — sales accounts cannot
    change an email draft's review status at all. This is an internal
    review marker only. Setting ``review_status`` to ``approved`` never
    sends the email or makes contact — any actual outreach remains a
    separate, manual step outside this system. If ``reviewer_name`` is
    omitted, it defaults to the logged-in user's name or email.

    Approving a draft whose company matches an active do-not-contact entry
    is refused with a 409 — opt-out takes precedence over review approval.
    """
    try:
        draft = await service.set_email_draft_review_status(
            email_draft_id,
            review_status=payload.review_status,
            reviewer_name=_resolve_reviewer_name(payload.reviewer_name, current_user),
            comment=payload.comment,
        )
    except EmailDraftNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DoNotContactBlockedError as exc:
        await audit.record(
            action="review_blocked",
            result="blocked",
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            entity_type="email_draft",
            entity_id=email_draft_id,
            reason=f"do-not-contact match ({exc.matched_by})",
            request=request,
        )
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=(
                "This email draft cannot be approved: its company matches an "
                f"active do-not-contact entry (matched by {exc.matched_by}). "
                "Do-not-contact takes precedence over review approval."
            ),
        ) from exc

    if payload.review_status.value in ("approved", "rejected"):
        await audit.record(
            action=f"review_{payload.review_status.value}",
            result="success",
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            entity_type="email_draft",
            entity_id=email_draft_id,
            request=request,
        )

    return EmailDraftReviewStatusResponse(
        email_draft_id=draft.id,
        review_status=draft.review_status,
        reviewer_name=draft.reviewer_name,
        review_comment=draft.review_comment,
        reviewed_at=draft.reviewed_at,
    )


@router.get(
    "/email-drafts/{email_draft_id}/events",
    response_model=ReviewEventListResponse,
)
async def list_email_draft_review_events(
    email_draft_id: UUID,
    service: ReviewServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> ReviewEventListResponse:
    """List the audit trail for a single email draft, newest first.

    Read-only. Any active admin, reviewer, or sales account may read it.
    """
    try:
        events = await service.list_email_draft_events(email_draft_id)
    except EmailDraftNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return ReviewEventListResponse(
        items=[ReviewEventResponse.model_validate(event) for event in events]
    )


@router.post(
    "/workflows/{workflow_id}/comment",
    response_model=WorkflowCommentResponse,
)
async def add_workflow_review_comment(
    workflow_id: UUID,
    payload: WorkflowCommentRequest,
    service: ReviewServiceDep,
    current_user: RequireSalesReviewerOrAdminDep,
) -> WorkflowCommentResponse:
    """Add a review comment to a workflow run.

    Any active admin, reviewer, or sales account may comment. Comment-only:
    never changes the run's review status, never sends an email, and never
    makes contact. If ``reviewer_name`` is omitted, it defaults to the
    logged-in user's name or email.
    """
    try:
        event = await service.add_workflow_comment(
            workflow_id,
            reviewer_name=_resolve_reviewer_name(payload.reviewer_name, current_user),
            comment=payload.comment,
        )
    except WorkflowRunNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return WorkflowCommentResponse(workflow_id=workflow_id, event_id=event.id)


@router.get(
    "/workflows/{workflow_id}/events",
    response_model=ReviewEventListResponse,
)
async def list_workflow_review_events(
    workflow_id: UUID,
    service: ReviewServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> ReviewEventListResponse:
    """List the audit trail for a single workflow run, newest first.

    Read-only. Any active admin, reviewer, or sales account may read it.
    """
    try:
        events = await service.list_workflow_events(workflow_id)
    except WorkflowRunNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return ReviewEventListResponse(
        items=[ReviewEventResponse.model_validate(event) for event in events]
    )
