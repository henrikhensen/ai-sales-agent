"""Schemas for the Lead Finder / Lead Discovery Run: a guided pipeline that
finds candidate companies for a target customer/region/offer, analyzes
their public websites, scores fit, and — only via a separate, explicit
follow-up action — prepares (never sends) email drafts for the qualified
ones.

Nothing here represents sending an email or making contact. This module
only orchestrates the existing Lead Sourcing, Lead Qualification, and
Outreach Queue services; it introduces no new external I/O of its own.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

LeadDiscoveryMode = Literal["safe", "mock", "real_llm"]
LeadDiscoveryRunStatus = Literal["pending", "running", "completed", "failed"]


class LeadDiscoveryRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    target_customer: str
    region: str | None
    offer_profile_id: UUID | None
    icp_profile_id: UUID | None
    requested_count: int
    min_score: int
    mode: LeadDiscoveryMode
    status: LeadDiscoveryRunStatus
    lead_sourcing_campaign_id: UUID | None
    lead_sourcing_run_id: UUID | None
    outreach_campaign_id: UUID | None
    found_candidates: int
    analyzed_websites: int
    qualified_leads: int
    rejected_leads: int
    needs_review_leads: int
    created_drafts: int
    warnings: list[str]
    errors: list[str]
    created_by_user_id: UUID | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CreateLeadDiscoveryRunRequest(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    target_customer: str = Field(min_length=1, max_length=200)
    region: str | None = Field(default=None, max_length=200)
    offer_profile_id: UUID
    icp_profile_id: UUID | None = None
    requested_count: int = Field(default=10, ge=1, le=50)
    min_score: int = Field(default=50, ge=0, le=100)
    mode: LeadDiscoveryMode = "mock"


class LeadDiscoveryRunListResponse(BaseModel):
    items: list[LeadDiscoveryRunResponse]
    limit: int
    offset: int


class LeadDiscoveryCandidateSummary(BaseModel):
    """One found candidate, enriched with its latest qualification result
    and draft/queue status — everything the Lead Finder result view needs
    in a single row, without a client-side join across four endpoints."""

    candidate_id: UUID
    company_name: str | None
    company_domain: str | None
    company_website_url: str | None
    industry: str | None
    location: str | None
    source_name: str | None
    website_quality_level: str | None
    website_quality_reasons: list[str]
    icp_fit_score: int | None
    icp_fit_level: str | None
    qualification_score: int | None
    qualification_level: str | None
    qualification_status: str | None
    fit_summary: str | None
    positive_signals: list[str]
    negative_signals: list[str]
    missing_data: list[str]
    disqualification_reason: str | None
    do_not_contact_status: str
    duplicate_status: str
    review_status: str
    in_outreach_queue: bool
    draft_status: Literal["none", "prepared", "review_pending"]
    email_draft_id: UUID | None
    warnings: list[str]


class LeadDiscoveryRunDetailResponse(LeadDiscoveryRunResponse):
    candidates: list[LeadDiscoveryCandidateSummary] = Field(default_factory=list)


class AddCandidateToQueueResponse(BaseModel):
    run: LeadDiscoveryRunDetailResponse
    added: bool
    warnings: list[str] = Field(default_factory=list)
