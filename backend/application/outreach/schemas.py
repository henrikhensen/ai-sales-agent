"""Schemas for the Outreach Campaign Queue.

A campaign is a reusable, named container; a queue item is one prioritized,
campaign-scoped entry for a Lead Candidate or CRM Lead already scored by
Lead Qualification. Nothing here represents sending an email, contacting
anyone, or creating an external (Gmail/Outlook) draft — every queue item
only ever moves forward through a deliberate, human-triggered action.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

OutreachCampaignStatus = Literal[
    "draft", "ready", "active", "paused", "completed", "archived"
]
OutreachQueueStatus = Literal[
    "queued",
    "blocked",
    "needs_review",
    "ready_for_workflow",
    "workflow_prepared",
    "draft_created",
    "review_pending",
    "approved",
    "rejected",
    "external_draft_created",
    "replied",
    "archived",
    # Added for Controlled Outreach Dispatch (see
    # backend/application/outreach/outreach_dispatch_service.py) — never set
    # automatically; only ever the outcome of a human-confirmed dispatch
    # action on an 'approved'/'external_draft_created' item.
    "sent_manually_confirmed",
    "failed",
    "cancelled",
]


# -- campaigns --------------------------------------------------------------------


class CreateOutreachCampaignRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    icp_profile_id: UUID | None = None
    offer_profile_id: UUID | None = None
    target_language: str | None = Field(default=None, max_length=50)
    tone: str | None = Field(default=None, max_length=50)
    min_qualification_score: int | None = Field(default=None, ge=0, le=100)
    allowed_qualification_levels: list[str] = Field(default_factory=list)
    excluded_statuses: list[str] = Field(default_factory=list)
    max_queue_items: int | None = Field(default=None, ge=1, le=500)


class UpdateOutreachCampaignRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    icp_profile_id: UUID | None = None
    offer_profile_id: UUID | None = None
    target_language: str | None = Field(default=None, max_length=50)
    tone: str | None = Field(default=None, max_length=50)
    min_qualification_score: int | None = Field(default=None, ge=0, le=100)
    allowed_qualification_levels: list[str] | None = None
    excluded_statuses: list[str] | None = None
    max_queue_items: int | None = Field(default=None, ge=1, le=500)


class UpdateOutreachCampaignStatusRequest(BaseModel):
    status: OutreachCampaignStatus


class OutreachCampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    icp_profile_id: UUID | None
    offer_profile_id: UUID | None
    target_language: str | None
    tone: str | None
    min_qualification_score: int
    allowed_qualification_levels: list[str]
    excluded_statuses: list[str]
    max_queue_items: int
    status: OutreachCampaignStatus
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime


class OutreachCampaignListResponse(BaseModel):
    items: list[OutreachCampaignResponse]
    limit: int
    offset: int


# -- queue items --------------------------------------------------------------------


class OutreachQueueItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None
    campaign_id: UUID
    lead_id: UUID | None
    company_id: UUID | None
    lead_candidate_id: UUID | None
    qualification_result_id: UUID | None
    icp_profile_id: UUID | None
    offer_profile_id: UUID | None
    priority_rank: int | None
    qualification_score: int
    qualification_level: str
    queue_status: OutreachQueueStatus
    recommended_outreach_angle: str | None
    personalization_notes: str | None
    compliance_status: Literal["clear", "blocked"]
    do_not_contact_status: Literal["unknown", "clear", "blocked"]
    duplicate_status: Literal["unknown", "new", "duplicate"]
    workflow_run_id: UUID | None
    email_draft_id: UUID | None
    review_id: UUID | None
    external_draft_id: UUID | None
    last_action: str | None
    last_error: str | None
    created_by_user_id: UUID | None
    assigned_to_user_id: UUID | None
    created_at: datetime | None
    updated_at: datetime | None


class OutreachQueueItemListResponse(BaseModel):
    items: list[OutreachQueueItemResponse]
    limit: int
    offset: int


# -- build queue --------------------------------------------------------------------


class BuildOutreachQueueRequest(BaseModel):
    qualification_result_ids: list[UUID] = Field(default_factory=list)
    lead_ids: list[UUID] = Field(default_factory=list)
    min_score: int | None = Field(default=None, ge=0, le=100)
    max_items: int | None = Field(default=None, ge=1, le=500)
    dry_run: bool = False


class BuildOutreachQueueResponse(BaseModel):
    campaign: OutreachCampaignResponse
    items: list[OutreachQueueItemResponse]
    skipped_count: int
    blocked_count: int
    dry_run: bool
    warnings: list[str] = Field(default_factory=list)


# -- workflow preparation ------------------------------------------------------------


class PrepareQueueItemWorkflowRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)


class PrepareQueueItemWorkflowResponse(BaseModel):
    item: OutreachQueueItemResponse
    workflow_id: str | None = None
    email_draft_id: str | None = None
    blocked: bool = False
    warnings: list[str] = Field(default_factory=list)


class PrepareQueueBatchRequest(BaseModel):
    queue_item_ids: list[UUID] = Field(default_factory=list)
    max_items: int | None = Field(default=None, ge=1, le=500)


class PrepareQueueBatchResponse(BaseModel):
    total_requested: int
    prepared_count: int
    skipped_count: int
    blocked_count: int
    failed_count: int
    items: list[OutreachQueueItemResponse]
    warnings: list[str] = Field(default_factory=list)


# -- status update ------------------------------------------------------------------


class UpdateQueueItemStatusRequest(BaseModel):
    queue_status: OutreachQueueStatus
    notes: str | None = Field(default=None, max_length=2000)
    external_draft_id: UUID | None = None


class UpdateQueueItemStatusResponse(BaseModel):
    item: OutreachQueueItemResponse


# -- dashboard --------------------------------------------------------------------


class OutreachQueueDashboardResponse(BaseModel):
    total_queued: int
    total_blocked: int
    total_needs_review: int
    total_ready_for_workflow: int
    total_workflow_prepared: int
    total_draft_created: int
    total_review_pending: int
    total_approved: int
    total_rejected: int
    total_external_draft_created: int
    total_archived: int
    campaigns: list[OutreachCampaignResponse]
    warnings: list[str] = Field(default_factory=list)


# -- status -------------------------------------------------------------------------


class OutreachQueueStatusResponse(BaseModel):
    enabled: bool
    default_min_score: int
    default_batch_size: int
    max_batch_size: int
    require_qualification: bool
    require_human_review: bool
    allow_batch_workflow_prep: bool
    auto_create_external_drafts: bool
    warnings: list[str] = Field(default_factory=list)
