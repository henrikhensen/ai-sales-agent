"""Schemas for Customer Onboarding.

A pure progress tracker over a fixed sequence of setup steps, plus a
system-wide readiness check. Nothing here ever enables a real provider,
sends an email, or makes contact — onboarding only ever reads state and
records which steps a user has completed or skipped.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

OnboardingStepName = Literal[
    "welcome",
    "profile_setup",
    "company_setup",
    "offer_setup",
    "icp_setup",
    "safe_mode_review",
    "provider_settings_review",
    "compliance_review",
    "do_not_contact_review",
    "first_lead_sourcing",
    "first_qualification",
    "first_outreach_queue",
    "first_draft_review",
    "completion",
]

#: Canonical order of the onboarding sequence — drives progress-percent and
#: "next step" calculation.
ONBOARDING_STEP_ORDER: tuple[OnboardingStepName, ...] = (
    "welcome",
    "profile_setup",
    "company_setup",
    "offer_setup",
    "icp_setup",
    "safe_mode_review",
    "provider_settings_review",
    "compliance_review",
    "do_not_contact_review",
    "first_lead_sourcing",
    "first_qualification",
    "first_outreach_queue",
    "first_draft_review",
    "completion",
)

ReadinessLevel = Literal["not_ready", "demo_ready", "internal_ready", "beta_ready"]


class OnboardingStatusResponse(BaseModel):
    id: UUID
    user_id: UUID
    current_step: OnboardingStepName
    completed_steps: list[str]
    skipped_steps: list[str]
    is_completed: bool
    completed_at: datetime | None
    progress_percent: int = Field(ge=0, le=100)
    next_step: OnboardingStepName | None
    created_at: datetime
    updated_at: datetime


class OnboardingStepUpdateRequest(BaseModel):
    """Deliberately empty — the step name is always addressed via the URL
    path, never guessed or bulk-applied."""


class OnboardingStepUpdateResponse(BaseModel):
    status: OnboardingStatusResponse


class OnboardingReadinessChecks(BaseModel):
    has_offer_profile: bool
    has_icp_profile: bool
    has_do_not_contact_enabled: bool
    has_human_review_enabled: bool
    safe_mode_active: bool
    real_llm_configured: bool
    email_integration_configured: bool
    reply_tracking_configured: bool
    dispatch_safe: bool
    audit_logs_enabled: bool
    rate_limits_enabled: bool
    ready_for_demo: bool
    ready_for_internal_use: bool
    ready_for_customer_beta: bool


class OnboardingReadinessResponse(BaseModel):
    readiness_level: ReadinessLevel
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    checks: OnboardingReadinessChecks
    message: str
