from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class UserFeedback:
    """One human's feedback on one entity (draft, workflow run, lead
    candidate, qualification result, outreach queue item, reply, or
    real-world test run) — or general/UI feedback not tied to any single
    entity (``entity_type="general"``, ``entity_id=None``).

    Recording feedback never changes the entity itself and never triggers
    any automatic action (no send, no re-draft, no re-scoring) — it is
    purely tracked signal that a human reviews separately.
    ``is_blocking=True`` marks feedback that should surface as a warning
    (or, where wired, a blocker) elsewhere — e.g. Dispatch Readiness — but
    it never bypasses Do-not-contact or Human Review, and it never sends
    anything by itself. ``feedback_text`` is length-bounded by
    ``QUALITY_MAX_FEEDBACK_TEXT_CHARS`` at the service layer, never a
    secret, API key, or token. ``priority`` is a human triage hint
    (low/medium/high) — it never changes scheduling or automated
    behavior by itself.
    """

    entity_type: str
    rating: int
    feedback_type: str
    entity_id: UUID | None = None
    priority: str = "medium"
    feedback_text: str | None = None
    issue_tags: list[str] = field(default_factory=list)
    improvement_tags: list[str] = field(default_factory=list)
    is_blocking: bool = False
    workflow_run_id: UUID | None = None
    email_draft_id: UUID | None = None
    lead_id: UUID | None = None
    company_id: UUID | None = None
    lead_candidate_id: UUID | None = None
    qualification_result_id: UUID | None = None
    outreach_queue_item_id: UUID | None = None
    reply_id: UUID | None = None
    real_world_test_run_id: UUID | None = None
    submitted_by_user_id: UUID | None = None
    reviewed_by_user_id: UUID | None = None
    review_status: str = "open"
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
