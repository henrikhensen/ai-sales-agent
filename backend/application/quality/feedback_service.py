"""Feedback: one human's structured feedback on one entity.

Recording feedback never changes the entity itself and never triggers any
automatic action — no re-draft, no re-send, no automatic contact.
``is_blocking`` feedback is surfaced as a warning (or, where explicitly
wired, a blocker) in Human Review and Dispatch Readiness — it never
bypasses Do-not-contact or Human Review, and it never sends anything by
itself.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Request

from backend.application.audit.audit_log_service import AuditLogService
from backend.application.quality.feedback_schemas import (
    CreateQualityFeedbackRequest,
    QualityFeedbackDetailResponse,
    QualityFeedbackListResponse,
    QualityFeedbackResponse,
    ReviewQualityFeedbackRequest,
)
from backend.domain.entities.user_feedback import UserFeedback
from backend.domain.exceptions import UserFeedbackNotFoundError
from backend.domain.repositories.user_feedback_repository import (
    UserFeedbackRepository,
)
from backend.shared.config import Settings


class FeedbackService:
    def __init__(
        self,
        feedback: UserFeedbackRepository,
        audit: AuditLogService,
        settings: Settings,
    ) -> None:
        self._feedback = feedback
        self._audit = audit
        self._settings = settings

    async def create_feedback(
        self,
        request: CreateQualityFeedbackRequest,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> QualityFeedbackResponse:
        max_chars = self._settings.quality_max_feedback_text_chars
        feedback_text = request.feedback_text
        if feedback_text and len(feedback_text) > max_chars:
            feedback_text = feedback_text[:max_chars]

        created = await self._feedback.create(
            UserFeedback(
                entity_type=request.entity_type,
                entity_id=request.entity_id,
                rating=request.rating,
                feedback_type=request.feedback_type,
                feedback_text=feedback_text,
                issue_tags=request.issue_tags,
                improvement_tags=request.improvement_tags,
                is_blocking=request.is_blocking,
                workflow_run_id=request.workflow_run_id,
                email_draft_id=request.email_draft_id,
                lead_id=request.lead_id,
                company_id=request.company_id,
                lead_candidate_id=request.lead_candidate_id,
                qualification_result_id=request.qualification_result_id,
                outreach_queue_item_id=request.outreach_queue_item_id,
                reply_id=request.reply_id,
                submitted_by_user_id=actor_user_id,
            )
        )
        await self._audit.record(
            action="quality_feedback_created",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            metadata={
                "feedback_id": str(created.id),
                "rating": request.rating,
                "feedback_type": request.feedback_type,
                "is_blocking": request.is_blocking,
            },
            request=http_request,
        )
        if request.is_blocking:
            await self._audit.record(
                action="blocking_feedback_created",
                result="blocked",
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                entity_type=request.entity_type,
                entity_id=request.entity_id,
                reason=feedback_text,
                request=http_request,
            )
        return QualityFeedbackResponse.model_validate(created)

    async def list_feedback(
        self,
        limit: int = 100,
        offset: int = 0,
        entity_type: str | None = None,
        feedback_type: str | None = None,
        rating: int | None = None,
        review_status: str | None = None,
        is_blocking: bool | None = None,
    ) -> QualityFeedbackListResponse:
        items = await self._feedback.list(
            limit=limit,
            offset=offset,
            entity_type=entity_type,
            feedback_type=feedback_type,
            rating=rating,
            review_status=review_status,
            is_blocking=is_blocking,
        )
        return QualityFeedbackListResponse(
            items=[QualityFeedbackResponse.model_validate(f) for f in items],
            limit=limit,
            offset=offset,
        )

    async def get_entity_feedback(
        self, entity_type: str, entity_id: UUID, limit: int = 100, offset: int = 0
    ) -> QualityFeedbackListResponse:
        items = await self._feedback.list_for_entity(
            entity_type, entity_id, limit=limit, offset=offset
        )
        return QualityFeedbackListResponse(
            items=[QualityFeedbackResponse.model_validate(f) for f in items],
            limit=limit,
            offset=offset,
        )

    async def _get_or_404(self, feedback_id: UUID) -> UserFeedback:
        feedback = await self._feedback.get_by_id(feedback_id)
        if feedback is None:
            raise UserFeedbackNotFoundError(feedback_id)
        return feedback

    async def get_feedback(self, feedback_id: UUID) -> QualityFeedbackDetailResponse:
        feedback = await self._get_or_404(feedback_id)
        return QualityFeedbackDetailResponse(
            feedback=QualityFeedbackResponse.model_validate(feedback)
        )

    async def review_feedback(
        self,
        feedback_id: UUID,
        request: ReviewQualityFeedbackRequest,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> QualityFeedbackResponse:
        feedback = await self._get_or_404(feedback_id)
        feedback.review_status = request.review_status
        feedback.reviewed_by_user_id = actor_user_id
        updated = await self._feedback.update(feedback)
        assert updated is not None
        await self._audit.record(
            action="quality_feedback_reviewed",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type=updated.entity_type,
            entity_id=updated.entity_id,
            metadata={"feedback_id": str(updated.id), "review_status": request.review_status},
            request=http_request,
        )
        return QualityFeedbackResponse.model_validate(updated)

    async def archive_feedback(
        self,
        feedback_id: UUID,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> QualityFeedbackResponse:
        feedback = await self._get_or_404(feedback_id)
        feedback.review_status = "archived"
        feedback.reviewed_by_user_id = actor_user_id
        updated = await self._feedback.update(feedback)
        assert updated is not None
        await self._audit.record(
            action="quality_feedback_archived",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type=updated.entity_type,
            entity_id=updated.entity_id,
            metadata={"feedback_id": str(updated.id)},
            request=http_request,
        )
        return QualityFeedbackResponse.model_validate(updated)

    async def count_blocking_for_entity(self, entity_type: str, entity_id: UUID) -> int:
        return await self._feedback.count_blocking_for_entity(entity_type, entity_id)
