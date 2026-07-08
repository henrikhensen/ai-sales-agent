from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class OutreachDispatch:
    """One controlled attempt to move a single, already-approved Outreach
    Queue item into an external draft or — only when explicitly enabled
    and confirmed by a human — a manually confirmed send.

    Never a record of automatic sending: ``sent_manually_confirmed`` is set
    only after a human has explicitly acknowledged compliance and given
    final confirmation, and only if real sending was deliberately enabled.
    Do-not-contact and Human Review approval are re-checked immediately
    before every action and can never be bypassed by this record's state.
    """

    queue_item_id: UUID
    outreach_campaign_id: UUID | None = None
    lead_id: UUID | None = None
    company_id: UUID | None = None
    email_draft_id: UUID | None = None
    external_draft_id: UUID | None = None
    review_id: UUID | None = None
    provider: str = "mock"
    dispatch_mode: str = "draft_only"
    dispatch_status: str = "pending"
    recipient_email: str | None = None
    subject_snapshot: str | None = None
    body_preview_snapshot: str | None = None
    final_confirmation_by_user_id: UUID | None = None
    final_confirmation_at: datetime | None = None
    compliance_acknowledged_by_user_id: UUID | None = None
    compliance_acknowledged_at: datetime | None = None
    do_not_contact_checked_at: datetime | None = None
    human_review_checked_at: datetime | None = None
    provider_message_id: str | None = None
    provider_draft_id: str | None = None
    provider_url: str | None = None
    last_error: str | None = None
    created_by_user_id: UUID | None = None
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
