"""Schemas for the Lead Qualification & Scoring Engine.

A run scores a batch of Lead Candidates and/or CRM Leads; a result is the
scored outcome for a single one of them — a recommendation only, never a
record that outreach happened. Nothing here represents sending an email or
starting a Sales Workflow.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

QualificationSourceType = Literal["lead_candidate", "crm_lead", "crm_company", "mixed"]
QualificationRunStatus = Literal["running", "completed", "failed", "cancelled"]
QualificationLevel = Literal["excellent", "good", "medium", "weak", "not_fit"]
QualificationStatus = Literal[
    "qualified", "priority", "needs_review", "disqualified", "blocked", "duplicate"
]
RecommendedNextAction = Literal[
    "start_sales_workflow",
    "enrich_more",
    "review_manually",
    "skip",
    "blocked_do_not_contact",
    "merge_duplicate",
]


# -- score breakdown ----------------------------------------------------------------


class QualificationScoreBreakdown(BaseModel):
    """A human-readable decomposition of the qualification score. Every
    field is a point contribution (positive or negative); ``total`` is the
    clamped 0-100 result actually used for the level/status thresholds."""

    base_score: float = 0.0
    icp_fit_contribution: float = 0.0
    industry_match: float = 0.0
    company_size_match: float = 0.0
    location_match: float = 0.0
    website_signal_quality: float = 0.0
    buying_triggers: float = 0.0
    pain_points_match: float = 0.0
    keyword_match: float = 0.0
    negative_keywords_penalty: float = 0.0
    excluded_signals_penalty: float = 0.0
    data_completeness_penalty: float = 0.0
    source_confidence_contribution: float = 0.0
    total: float = 0.0


# -- runs -----------------------------------------------------------------------


class QualificationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str | None
    source_type: QualificationSourceType
    icp_profile_id: UUID | None
    offer_profile_id: UUID | None
    status: QualificationRunStatus
    started_by_user_id: UUID | None
    started_at: datetime | None
    completed_at: datetime | None
    total_items: int
    qualified_count: int
    priority_count: int
    disqualified_count: int
    needs_review_count: int
    average_score: float | None
    warnings: list[str]
    created_at: datetime
    updated_at: datetime


class QualificationRunListResponse(BaseModel):
    items: list[QualificationRunResponse]
    limit: int
    offset: int


# -- results ----------------------------------------------------------------------


class QualificationResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    qualification_run_id: UUID
    lead_candidate_id: UUID | None
    lead_id: UUID | None
    company_id: UUID | None
    icp_profile_id: UUID | None
    offer_profile_id: UUID | None
    qualification_score: int
    qualification_level: QualificationLevel
    qualification_status: QualificationStatus
    priority_rank: int | None
    fit_summary: str | None
    score_breakdown: QualificationScoreBreakdown
    positive_signals: list[str]
    negative_signals: list[str]
    missing_data: list[str]
    recommended_next_action: RecommendedNextAction
    recommended_outreach_angle: str | None
    disqualification_reason: str | None
    compliance_status: Literal["clear", "blocked"]
    do_not_contact_status: Literal["unknown", "clear", "blocked"]
    duplicate_status: Literal["unknown", "new", "duplicate"]
    pipeline_status: str | None
    confidence_score: float | None
    reviewed_by_user_id: UUID | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class QualificationResultListResponse(BaseModel):
    items: list[QualificationResultResponse]
    limit: int
    offset: int


# -- start run --------------------------------------------------------------------


class StartLeadQualificationRequest(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    source_type: QualificationSourceType = "lead_candidate"
    lead_candidate_ids: list[UUID] = Field(default_factory=list)
    lead_ids: list[UUID] = Field(default_factory=list)
    company_ids: list[UUID] = Field(default_factory=list)
    icp_profile_id: UUID | None = None
    offer_profile_id: UUID | None = None
    min_score: int | None = Field(default=None, ge=0, le=100)
    dry_run: bool = False


class StartLeadQualificationResponse(BaseModel):
    run: QualificationRunResponse
    results: list[QualificationResultResponse]
    dry_run: bool


# -- single-item qualify ------------------------------------------------------------


class QualifyLeadCandidateRequest(BaseModel):
    icp_profile_id: UUID | None = None
    offer_profile_id: UUID | None = None


class QualifyCRMLeadRequest(BaseModel):
    icp_profile_id: UUID | None = None
    offer_profile_id: UUID | None = None


# -- review -----------------------------------------------------------------------


class QualificationReviewRequest(BaseModel):
    qualification_status: Literal["qualified", "priority", "needs_review", "disqualified"]
    notes: str | None = Field(default=None, max_length=2000)


class QualificationReviewResponse(BaseModel):
    result: QualificationResultResponse


# -- dashboard --------------------------------------------------------------------


class QualificationDashboardResponse(BaseModel):
    total_qualified: int
    total_priority: int
    total_needs_review: int
    total_disqualified: int
    total_blocked: int
    average_score: float | None
    top_recommended_leads: list[QualificationResultResponse]
    warnings: list[str] = Field(default_factory=list)


# -- status -------------------------------------------------------------------------


class LeadQualificationStatusResponse(BaseModel):
    enabled: bool
    use_llm: bool
    llm_provider: str
    llm_real_calls_enabled: bool
    use_website_research: bool
    require_icp: bool
    default_min_score: int
    priority_score: int
    disqualify_score: int
    warnings: list[str] = Field(default_factory=list)
