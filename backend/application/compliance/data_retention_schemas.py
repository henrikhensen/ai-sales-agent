"""Schemas for Data Retention Policies and Runs.

A policy is purely declarative until a run is started against it. A dry
run never changes data. A real (non-dry-run) run requires an active admin
account and is never triggered automatically or on a schedule.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

RetentionEntityType = Literal[
    "lead",
    "company",
    "email_draft",
    "reply",
    "workflow_run",
    "audit_log",
    "do_not_contact",
    "external_draft",
    "outreach",
    "qualification",
    "sourcing_candidate",
]

RetentionAction = Literal["delete", "anonymize", "archive"]

RetentionRunStatus = Literal["running", "completed", "failed", "cancelled"]


class DataRetentionPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    entity_type: RetentionEntityType
    retention_days: int
    action: RetentionAction
    is_active: bool
    dry_run_default: bool
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime


class DataRetentionPolicyListResponse(BaseModel):
    items: list[DataRetentionPolicyResponse]
    limit: int
    offset: int


class CreateDataRetentionPolicyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    entity_type: RetentionEntityType
    retention_days: int = Field(ge=1, le=3650)
    action: RetentionAction = "anonymize"
    dry_run_default: bool = True


class UpdateDataRetentionPolicyRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    retention_days: int | None = Field(default=None, ge=1, le=3650)
    action: RetentionAction | None = None
    dry_run_default: bool | None = None


class DataRetentionRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    policy_id: UUID
    entity_type: RetentionEntityType
    action: RetentionAction
    dry_run: bool
    status: RetentionRunStatus
    started_by_user_id: UUID | None
    started_at: datetime | None
    completed_at: datetime | None
    total_scanned: int
    total_eligible: int
    total_processed: int
    total_failed: int
    warnings: list[str]
    errors: list[str]
    created_at: datetime
    updated_at: datetime


class DataRetentionRunListResponse(BaseModel):
    items: list[DataRetentionRunResponse]
    limit: int
    offset: int


class RunDataRetentionPolicyRequest(BaseModel):
    """Explicit confirmation required to start a real (non-dry-run) run.

    ``confirm`` must be exactly ``True`` — omitting it, or sending
    ``False``, is treated as "not confirmed" and the run is refused.
    """

    confirm: bool = False
