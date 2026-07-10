"""Schemas for Real-World Test Runs (Phase 34).

A Real-World Test Run wraps the existing Sales Workflow to let a human
run a controlled test against a real lead/candidate and, optionally, a
real website and real LLM output — never an automatic send, external
draft, or contact attempt. Approval/completion here never means anything
was sent.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

RealWorldTestRunMode = Literal["safe", "mock", "real_llm"]

RealWorldTestRunStatus = Literal[
    "pending", "running", "completed", "blocked", "failed", "aborted"
]


class RealWorldTestRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    status: RealWorldTestRunStatus
    mode: RealWorldTestRunMode
    lead_candidate_id: UUID | None
    lead_id: UUID | None
    icp_profile_id: UUID | None
    offer_profile_id: UUID | None
    workflow_run_id: UUID | None
    quality_score_id: UUID | None
    input_snapshot: dict
    result_snapshot: dict
    warnings: list[str]
    errors: list[str]
    created_by_user_id: UUID | None
    aborted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RealWorldTestRunListResponse(BaseModel):
    items: list[RealWorldTestRunResponse]
    limit: int
    offset: int


class CreateRealWorldTestRunRequest(BaseModel):
    """Exactly one of ``lead_candidate_id``, ``lead_id``, or a direct
    ``company_name`` must be given to identify the real-world target."""

    name: str = Field(min_length=1, max_length=200)
    mode: RealWorldTestRunMode = "safe"
    lead_candidate_id: UUID | None = None
    lead_id: UUID | None = None
    icp_profile_id: UUID | None = None
    offer_profile_id: UUID | None = None
    company_name: str | None = Field(default=None, max_length=200)
    website_url: str | None = Field(default=None, max_length=500)
    industry: str | None = Field(default=None, max_length=200)
    product_or_service_offered: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _require_a_target(self) -> "CreateRealWorldTestRunRequest":
        if not self.lead_candidate_id and not self.lead_id and not self.company_name:
            raise ValueError(
                "One of lead_candidate_id, lead_id, or company_name is required."
            )
        return self
