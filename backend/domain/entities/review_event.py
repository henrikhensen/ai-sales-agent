from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from backend.domain.enums import ReviewEventType


@dataclass
class ReviewEvent:
    """An immutable audit-trail entry for a workflow run or email draft review.

    Always references at least one of ``workflow_run_id`` / ``email_draft_id``.
    No event type here ever represents that an email was sent or that
    contact was made — this is an internal review audit log only.
    """

    event_type: ReviewEventType
    workflow_run_id: UUID | None = None
    email_draft_id: UUID | None = None
    previous_status: str | None = None
    new_status: str | None = None
    comment: str | None = None
    reviewer_name: str | None = None
    metadata: dict[str, Any] | None = None
    id: UUID | None = None
    created_at: datetime | None = None
