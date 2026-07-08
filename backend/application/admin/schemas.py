"""Schemas for Admin Controls.

Two related but distinct surfaces over the same underlying
``WorkspaceSettings`` singleton row: plain branding/defaults
(``WorkspaceSettingsResponse``) and safety-relevant toggles
(``AdminControlsStatus``). Neither ever returns a secret, API key, or
token — every "is X configured" signal here is a boolean/message only.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

DispatchMode = Literal["draft_only", "manual_send"]

ChecklistItemStatus = Literal["passed", "warning", "blocker", "not_checked"]


# -- workspace settings (branding / defaults) ----------------------------------------


class WorkspaceSettingsResponse(BaseModel):
    id: UUID
    workspace_name: str
    company_name: str | None
    company_website: str | None
    default_language: str
    default_tone: str
    default_icp_profile_id: UUID | None
    default_offer_profile_id: UUID | None
    created_at: datetime
    updated_at: datetime


class UpdateWorkspaceSettingsRequest(BaseModel):
    workspace_name: str | None = Field(default=None, min_length=1, max_length=200)
    company_name: str | None = Field(default=None, max_length=200)
    company_website: str | None = Field(default=None, max_length=500)
    default_language: str | None = Field(default=None, max_length=10)
    default_tone: str | None = Field(default=None, max_length=50)
    default_icp_profile_id: UUID | None = None
    default_offer_profile_id: UUID | None = None


# -- admin controls (safety toggles) -------------------------------------------------


class AdminControlsStatus(BaseModel):
    require_human_review: bool
    require_do_not_contact_check: bool
    allow_real_llm_calls: bool
    allow_real_email_drafts: bool
    allow_real_reply_reads: bool
    allow_real_dispatch: bool
    dispatch_mode: DispatchMode
    # Computed, read-only signals about whether the environment actually
    # backs each toggle — never a secret, just booleans/messages.
    real_llm_configured: bool
    email_integration_configured: bool
    reply_tracking_configured: bool
    real_send_env_enabled: bool
    # -- Legal/Compliance Pack ------------------------------------------------------
    data_retention_enabled: bool
    anonymize_instead_of_delete: bool
    data_export_enabled: bool
    data_subject_requests_enabled: bool
    # Always True — never settable via the API. A reminder, not a gate:
    # this system is prepared for a legal/compliance review, never
    # certified compliant with any law or standard. See COMPLIANCE.md.
    legal_review_required: bool = True
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)


class UpdateAdminControlsRequest(BaseModel):
    require_human_review: bool | None = None
    require_do_not_contact_check: bool | None = None
    allow_real_llm_calls: bool | None = None
    allow_real_email_drafts: bool | None = None
    allow_real_reply_reads: bool | None = None
    allow_real_dispatch: bool | None = None
    dispatch_mode: DispatchMode | None = None
    data_retention_enabled: bool | None = None
    anonymize_instead_of_delete: bool | None = None
    data_export_enabled: bool | None = None
    data_subject_requests_enabled: bool | None = None


# -- setup checklist ------------------------------------------------------------------


class ChecklistItem(BaseModel):
    key: str
    label: str
    status: ChecklistItemStatus
    detail: str | None = None


class CustomerSetupChecklistResponse(BaseModel):
    items: list[ChecklistItem]
    overall_status: ChecklistItemStatus
