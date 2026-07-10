from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass
class QualityScore:
    """A single quality evaluation of one entity (draft, workflow run,
    lead candidate, qualification result, outreach queue item, or reply).

    A decision-support signal only, never a guarantee and never a legal
    clearance. ``score_level="blocked"`` is reserved for entities that are
    blocked by Do-not-contact or another compliance gate — a blocked
    entity can never score as "good" regardless of everything else.
    Never stores a secret, full email/reply body, or full LLM prompt —
    only short, bounded strings (see ``QualityScoringService``).
    """

    entity_type: str
    entity_id: UUID
    score_total: int
    score_level: str = "acceptable"
    score_breakdown: dict[str, Any] = field(default_factory=dict)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recommended_improvements: list[str] = field(default_factory=list)
    compliance_flags: list[str] = field(default_factory=list)
    evaluated_by: str = "system"
    evaluated_by_user_id: UUID | None = None
    provider: str = "rule_based"
    workflow_run_id: UUID | None = None
    email_draft_id: UUID | None = None
    lead_id: UUID | None = None
    company_id: UUID | None = None
    lead_candidate_id: UUID | None = None
    qualification_result_id: UUID | None = None
    outreach_queue_item_id: UUID | None = None
    reply_id: UUID | None = None
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
