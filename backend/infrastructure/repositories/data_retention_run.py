from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.entities.data_retention_run import DataRetentionRun
from backend.domain.repositories.data_retention_run_repository import (
    DataRetentionRunRepository,
)
from backend.infrastructure.database.models.data_retention_run import (
    DataRetentionRunModel,
)


class SQLAlchemyDataRetentionRunRepository(DataRetentionRunRepository):
    """SQLAlchemy-backed :class:`DataRetentionRunRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, run: DataRetentionRun) -> DataRetentionRun:
        orm_obj = DataRetentionRunModel(
            policy_id=run.policy_id,
            entity_type=run.entity_type,
            action=run.action,
            dry_run=run.dry_run,
            status=run.status,
            started_by_user_id=run.started_by_user_id,
            started_at=run.started_at,
            completed_at=run.completed_at,
            total_scanned=run.total_scanned,
            total_eligible=run.total_eligible,
            total_processed=run.total_processed,
            total_failed=run.total_failed,
            warnings=run.warnings,
            errors=run.errors,
        )
        self._session.add(orm_obj)
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def get_by_id(self, run_id: UUID) -> DataRetentionRun | None:
        orm_obj = await self._session.get(DataRetentionRunModel, run_id)
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def update(self, run: DataRetentionRun) -> DataRetentionRun | None:
        orm_obj = await self._session.get(DataRetentionRunModel, run.id)
        if orm_obj is None:
            return None
        orm_obj.status = run.status
        orm_obj.completed_at = run.completed_at
        orm_obj.total_scanned = run.total_scanned
        orm_obj.total_eligible = run.total_eligible
        orm_obj.total_processed = run.total_processed
        orm_obj.total_failed = run.total_failed
        orm_obj.warnings = run.warnings
        orm_obj.errors = run.errors
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        policy_id: UUID | None = None,
    ) -> list[DataRetentionRun]:
        stmt = select(DataRetentionRunModel)
        if policy_id is not None:
            stmt = stmt.where(DataRetentionRunModel.policy_id == policy_id)
        stmt = stmt.order_by(DataRetentionRunModel.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    @staticmethod
    def _to_entity(orm_obj: DataRetentionRunModel) -> DataRetentionRun:
        return DataRetentionRun(
            id=orm_obj.id,
            policy_id=orm_obj.policy_id,
            entity_type=orm_obj.entity_type,
            action=orm_obj.action,
            dry_run=orm_obj.dry_run,
            status=orm_obj.status,
            started_by_user_id=orm_obj.started_by_user_id,
            started_at=orm_obj.started_at,
            completed_at=orm_obj.completed_at,
            total_scanned=orm_obj.total_scanned,
            total_eligible=orm_obj.total_eligible,
            total_processed=orm_obj.total_processed,
            total_failed=orm_obj.total_failed,
            warnings=orm_obj.warnings,
            errors=orm_obj.errors,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )
