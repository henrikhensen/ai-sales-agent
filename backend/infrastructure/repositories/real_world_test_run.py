from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.entities.real_world_test_run import RealWorldTestRun
from backend.domain.repositories.real_world_test_run_repository import (
    RealWorldTestRunRepository,
)
from backend.infrastructure.database.models.real_world_test_run import (
    RealWorldTestRunModel,
)


class SQLAlchemyRealWorldTestRunRepository(RealWorldTestRunRepository):
    """SQLAlchemy-backed :class:`RealWorldTestRunRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, run: RealWorldTestRun) -> RealWorldTestRun:
        orm_obj = RealWorldTestRunModel(
            name=run.name,
            status=run.status,
            mode=run.mode,
            lead_candidate_id=run.lead_candidate_id,
            lead_id=run.lead_id,
            icp_profile_id=run.icp_profile_id,
            offer_profile_id=run.offer_profile_id,
            workflow_run_id=run.workflow_run_id,
            quality_score_id=run.quality_score_id,
            input_snapshot=run.input_snapshot,
            result_snapshot=run.result_snapshot,
            warnings=run.warnings,
            errors=run.errors,
            created_by_user_id=run.created_by_user_id,
            aborted_at=run.aborted_at,
        )
        self._session.add(orm_obj)
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def get_by_id(self, run_id: UUID) -> RealWorldTestRun | None:
        orm_obj = await self._session.get(RealWorldTestRunModel, run_id)
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def update(self, run: RealWorldTestRun) -> RealWorldTestRun | None:
        orm_obj = await self._session.get(RealWorldTestRunModel, run.id)
        if orm_obj is None:
            return None
        orm_obj.name = run.name
        orm_obj.status = run.status
        orm_obj.mode = run.mode
        orm_obj.lead_candidate_id = run.lead_candidate_id
        orm_obj.lead_id = run.lead_id
        orm_obj.icp_profile_id = run.icp_profile_id
        orm_obj.offer_profile_id = run.offer_profile_id
        orm_obj.workflow_run_id = run.workflow_run_id
        orm_obj.quality_score_id = run.quality_score_id
        orm_obj.input_snapshot = run.input_snapshot
        orm_obj.result_snapshot = run.result_snapshot
        orm_obj.warnings = run.warnings
        orm_obj.errors = run.errors
        orm_obj.aborted_at = run.aborted_at
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        status: str | None = None,
        created_by_user_id: UUID | None = None,
    ) -> list[RealWorldTestRun]:
        stmt = select(RealWorldTestRunModel)
        if status is not None:
            stmt = stmt.where(RealWorldTestRunModel.status == status)
        if created_by_user_id is not None:
            stmt = stmt.where(RealWorldTestRunModel.created_by_user_id == created_by_user_id)
        stmt = (
            stmt.order_by(RealWorldTestRunModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    @staticmethod
    def _to_entity(orm_obj: RealWorldTestRunModel) -> RealWorldTestRun:
        return RealWorldTestRun(
            id=orm_obj.id,
            name=orm_obj.name,
            status=orm_obj.status,
            mode=orm_obj.mode,
            lead_candidate_id=orm_obj.lead_candidate_id,
            lead_id=orm_obj.lead_id,
            icp_profile_id=orm_obj.icp_profile_id,
            offer_profile_id=orm_obj.offer_profile_id,
            workflow_run_id=orm_obj.workflow_run_id,
            quality_score_id=orm_obj.quality_score_id,
            input_snapshot=orm_obj.input_snapshot,
            result_snapshot=orm_obj.result_snapshot,
            warnings=orm_obj.warnings,
            errors=orm_obj.errors,
            created_by_user_id=orm_obj.created_by_user_id,
            aborted_at=orm_obj.aborted_at,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )
