"""Schemas for User Feedback.

Recording feedback never changes the entity it's about and never triggers
any automatic action (no re-draft, no re-send, no automatic contact).
``feedback_text`` is bounded by ``QUALITY_MAX_FEEDBACK_TEXT_CHARS`` at the
service layer. Never store a secret, API key, or token in feedback.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.application.quality.quality_score_schemas import QualityEntityType

FeedbackType = Literal[
    "positive",
    "negative",
    "correction",
    "bug",
    "quality_issue",
    "compliance_issue",
    "missing_context",
    "wrong_target",
    "bad_copy",
    "good_result",
]

FeedbackReviewStatus = Literal["open", "reviewed", "accepted", "rejected", "archived"]

FeedbackPriority = Literal["low", "medium", "high"]

# Feedback may be given about anything Quality Scoring can score, plus a
# Real-World Test Run, plus general/UI feedback not tied to any single
# record (entity_id is None in that case — see the validator below).
FeedbackEntityType = QualityEntityType | Literal["real_world_test_run", "general"]


class QualityFeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entity_type: FeedbackEntityType
    entity_id: UUID | None
    workflow_run_id: UUID | None
    email_draft_id: UUID | None
    lead_id: UUID | None
    company_id: UUID | None
    lead_candidate_id: UUID | None
    qualification_result_id: UUID | None
    outreach_queue_item_id: UUID | None
    reply_id: UUID | None
    real_world_test_run_id: UUID | None
    rating: int
    feedback_type: FeedbackType
    priority: FeedbackPriority
    feedback_text: str | None
    issue_tags: list[str]
    improvement_tags: list[str]
    is_blocking: bool
    submitted_by_user_id: UUID | None
    reviewed_by_user_id: UUID | None
    review_status: FeedbackReviewStatus
    created_at: datetime
    updated_at: datetime


class QualityFeedbackListResponse(BaseModel):
    items: list[QualityFeedbackResponse]
    limit: int
    offset: int


class QualityFeedbackDetailResponse(BaseModel):
    feedback: QualityFeedbackResponse


class CreateQualityFeedbackRequest(BaseModel):
    """``entity_id`` is required for every ``entity_type`` except
    ``"general"`` (UI/App feedback not tied to a single record)."""

    entity_type: FeedbackEntityType
    entity_id: UUID | None = None
    rating: int = Field(ge=1, le=5)
    feedback_type: FeedbackType
    priority: FeedbackPriority = "medium"
    feedback_text: str | None = Field(default=None, max_length=5000)
    issue_tags: list[str] = Field(default_factory=list)
    improvement_tags: list[str] = Field(default_factory=list)
    is_blocking: bool = False
    # Optional linking ids — the caller may supply whichever of these it
    # already knows to make cross-entity queries easier later.
    workflow_run_id: UUID | None = None
    email_draft_id: UUID | None = None
    lead_id: UUID | None = None
    company_id: UUID | None = None
    lead_candidate_id: UUID | None = None
    qualification_result_id: UUID | None = None
    outreach_queue_item_id: UUID | None = None
    reply_id: UUID | None = None
    real_world_test_run_id: UUID | None = None

    @model_validator(mode="after")
    def _entity_id_required_unless_general(self) -> "CreateQualityFeedbackRequest":
        if self.entity_type != "general" and self.entity_id is None:
            raise ValueError(
                "entity_id is required unless entity_type is 'general'."
            )
        return self


class ReviewQualityFeedbackRequest(BaseModel):
    review_status: Literal["reviewed", "accepted", "rejected"]
