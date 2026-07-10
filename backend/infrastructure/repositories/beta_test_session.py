from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.entities.beta_test_session import BetaTestSession
from backend.domain.repositories.beta_test_session_repository import (
    BetaTestSessionRepository,
)
from backend.infrastructure.database.models.beta_test_session import (
    BetaTestSessionModel,
)


class SQLAlchemyBetaTestSessionRepository(BetaTestSessionRepository):
    """SQLAlchemy-backed :class:`BetaTestSessionRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, session: BetaTestSession) -> BetaTestSession:
        orm_obj = BetaTestSessionModel(
            name=session.name,
            description=session.description,
            tester_user_id=session.tester_user_id,
            status=session.status,
            started_at=session.started_at,
            completed_at=session.completed_at,
            target_goal=session.target_goal,
            total_workflows_tested=session.total_workflows_tested,
            total_drafts_reviewed=session.total_drafts_reviewed,
            total_feedback_items=session.total_feedback_items,
            average_quality_score=session.average_quality_score,
            blockers_count=session.blockers_count,
            bugs_count=session.bugs_count,
            notes=session.notes,
        )
        self._session.add(orm_obj)
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def get_by_id(self, session_id: UUID) -> BetaTestSession | None:
        orm_obj = await self._session.get(BetaTestSessionModel, session_id)
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def update(self, session: BetaTestSession) -> BetaTestSession | None:
        orm_obj = await self._session.get(BetaTestSessionModel, session.id)
        if orm_obj is None:
            return None
        orm_obj.name = session.name
        orm_obj.description = session.description
        orm_obj.status = session.status
        orm_obj.started_at = session.started_at
        orm_obj.completed_at = session.completed_at
        orm_obj.target_goal = session.target_goal
        orm_obj.total_workflows_tested = session.total_workflows_tested
        orm_obj.total_drafts_reviewed = session.total_drafts_reviewed
        orm_obj.total_feedback_items = session.total_feedback_items
        orm_obj.average_quality_score = session.average_quality_score
        orm_obj.blockers_count = session.blockers_count
        orm_obj.bugs_count = session.bugs_count
        orm_obj.notes = session.notes
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def list(
        self, limit: int = 100, offset: int = 0, status: str | None = None
    ) -> list[BetaTestSession]:
        stmt = select(BetaTestSessionModel)
        if status is not None:
            stmt = stmt.where(BetaTestSessionModel.status == status)
        stmt = stmt.order_by(BetaTestSessionModel.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    @staticmethod
    def _to_entity(orm_obj: BetaTestSessionModel) -> BetaTestSession:
        return BetaTestSession(
            id=orm_obj.id,
            name=orm_obj.name,
            description=orm_obj.description,
            tester_user_id=orm_obj.tester_user_id,
            status=orm_obj.status,
            started_at=orm_obj.started_at,
            completed_at=orm_obj.completed_at,
            target_goal=orm_obj.target_goal,
            total_workflows_tested=orm_obj.total_workflows_tested,
            total_drafts_reviewed=orm_obj.total_drafts_reviewed,
            total_feedback_items=orm_obj.total_feedback_items,
            average_quality_score=orm_obj.average_quality_score,
            blockers_count=orm_obj.blockers_count,
            bugs_count=orm_obj.bugs_count,
            notes=orm_obj.notes,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )
