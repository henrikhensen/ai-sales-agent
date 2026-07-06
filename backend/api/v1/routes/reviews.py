from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from backend.api.v1.dependencies import ReviewServiceDep
from backend.api.v1.schemas.review import (
    EmailDraftReviewStatusResponse,
    EmailDraftReviewStatusUpdateRequest,
    ReviewEventListResponse,
    ReviewEventResponse,
    WorkflowCommentRequest,
    WorkflowCommentResponse,
)
from backend.domain.exceptions import EmailDraftNotFoundError, WorkflowRunNotFoundError

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post(
    "/email-drafts/{email_draft_id}/status",
    response_model=EmailDraftReviewStatusResponse,
)
async def update_email_draft_review_status(
    email_draft_id: UUID,
    payload: EmailDraftReviewStatusUpdateRequest,
    service: ReviewServiceDep,
) -> EmailDraftReviewStatusResponse:
    """Change an email draft's internal review status.

    This is an internal review marker only. Setting ``review_status`` to
    ``approved`` never sends the email or makes contact — any actual
    outreach remains a separate, manual step outside this system.
    """
    try:
        draft = await service.set_email_draft_review_status(
            email_draft_id,
            review_status=payload.review_status,
            reviewer_name=payload.reviewer_name,
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
) -> WorkflowCommentResponse:
    """Add a review comment to a workflow run.

    Comment-only: never changes the run's review status, never sends an
    email, and never makes contact.
    """
    try:
        event = await service.add_workflow_comment(
            workflow_id,
            reviewer_name=payload.reviewer_name,
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
