from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class QualificationRun:
    """One execution of the Lead Qualification engine over a batch of Lead
    Candidates and/or CRM Leads.

    Only ever scores and prioritizes — never sends anything, never
    contacts anyone, and never starts a Sales Workflow or creates a draft
    by itself.
    """

    name: str | None = None
    source_type: str = "lead_candidate"
    icp_profile_id: UUID | None = None
    offer_profile_id: UUID | None = None
    status: str = "running"
    started_by_user_id: UUID | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    total_items: int = 0
    qualified_count: int = 0
    priority_count: int = 0
    disqualified_count: int = 0
    needs_review_count: int = 0
    average_score: float | None = None
    warnings: list[str] = field(default_factory=list)
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
