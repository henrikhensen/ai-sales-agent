from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class LeadSourcingRun:
    """One execution of a lead sourcing campaign.

    Only ever finds and scores candidates for human review — a run never
    sends an email, never contacts anyone, and never creates a CRM Company
    or Lead by itself (that only happens when a human approves a candidate).
    """

    campaign_id: UUID
    status: str = "running"
    provider: str = "mock"
    started_by_user_id: UUID | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    total_candidates_found: int = 0
    total_candidates_saved: int = 0
    total_duplicates: int = 0
    total_blocked_by_do_not_contact: int = 0
    total_errors: int = 0
    warnings: list[str] = field(default_factory=list)
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
