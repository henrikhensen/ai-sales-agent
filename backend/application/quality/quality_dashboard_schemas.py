"""Schemas for the Quality Status and Quality Dashboard endpoints."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from backend.application.quality.beta_test_schemas import BetaReadinessLevel


class QualityStatusResponse(BaseModel):
    quality_feedback_enabled: bool
    quality_scoring_enabled: bool
    quality_scoring_provider: str
    quality_scoring_use_llm: bool
    min_draft_score: int
    min_lead_score: int
    min_workflow_score: int
    auto_score_drafts: bool
    auto_score_workflows: bool
    require_human_feedback_for_beta: bool
    message: str


class QualityIssueSummary(BaseModel):
    tag: str
    count: int


class EntityScoreSummary(BaseModel):
    entity_type: str
    entity_id: UUID
    score_total: int
    score_level: str


class QualityDashboardResponse(BaseModel):
    average_draft_quality_score: float | None = None
    average_lead_quality_score: float | None = None
    average_workflow_quality_score: float | None = None
    total_feedback_items: int = 0
    open_feedback_items: int = 0
    blocking_feedback_items: int = 0
    top_quality_issues: list[QualityIssueSummary] = Field(default_factory=list)
    top_improvement_suggestions: list[QualityIssueSummary] = Field(default_factory=list)
    best_performing_drafts: list[EntityScoreSummary] = Field(default_factory=list)
    weakest_drafts: list[EntityScoreSummary] = Field(default_factory=list)
    best_leads: list[EntityScoreSummary] = Field(default_factory=list)
    weakest_leads: list[EntityScoreSummary] = Field(default_factory=list)
    beta_readiness_level: BetaReadinessLevel
    warnings: list[str] = Field(default_factory=list)
    message: str
