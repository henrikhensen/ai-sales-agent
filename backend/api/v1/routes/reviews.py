from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from backend.api.dependencies.auth import OptionalCurrentUserDep
from backend.api.v1.dependencies import ReviewServiceDep
from backend.api.v1.schemas.review import (
    EmailDraftReviewStatusResponse,
    EmailDraftReviewStatusUpdateRequest,
    ReviewEventListResponse,
    ReviewEventResponse,
    WorkflowCommentRequest,
    WorkflowCommentResponse,
)
from backend.domain.entities.user import User
from backend.domain.exceptions import EmailDraftNotFoundError, WorkflowRunNotFoundError

router = APIRouter(prefix="/reviews", tags=["reviews"])


def _resolve_reviewer_name(reviewer_name: str | None, current_user: User | None) -> str | None:
    """Default ``reviewer_name`` to the logged-in user, if one is present.

    Purely a convenience: an explicit ``reviewer_name`` in the request
    always wins, and an anonymous (unauthenticated) request behaves exactly
    as before this phase.
    """
    if reviewer_name is not None:
        return reviewer_name
    if current_user is not None:
        return current_user.full_name or current_user.email
    return None


@router.post(
    "/email-drafts/{email_draft_id}/status",
    response_model=EmailDraftReviewStatusResponse,
)
async def update_email_draft_review_status(
    email_draft_id: UUID,
    payload: EmailDraftReviewStatusUpdateRequest,
    service: ReviewServiceDep,
    current_user: OptionalCurrentUserDep,
) -> EmailDraftReviewStatusResponse:
    """Change an email draft's internal review status.

    This is an internal review marker only. Setting ``review_status`` to
    ``approved`` never sends the email or makes contact — any actual
    outreach remains a separate, manual step outside this system. If
    ``reviewer_name`` is omitted and the caller is authenticated, it
    defaults to the logged-in user's name or email; authentication is not
    required.
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
) -> ReviewEventListResponse:
    """List the audit trail for a single email draft, newest first. Read-only."""
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
    current_user: OptionalCurrentUserDep,
) -> WorkflowCommentResponse:
    """Add a review comment to a workflow run.

    Comment-only: never changes the run's review status, never sends an
    email, and never makes contact. If ``reviewer_name`` is omitted and the
    caller is authenticated, it defaults to the logged-in user's name or
    email; authentication is not required.
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
) -> ReviewEventListResponse:
    """List the audit trail for a single workflow run, newest first. Read-only."""
    try:
        events = await service.list_workflow_events(workflow_id)
    except WorkflowRunNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return ReviewEventListResponse(
        items=[ReviewEventResponse.model_validate(event) for event in events]
    )
