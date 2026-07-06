from enum import Enum


class LeadStatus(str, Enum):
    """Lifecycle stages of a sales lead."""

    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    WON = "won"
    LOST = "lost"


class LeadSource(str, Enum):
    """Channel a lead originated from."""

    WEBSITE = "website"
    REFERRAL = "referral"
    OUTBOUND = "outbound"
    EVENT = "event"
    OTHER = "other"


class InteractionType(str, Enum):
    """Kind of touchpoint recorded against a lead."""

    EMAIL = "email"
    CALL = "call"
    MEETING = "meeting"
    NOTE = "note"
    WORKFLOW_RUN = "workflow_run"


class WorkflowReviewStatus(str, Enum):
    """Human review lifecycle for a persisted workflow run.

    'APPROVED' means a human has internally reviewed the run and judged it
    good to use — it never means an email was sent, a contact was made, or a
    meeting was booked. Any actual outreach remains a fully separate, manual
    step outside this system.
    """

    NEEDS_REVIEW = "needs_review"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class EmailDraftReviewStatus(str, Enum):
    """Human review lifecycle for a persisted email draft.

    'APPROVED' means a human has internally reviewed the draft and judged it
    good to use — it never means the email was sent. Sending remains a fully
    separate, manual step outside this system.
    """

    NEEDS_REVIEW = "needs_review"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"
    ARCHIVED = "archived"


class ReviewEventType(str, Enum):
    """Kind of audit event recorded against a workflow run or email draft."""

    REVIEW_STARTED = "review_started"
    COMMENT_ADDED = "comment_added"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"
    ARCHIVED = "archived"
