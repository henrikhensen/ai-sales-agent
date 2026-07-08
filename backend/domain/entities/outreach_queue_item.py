from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class OutreachQueueItem:
    """One prioritized, campaign-scoped queue entry for a qualified Lead
    Candidate or CRM Lead, awaiting a human-triggered next step.

    Never a record that outreach happened: 'approved' and
    'external_draft_created' both mean a human/internal artifact was
    prepared, never that an email was sent. Do-not-contact always takes
    precedence — a blocked item is never eligible to move forward.
    """

    campaign_id: UUID
    lead_id: UUID | None = None
    company_id: UUID | None = None
    lead_candidate_id: UUID | None = None
    qualification_result_id: UUID | None = None
    icp_profile_id: UUID | None = None
    offer_profile_id: UUID | None = None
    priority_rank: int | None = None
    qualification_score: int = 0
    qualification_level: str = "not_fit"
    queue_status: str = "queued"
    recommended_outreach_angle: str | None = None
    personalization_notes: str | None = None
    compliance_status: str = "clear"
    do_not_contact_status: str = "unknown"
    duplicate_status: str = "unknown"
    workflow_run_id: UUID | None = None
    email_draft_id: UUID | None = None
    review_id: UUID | None = None
    external_draft_id: UUID | None = None
    last_action: str | None = None
    last_error: str | None = None
    created_by_user_id: UUID | None = None
    assigned_to_user_id: UUID | None = None
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
