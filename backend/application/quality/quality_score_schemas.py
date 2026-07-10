"""Schemas for Quality Scores.

A quality score is decision support only — never a guarantee, never a
legal clearance, and never a substitute for Human Review. Scores never
store a secret, a full email/reply body, or a full LLM prompt.
``score_level="blocked"`` is reserved for entities blocked by Do-not-
contact or another compliance gate — a blocked entity can never also
score as good.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

QualityEntityType = Literal[
    "lead_candidate",
    "crm_lead",
    "company",
    "email_draft",
    "workflow_run",
    "outreach_queue_item",
    "dispatch",
    "reply",
    "qualification_result",
]

QualityScoreLevel = Literal["excellent", "good", "acceptable", "weak", "poor", "blocked"]

EvaluatedBy = Literal["system", "user", "mock", "llm"]


class QualityScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entity_type: QualityEntityType
    entity_id: UUID
    workflow_run_id: UUID | None
    email_draft_id: UUID | None
    lead_id: UUID | None
    company_id: UUID | None
    lead_candidate_id: UUID | None
    qualification_result_id: UUID | None
    outreach_queue_item_id: UUID | None
    reply_id: UUID | None
    score_total: int
    score_level: QualityScoreLevel
    score_breakdown: dict[str, Any]
    strengths: list[str]
    weaknesses: list[str]
    warnings: list[str]
    recommended_improvements: list[str]
    compliance_flags: list[str]
    evaluated_by: EvaluatedBy
    evaluated_by_user_id: UUID | None
    provider: str
    created_at: datetime
    updated_at: datetime


class QualityScoreListResponse(BaseModel):
    items: list[QualityScoreResponse]
    limit: int
    offset: int


class CreateQualityScoreRequest(BaseModel):
    """Requests an on-demand (re-)score of one entity. Never crashes the
    caller — a scoring failure always returns a low-confidence score with
    warnings rather than raising, except for a genuinely unknown entity."""

    entity_type: QualityEntityType
    entity_id: UUID
