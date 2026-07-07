from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass
class QualificationResult:
    """The scored outcome for a single Lead Candidate or CRM Lead.

    A recommendation only — becoming an outreach target still requires a
    human to start the Sales Workflow themselves. Do-not-contact always
    takes precedence: a blocked result is never eligible for outreach
    regardless of score.
    """

    qualification_run_id: UUID
    lead_candidate_id: UUID | None = None
    lead_id: UUID | None = None
    company_id: UUID | None = None
    icp_profile_id: UUID | None = None
    offer_profile_id: UUID | None = None
    qualification_score: int = 0
    qualification_level: str = "not_fit"
    qualification_status: str = "needs_review"
    priority_rank: int | None = None
    fit_summary: str | None = None
    score_breakdown: dict[str, Any] = field(default_factory=dict)
    positive_signals: list[str] = field(default_factory=list)
    negative_signals: list[str] = field(default_factory=list)
    missing_data: list[str] = field(default_factory=list)
    recommended_next_action: str = "review_manually"
    recommended_outreach_angle: str | None = None
    disqualification_reason: str | None = None
    compliance_status: str = "clear"
    do_not_contact_status: str = "unknown"
    duplicate_status: str = "unknown"
    pipeline_status: str | None = None
    confidence_score: float | None = None
    reviewed_by_user_id: UUID | None = None
    reviewed_at: datetime | None = None
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
