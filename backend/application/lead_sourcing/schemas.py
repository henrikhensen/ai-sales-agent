"""Schemas for the Lead Sourcing Engine.

A campaign is a reusable search definition; a run is one execution of a
campaign that finds and scores candidates; a candidate is a potential
customer awaiting human review before it may become a CRM Company/Lead.
Nothing in this module represents sending an email or making contact.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

CampaignStatus = Literal["draft", "ready", "running", "completed", "failed", "archived"]
RunStatus = Literal["running", "completed", "failed", "cancelled"]
DoNotContactStatus = Literal["unknown", "clear", "blocked"]
DuplicateStatus = Literal["unknown", "new", "duplicate"]
ReviewStatus = Literal["pending", "approved", "rejected"]


# -- Provider status --------------------------------------------------------------


class LeadSourcingProviderStatusResponse(BaseModel):
    provider: str
    real_search_enabled: bool
    status: str
    max_results_per_run: int
    max_website_pages_per_company: int
    allow_public_website_email_extraction: bool
    allow_personal_emails: bool
    require_review_before_crm: bool
    warnings: list[str] = Field(default_factory=list)


# -- Campaign -----------------------------------------------------------------------


class LeadSourcingCampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    icp_profile_id: UUID | None
    offer_profile_id: UUID | None
    source_type: str
    search_query: str | None
    target_industry: str | None
    target_location: str | None
    target_keywords: list[str]
    excluded_keywords: list[str]
    max_results: int
    status: CampaignStatus
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime


class CreateLeadSourcingCampaignRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    icp_profile_id: UUID | None = None
    offer_profile_id: UUID | None = None
    search_query: str | None = Field(default=None, max_length=500)
    target_industry: str | None = Field(default=None, max_length=200)
    target_location: str | None = Field(default=None, max_length=200)
    target_keywords: list[str] = Field(default_factory=list)
    excluded_keywords: list[str] = Field(default_factory=list)
    max_results: int = Field(default=25, ge=1, le=200)


class UpdateLeadSourcingCampaignRequest(BaseModel):
    """Only fields present in the request body are changed. ``status`` may
    only be set to 'draft' or 'ready' here — 'running'/'completed'/'failed'
    are set by the service during a run, and 'archived' has its own
    dedicated endpoint."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    icp_profile_id: UUID | None = None
    offer_profile_id: UUID | None = None
    search_query: str | None = Field(default=None, max_length=500)
    target_industry: str | None = Field(default=None, max_length=200)
    target_location: str | None = Field(default=None, max_length=200)
    target_keywords: list[str] | None = None
    excluded_keywords: list[str] | None = None
    max_results: int | None = Field(default=None, ge=1, le=200)
    status: Literal["draft", "ready"] | None = None


class LeadSourcingCampaignListResponse(BaseModel):
    items: list[LeadSourcingCampaignResponse]
    limit: int
    offset: int


# -- Run --------------------------------------------------------------------------


class LeadSourcingRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_id: UUID
    status: RunStatus
    provider: str
    started_by_user_id: UUID | None
    started_at: datetime | None
    completed_at: datetime | None
    total_candidates_found: int
    total_candidates_saved: int
    total_duplicates: int
    total_blocked_by_do_not_contact: int
    total_errors: int
    warnings: list[str]
    created_at: datetime
    updated_at: datetime


class LeadSourcingRunListResponse(BaseModel):
    items: list[LeadSourcingRunResponse]
    limit: int
    offset: int


# -- Candidate ----------------------------------------------------------------------


class LeadCandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # None only for an ephemeral dry-run candidate that was never persisted.
    id: UUID | None
    sourcing_run_id: UUID
    campaign_id: UUID
    company_name: str | None
    company_domain: str | None
    company_website_url: str | None
    industry: str | None
    location: str | None
    description: str | None
    source_url: str | None
    source_name: str | None
    source_type: str
    public_contact_email: str | None
    contact_page_url: str | None
    confidence_score: float | None
    icp_fit_score: int | None
    icp_fit_level: str | None
    matched_signals: list[str]
    negative_signals: list[str]
    # "poor" | "medium" | "good" | "unknown" (URL known, fetch/analysis
    # failed) | None (no website URL was known at all).
    website_quality_level: str | None = None
    website_quality_reasons: list[str] = Field(default_factory=list)
    do_not_contact_status: DoNotContactStatus
    duplicate_status: DuplicateStatus
    review_status: ReviewStatus
    crm_company_id: UUID | None
    crm_lead_id: UUID | None
    notes: list[str]
    warnings: list[str]


class LeadCandidateListResponse(BaseModel):
    items: list[LeadCandidateResponse]
    limit: int
    offset: int


# -- Run start / dry run -------------------------------------------------------------


class StartLeadSourcingRunRequest(BaseModel):
    campaign_id: UUID
    max_results: int | None = Field(default=None, ge=1, le=200)
    dry_run: bool = False


class StartLeadSourcingRunResponse(BaseModel):
    run: LeadSourcingRunResponse
    candidates: list[LeadCandidateResponse]
    dry_run: bool


# -- Approve / reject ---------------------------------------------------------------


class ApproveLeadCandidateRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)


class ApproveLeadCandidateResponse(BaseModel):
    candidate: LeadCandidateResponse
    crm_company_id: UUID | None
    crm_lead_id: UUID | None
    warnings: list[str] = Field(default_factory=list)


class RejectLeadCandidateRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)


class RejectLeadCandidateResponse(BaseModel):
    candidate: LeadCandidateResponse


# -- Manual import --------------------------------------------------------------------


class ImportLeadCandidatesRequest(BaseModel):
    campaign_id: UUID
    # One candidate per line: "company_name, domain, website_url, notes" —
    # any of the four fields may be blank, but at least company_name or
    # domain must be present per line.
    raw_text: str = Field(min_length=1, max_length=50_000)


class ImportLeadCandidatesResponse(BaseModel):
    run: LeadSourcingRunResponse
    candidates: list[LeadCandidateResponse]
    total_imported: int
    total_duplicates: int
    total_blocked_by_do_not_contact: int
    warnings: list[str] = Field(default_factory=list)
