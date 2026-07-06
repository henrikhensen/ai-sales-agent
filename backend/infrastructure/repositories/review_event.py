from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.entities.review_event import ReviewEvent
from backend.domain.repositories.review_event_repository import ReviewEventRepository
from backend.infrastructure.database.models.review_event import ReviewEventModel


class SQLAlchemyReviewEventRepository(ReviewEventRepository):
    """SQLAlchemy-backed :class:`ReviewEventRepository`. Append-only audit log."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, event: ReviewEvent) -> ReviewEvent:
        orm_obj = ReviewEventModel(
            workflow_run_id=event.workflow_run_id,
            email_draft_id=event.email_draft_id,
            event_type=event.event_type,
            previous_status=event.previous_status,
            new_status=event.new_status,
            comment=event.comment,
            reviewer_name=event.reviewer_name,
            event_metadata=event.metadata,
        )
        self._session.add(orm_obj)
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def list_by_workflow_run(
        self, workflow_run_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[ReviewEvent]:
        stmt = (
            select(ReviewEventModel)
            .where(ReviewEventModel.workflow_run_id == workflow_run_id)
            .order_by(ReviewEventModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def list_by_email_draft(
        self, email_draft_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[ReviewEvent]:
        stmt = (
            select(ReviewEventModel)
            .where(ReviewEventModel.email_draft_id == email_draft_id)
            .order_by(ReviewEventModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    @staticmethod
    def _to_entity(orm_obj: ReviewEventModel) -> ReviewEvent:
        return ReviewEvent(
            id=orm_obj.id,
            workflow_run_id=orm_obj.workflow_run_id,
            email_draft_id=orm_obj.email_draft_id,
            event_type=orm_obj.event_type,
            previous_status=orm_obj.previous_status,
            new_status=orm_obj.new_status,
            comment=orm_obj.comment,
            reviewer_name=orm_obj.reviewer_name,
            metadata=orm_obj.event_metadata,
            created_at=orm_obj.created_at,
        )
