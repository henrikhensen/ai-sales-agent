from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.entities.qualification_run import QualificationRun
from backend.domain.repositories.qualification_run_repository import (
    QualificationRunRepository,
)
from backend.infrastructure.database.models.qualification_run import (
    QualificationRunModel,
)


class SQLAlchemyQualificationRunRepository(QualificationRunRepository):
    """SQLAlchemy-backed :class:`QualificationRunRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, run: QualificationRun) -> QualificationRun:
        orm_obj = QualificationRunModel(
            name=run.name,
            source_type=run.source_type,
            icp_profile_id=run.icp_profile_id,
            offer_profile_id=run.offer_profile_id,
            status=run.status,
            started_by_user_id=run.started_by_user_id,
            started_at=run.started_at,
            completed_at=run.completed_at,
            total_items=run.total_items,
            qualified_count=run.qualified_count,
            priority_count=run.priority_count,
            disqualified_count=run.disqualified_count,
            needs_review_count=run.needs_review_count,
            average_score=run.average_score,
            warnings=run.warnings,
        )
        self._session.add(orm_obj)
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def get_by_id(self, run_id: UUID) -> QualificationRun | None:
        orm_obj = await self._session.get(QualificationRunModel, run_id)
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def list(self, limit: int = 100, offset: int = 0) -> list[QualificationRun]:
        stmt = (
            select(QualificationRunModel)
            .order_by(QualificationRunModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def update(self, run: QualificationRun) -> QualificationRun | None:
        orm_obj = await self._session.get(QualificationRunModel, run.id)
        if orm_obj is None:
            return None
        orm_obj.status = run.status
        orm_obj.completed_at = run.completed_at
        orm_obj.total_items = run.total_items
        orm_obj.qualified_count = run.qualified_count
        orm_obj.priority_count = run.priority_count
        orm_obj.disqualified_count = run.disqualified_count
        orm_obj.needs_review_count = run.needs_review_count
        orm_obj.average_score = run.average_score
        orm_obj.warnings = run.warnings
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    @staticmethod
    def _to_entity(orm_obj: QualificationRunModel) -> QualificationRun:
        return QualificationRun(
            id=orm_obj.id,
            name=orm_obj.name,
            source_type=orm_obj.source_type,
            icp_profile_id=orm_obj.icp_profile_id,
            offer_profile_id=orm_obj.offer_profile_id,
            status=orm_obj.status,
            started_by_user_id=orm_obj.started_by_user_id,
            started_at=orm_obj.started_at,
            completed_at=orm_obj.completed_at,
            total_items=orm_obj.total_items,
            qualified_count=orm_obj.qualified_count,
            priority_count=orm_obj.priority_count,
            disqualified_count=orm_obj.disqualified_count,
            needs_review_count=orm_obj.needs_review_count,
            average_score=orm_obj.average_score,
            warnings=orm_obj.warnings,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )
