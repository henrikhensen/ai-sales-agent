from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from backend.domain.enums import EmailDraftReviewStatus


@dataclass
class EmailDraft:
    """A persisted, human-reviewable email draft produced by a sales workflow.

    This is a draft only: nothing on this entity ever represents that an
    email was sent, scheduled, or that contact was made. Sending remains a
    fully separate, manual step outside this system. ``review_status`` is an
    internal review marker only — even ``APPROVED`` never triggers sending.
    """

    company_id: UUID
    email_body: str
    subject_lines: list[str] = field(default_factory=list)
    lead_id: UUID | None = None
    workflow_run_id: UUID | None = None
    status: str = "draft"
    review_status: EmailDraftReviewStatus = EmailDraftReviewStatus.NEEDS_REVIEW
    reviewer_name: str | None = None
    review_comment: str | None = None
    reviewed_at: datetime | None = None
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
