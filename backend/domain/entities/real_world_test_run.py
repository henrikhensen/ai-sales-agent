from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class RealWorldTestRun:
    """A controlled, auditable test run against real leads/websites and,
    optionally, real LLM output — never an automatic send, external draft,
    or contact attempt.

    ``mode`` only ever governs how much of this run is allowed to touch
    real external systems (website fetch, LLM provider) — it can never
    enable sending, and it never bypasses Do-not-contact or Human Review,
    both of which remain fully enforced by the underlying Sales Workflow
    this wraps.
    """

    name: str
    status: str = "pending"
    mode: str = "safe"
    lead_candidate_id: UUID | None = None
    lead_id: UUID | None = None
    icp_profile_id: UUID | None = None
    offer_profile_id: UUID | None = None
    workflow_run_id: UUID | None = None
    quality_score_id: UUID | None = None
    input_snapshot: dict = field(default_factory=dict)
    result_snapshot: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    created_by_user_id: UUID | None = None
    aborted_at: datetime | None = None
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
