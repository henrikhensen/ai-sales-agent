"""Schemas for the Do-not-contact (opt-out) compliance system.

Used both by :class:`~backend.application.compliance.do_not_contact_service.
DoNotContactService` directly and as ``response_model`` for
``backend/api/v1/routes/compliance.py``, following the same pattern as
``backend/application/crm/pipeline_schemas.py``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class DoNotContactEntryResponse(BaseModel):
    """A single opt-out / do-not-contact record."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str | None
    domain: str | None
    company_name: str | None
    reason: str
    source: str
    is_active: bool
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime


def _require_at_least_one_target(
    email: str | None, domain: str | None, company_name: str | None
) -> None:
    if not (email or domain or company_name):
        raise ValueError(
            "At least one of email, domain, or company_name is required."
        )


class CreateDoNotContactRequest(BaseModel):
    """Request body for ``POST /api/v1/compliance/do-not-contact``.

    At least one of ``email``, ``domain``, or ``company_name`` is required.
    ``email``/``domain`` are lowercased when stored; ``company_name`` is
    normalized for matching while the original casing is kept for display.
    """

    email: EmailStr | None = Field(default=None, max_length=320)
    domain: str | None = Field(default=None, max_length=255)
    company_name: str | None = Field(default=None, max_length=200)
    reason: str = Field(min_length=1, max_length=500)
    source: str = Field(default="manual", max_length=100)

    @model_validator(mode="after")
    def _validate_target(self) -> "CreateDoNotContactRequest":
        _require_at_least_one_target(self.email, self.domain, self.company_name)
        return self


class UpdateDoNotContactRequest(BaseModel):
    """Request body for ``PATCH /api/v1/compliance/do-not-contact/{entry_id}``.

    Every field is optional — only fields explicitly present in the request
    body are changed (partial update). Setting a field to ``null``
    explicitly clears it.
    """

    email: EmailStr | None = Field(default=None, max_length=320)
    domain: str | None = Field(default=None, max_length=255)
    company_name: str | None = Field(default=None, max_length=200)
    reason: str | None = Field(default=None, min_length=1, max_length=500)
    is_active: bool | None = None


class DoNotContactListResponse(BaseModel):
    """Response for ``GET /api/v1/compliance/do-not-contact``."""

    items: list[DoNotContactEntryResponse]
    limit: int
    offset: int


class DoNotContactCheckRequest(BaseModel):
    """Request body for ``POST /api/v1/compliance/do-not-contact/check``.

    At least one of ``email``, ``domain``, or ``company_name`` is required.
    """

    email: EmailStr | None = Field(default=None, max_length=320)
    domain: str | None = Field(default=None, max_length=255)
    company_name: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _validate_target(self) -> "DoNotContactCheckRequest":
        _require_at_least_one_target(self.email, self.domain, self.company_name)
        return self


class DoNotContactCheckResponse(BaseModel):
    """Result of checking email/domain/company_name against active opt-outs.

    Never triggers a send or contacts anyone by itself — this only ever
    reports whether outreach preparation should be blocked elsewhere (Sales
    Workflow, Human Review).
    """

    is_blocked: bool
    matched_by: Literal["email", "domain", "company_name"] | None = None
    matched_entry_id: UUID | None = None
    reason: str | None = None
    warning_message: str | None = None


class ComplianceStatusResponse(BaseModel):
    """A safe, at-a-glance compliance snapshot. Never includes a secret,
    API key, or token — only which safeguards are active and which
    providers are running in mock vs. real mode.

    ``email_sending_enabled`` and ``automatic_contact_enabled`` are always
    ``False`` — there is no send/auto-contact capability anywhere in this
    system.
    """

    do_not_contact_enabled: bool
    human_review_enabled: bool
    email_sending_enabled: bool
    automatic_contact_enabled: bool
    llm_provider: str
    llm_real_calls_enabled: bool
    email_integration_provider: str
    email_real_drafts_enabled: bool
    reply_tracking_provider: str
    reply_real_reads_enabled: bool
    rate_limits_enabled: bool
    audit_logs_enabled: bool
    last_do_not_contact_block_count: int
    last_review_block_count: int
    safe_mode: bool
    warnings: list[str]
    message: str
