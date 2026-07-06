"""API request/response schemas for Human Review & Approval.

Covers email draft review-status changes, workflow run comments, and the
resulting audit trail. No schema here ever represents that an email was
sent, a contact was made, or a meeting was booked — ``approved`` means only
that a human has internally reviewed the item.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.domain.enums import EmailDraftReviewStatus, ReviewEventType


def _clean_optional_text(value: object) -> object:
    """Trim strings and reject whitespace-only values; ``None`` passes through.

    Non-string values are returned unchanged so normal type validation can
    still report a helpful error.
    """
    if value is None:
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty or whitespace only")
        return stripped
    return value


class EmailDraftReviewStatusUpdateRequest(BaseModel):
    """Request body for changing an email draft's review status.

    Setting ``review_status`` to ``approved`` means a human has internally
    reviewed the draft — it never sends the email or makes contact. Any
    actual outreach remains a separate, manual step outside this system.
    """

    review_status: EmailDraftReviewStatus
    reviewer_name: str | None = Field(default=None, max_length=200)
    comment: str | None = Field(default=None, max_length=2000)

    @field_validator("reviewer_name", "comment", mode="before")
    @classmethod
    def _no_blank_strings(cls, value: object) -> object:
        return _clean_optional_text(value)


class EmailDraftReviewStatusResponse(BaseModel):
    """Result of an email draft review-status change.

    ``message`` always states explicitly that nothing was sent.
    """

    email_draft_id: UUID
    review_status: EmailDraftReviewStatus
    reviewer_name: str | None
    review_comment: str | None
    reviewed_at: datetime | None
    message: str = "Review-Status gespeichert. Es wurde keine E-Mail gesendet."


class WorkflowCommentRequest(BaseModel):
    """Request body for adding a review comment to a workflow run."""

    reviewer_name: str | None = Field(default=None, max_length=200)
    comment: str = Field(min_length=1, max_length=2000)

    @field_validator("reviewer_name", mode="before")
    @classmethod
    def _no_blank_reviewer_name(cls, value: object) -> object:
        return _clean_optional_text(value)

    @field_validator("comment", mode="before")
    @classmethod
    def _no_blank_comment(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("must not be empty or whitespace only")
            return stripped
        return value


class WorkflowCommentResponse(BaseModel):
    """Result of adding a review comment to a workflow run.

    ``message`` always states explicitly that nothing was sent.
    """

    workflow_id: UUID
    event_id: UUID
    message: str = "Kommentar gespeichert. Es wurde keine E-Mail gesendet."


class ReviewEventResponse(BaseModel):
    """A single audit-trail entry for a workflow run or email draft review."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_run_id: UUID | None
    email_draft_id: UUID | None
    event_type: ReviewEventType
    previous_status: str | None
    new_status: str | None
    comment: str | None
    reviewer_name: str | None
    metadata: dict[str, Any] | None
    created_at: datetime


class ReviewEventListResponse(BaseModel):
    """A list of audit-trail entries, newest first."""

    items: list[ReviewEventResponse]
