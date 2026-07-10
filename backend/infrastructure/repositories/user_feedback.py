from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.entities.user_feedback import UserFeedback
from backend.domain.repositories.user_feedback_repository import (
    UserFeedbackRepository,
)
from backend.infrastructure.database.models.user_feedback import UserFeedbackModel


class SQLAlchemyUserFeedbackRepository(UserFeedbackRepository):
    """SQLAlchemy-backed :class:`UserFeedbackRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, feedback: UserFeedback) -> UserFeedback:
        orm_obj = UserFeedbackModel(
            entity_type=feedback.entity_type,
            entity_id=feedback.entity_id,
            rating=feedback.rating,
            feedback_type=feedback.feedback_type,
            priority=feedback.priority,
            feedback_text=feedback.feedback_text,
            issue_tags=feedback.issue_tags,
            improvement_tags=feedback.improvement_tags,
            is_blocking=feedback.is_blocking,
            workflow_run_id=feedback.workflow_run_id,
            email_draft_id=feedback.email_draft_id,
            lead_id=feedback.lead_id,
            company_id=feedback.company_id,
            lead_candidate_id=feedback.lead_candidate_id,
            qualification_result_id=feedback.qualification_result_id,
            outreach_queue_item_id=feedback.outreach_queue_item_id,
            reply_id=feedback.reply_id,
            real_world_test_run_id=feedback.real_world_test_run_id,
            submitted_by_user_id=feedback.submitted_by_user_id,
            reviewed_by_user_id=feedback.reviewed_by_user_id,
            review_status=feedback.review_status,
        )
        self._session.add(orm_obj)
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def get_by_id(self, feedback_id: UUID) -> UserFeedback | None:
        orm_obj = await self._session.get(UserFeedbackModel, feedback_id)
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def update(self, feedback: UserFeedback) -> UserFeedback | None:
        orm_obj = await self._session.get(UserFeedbackModel, feedback.id)
        if orm_obj is None:
            return None
        orm_obj.review_status = feedback.review_status
        orm_obj.reviewed_by_user_id = feedback.reviewed_by_user_id
        orm_obj.is_blocking = feedback.is_blocking
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def list_for_entity(
        self, entity_type: str, entity_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[UserFeedback]:
        stmt = (
            select(UserFeedbackModel)
            .where(
                UserFeedbackModel.entity_type == entity_type,
                UserFeedbackModel.entity_id == entity_id,
            )
            .order_by(UserFeedbackModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        entity_type: str | None = None,
        feedback_type: str | None = None,
        rating: int | None = None,
        review_status: str | None = None,
        is_blocking: bool | None = None,
        priority: str | None = None,
    ) -> list[UserFeedback]:
        stmt = select(UserFeedbackModel)
        if entity_type is not None:
            stmt = stmt.where(UserFeedbackModel.entity_type == entity_type)
        if feedback_type is not None:
            stmt = stmt.where(UserFeedbackModel.feedback_type == feedback_type)
        if rating is not None:
            stmt = stmt.where(UserFeedbackModel.rating == rating)
        if review_status is not None:
            stmt = stmt.where(UserFeedbackModel.review_status == review_status)
        if is_blocking is not None:
            stmt = stmt.where(UserFeedbackModel.is_blocking == is_blocking)
        if priority is not None:
            stmt = stmt.where(UserFeedbackModel.priority == priority)
        stmt = stmt.order_by(UserFeedbackModel.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def count_blocking_for_entity(self, entity_type: str, entity_id: UUID) -> int:
        stmt = select(func.count()).select_from(UserFeedbackModel).where(
            UserFeedbackModel.entity_type == entity_type,
            UserFeedbackModel.entity_id == entity_id,
            UserFeedbackModel.is_blocking.is_(True),
            UserFeedbackModel.review_status.in_(("open", "reviewed", "accepted")),
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    @staticmethod
    def _to_entity(orm_obj: UserFeedbackModel) -> UserFeedback:
        return UserFeedback(
            id=orm_obj.id,
            entity_type=orm_obj.entity_type,
            entity_id=orm_obj.entity_id,
            rating=orm_obj.rating,
            feedback_type=orm_obj.feedback_type,
            priority=orm_obj.priority,
            feedback_text=orm_obj.feedback_text,
            issue_tags=orm_obj.issue_tags,
            improvement_tags=orm_obj.improvement_tags,
            is_blocking=orm_obj.is_blocking,
            workflow_run_id=orm_obj.workflow_run_id,
            email_draft_id=orm_obj.email_draft_id,
            lead_id=orm_obj.lead_id,
            company_id=orm_obj.company_id,
            lead_candidate_id=orm_obj.lead_candidate_id,
            qualification_result_id=orm_obj.qualification_result_id,
            outreach_queue_item_id=orm_obj.outreach_queue_item_id,
            reply_id=orm_obj.reply_id,
            real_world_test_run_id=orm_obj.real_world_test_run_id,
            submitted_by_user_id=orm_obj.submitted_by_user_id,
            reviewed_by_user_id=orm_obj.reviewed_by_user_id,
            review_status=orm_obj.review_status,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )
