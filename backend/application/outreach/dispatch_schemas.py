"""Schemas for Controlled Outreach Dispatch.

A dispatch attempt processes one already-approved Outreach Queue item into
either a controlled external draft, or — only when explicitly enabled and
confirmed by a human — a manually confirmed send. Nothing here represents
automatic or batch sending; every action requires an existing, specific
queue item plus (for anything beyond a readiness check) an explicit
compliance acknowledgement and final confirmation from a human.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

DispatchMode = Literal["draft_only", "manual_send"]
DispatchStatus = Literal[
    "pending",
    "blocked",
    "ready",
    "external_draft_created",
    "send_ready",
    "sent_manually_confirmed",
    "failed",
    "cancelled",
    "archived",
]


# -- readiness ----------------------------------------------------------------------


class DispatchReadinessChecks(BaseModel):
    """Individual pass/fail checks behind a readiness decision."""

    do_not_contact_passed: bool = False
    human_review_approved: bool = False
    email_draft_exists: bool = False
    queue_item_allowed: bool = False
    rate_limit_ok: bool = False
    provider_config_ok: bool = False
    recipient_valid: bool = False
    compliance_ack_present: bool = False


class DispatchReadinessCheckRequest(BaseModel):
    dispatch_mode: DispatchMode | None = None


class DispatchReadinessCheckResponse(BaseModel):
    is_ready: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checks: DispatchReadinessChecks
    recommended_mode: DispatchMode
    requires_final_confirmation: bool
    requires_compliance_ack: bool
    provider_status: str


# -- dispatch record ----------------------------------------------------------------


class OutreachDispatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    queue_item_id: UUID
    outreach_campaign_id: UUID | None
    lead_id: UUID | None
    company_id: UUID | None
    email_draft_id: UUID | None
    external_draft_id: UUID | None
    review_id: UUID | None
    provider: str
    dispatch_mode: DispatchMode
    dispatch_status: DispatchStatus
    recipient_email: str | None
    subject_snapshot: str | None
    body_preview_snapshot: str | None
    final_confirmation_by_user_id: UUID | None
    final_confirmation_at: datetime | None
    compliance_acknowledged_by_user_id: UUID | None
    compliance_acknowledged_at: datetime | None
    do_not_contact_checked_at: datetime | None
    human_review_checked_at: datetime | None
    provider_message_id: str | None
    provider_draft_id: str | None
    provider_url: str | None
    last_error: str | None
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime


class OutreachDispatchListResponse(BaseModel):
    items: list[OutreachDispatchResponse]
    limit: int
    offset: int


# -- create -----------------------------------------------------------------------


class CreateDispatchRequest(BaseModel):
    dispatch_mode: DispatchMode | None = None


class CreateDispatchResponse(BaseModel):
    dispatch: OutreachDispatchResponse
    readiness: DispatchReadinessCheckResponse


# -- compliance ack -----------------------------------------------------------------


class DispatchComplianceAckRequest(BaseModel):
    contact_permission_confirmed: bool = Field(
        description="'Ich habe geprüft, dass dieser Kontakt kontaktiert werden darf.'"
    )
    do_not_contact_confirmed: bool = Field(
        description="'Do-not-contact wurde geprüft.'"
    )
    human_review_confirmed: bool = Field(
        description="'Human Review ist abgeschlossen.'"
    )
    draft_or_controlled_send_confirmed: bool = Field(
        description="'Die Nachricht ist ein Draft oder kontrollierter manueller Versand.'"
    )
    legal_responsibility_confirmed: bool = Field(
        description="'Ich verstehe, dass rechtliche Verantwortung beim Nutzer liegt.'"
    )


class DispatchComplianceAckResponse(BaseModel):
    dispatch: OutreachDispatchResponse


# -- confirm ------------------------------------------------------------------------


class ConfirmDispatchRequest(BaseModel):
    confirmed: bool = Field(
        default=True, description="'Ich bestätige diese kontrollierte Aktion.'"
    )


class ConfirmDispatchResponse(BaseModel):
    dispatch: OutreachDispatchResponse
    warnings: list[str] = Field(default_factory=list)


# -- cancel -------------------------------------------------------------------------


class CancelDispatchRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class CancelDispatchResponse(BaseModel):
    dispatch: OutreachDispatchResponse


# -- dashboard --------------------------------------------------------------------


class DispatchDashboardResponse(BaseModel):
    enabled: bool
    dispatch_mode: DispatchMode
    provider: str
    real_send_enabled: bool
    require_final_confirmation: bool
    require_compliance_ack: bool
    require_approved_review: bool
    require_do_not_contact_check: bool
    max_per_day: int
    max_per_hour: int
    total_pending: int
    total_blocked: int
    total_ready: int
    total_external_draft_created: int
    total_send_ready: int
    total_sent_manually_confirmed: int
    total_failed: int
    total_cancelled: int
    warnings: list[str] = Field(default_factory=list)
