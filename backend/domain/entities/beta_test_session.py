from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class BetaTestSession:
    """A tracked, structured round of manual beta testing.

    Purely a tracking/aggregation record — creating, starting, or
    completing a session never activates a real provider, sends an email,
    or creates an external draft automatically. It exists to make manual
    testing measurable (quality scores, feedback, blockers, bugs), not to
    unlock any feature.
    """

    name: str
    description: str | None = None
    tester_user_id: UUID | None = None
    status: str = "planned"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    target_goal: str | None = None
    total_workflows_tested: int = 0
    total_drafts_reviewed: int = 0
    total_feedback_items: int = 0
    average_quality_score: float | None = None
    blockers_count: int = 0
    bugs_count: int = 0
    notes: str | None = None
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
