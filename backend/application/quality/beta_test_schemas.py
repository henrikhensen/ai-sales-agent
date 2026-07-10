"""Schemas for Beta Test Sessions.

A Beta Test Session is a tracking/aggregation record only — creating,
starting, or completing one never activates a real provider, sends an
email, or creates an external draft automatically.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

BetaSessionStatus = Literal["planned", "running", "completed", "cancelled"]

BetaReadinessLevel = Literal["not_ready", "needs_improvement", "beta_testable", "beta_ready"]


class BetaTestSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    tester_user_id: UUID | None
    status: BetaSessionStatus
    started_at: datetime | None
    completed_at: datetime | None
    target_goal: str | None
    total_workflows_tested: int
    total_drafts_reviewed: int
    total_feedback_items: int
    average_quality_score: float | None
    blockers_count: int
    bugs_count: int
    notes: str | None
    created_at: datetime
    updated_at: datetime


class BetaTestSessionListResponse(BaseModel):
    items: list[BetaTestSessionResponse]
    limit: int
    offset: int


class CreateBetaTestSessionRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    target_goal: str | None = Field(default=None, max_length=500)


class BetaTestDashboardResponse(BaseModel):
    sessions_count: int
    running_sessions_count: int
    completed_sessions_count: int
    average_quality_score: float | None
    total_feedback_items: int
    open_feedback_items: int
    blocking_feedback_items: int
    total_bugs: int
    readiness_level: BetaReadinessLevel
    recommendations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    message: str
