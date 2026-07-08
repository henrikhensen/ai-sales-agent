from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.entities.data_retention_policy import DataRetentionPolicy
from backend.domain.repositories.data_retention_policy_repository import (
    DataRetentionPolicyRepository,
)
from backend.infrastructure.database.models.data_retention_policy import (
    DataRetentionPolicyModel,
)


class SQLAlchemyDataRetentionPolicyRepository(DataRetentionPolicyRepository):
    """SQLAlchemy-backed :class:`DataRetentionPolicyRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, policy: DataRetentionPolicy) -> DataRetentionPolicy:
        orm_obj = DataRetentionPolicyModel(
            name=policy.name,
            entity_type=policy.entity_type,
            retention_days=policy.retention_days,
            action=policy.action,
            is_active=policy.is_active,
            dry_run_default=policy.dry_run_default,
            created_by_user_id=policy.created_by_user_id,
        )
        self._session.add(orm_obj)
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def get_by_id(self, policy_id: UUID) -> DataRetentionPolicy | None:
        orm_obj = await self._session.get(DataRetentionPolicyModel, policy_id)
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def update(
        self, policy: DataRetentionPolicy
    ) -> DataRetentionPolicy | None:
        orm_obj = await self._session.get(DataRetentionPolicyModel, policy.id)
        if orm_obj is None:
            return None
        orm_obj.name = policy.name
        orm_obj.entity_type = policy.entity_type
        orm_obj.retention_days = policy.retention_days
        orm_obj.action = policy.action
        orm_obj.is_active = policy.is_active
        orm_obj.dry_run_default = policy.dry_run_default
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        active_only: bool = False,
        entity_type: str | None = None,
    ) -> list[DataRetentionPolicy]:
        stmt = select(DataRetentionPolicyModel)
        if active_only:
            stmt = stmt.where(DataRetentionPolicyModel.is_active.is_(True))
        if entity_type is not None:
            stmt = stmt.where(DataRetentionPolicyModel.entity_type == entity_type)
        stmt = stmt.order_by(DataRetentionPolicyModel.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    @staticmethod
    def _to_entity(orm_obj: DataRetentionPolicyModel) -> DataRetentionPolicy:
        return DataRetentionPolicy(
            id=orm_obj.id,
            name=orm_obj.name,
            entity_type=orm_obj.entity_type,
            retention_days=orm_obj.retention_days,
            action=orm_obj.action,
            is_active=orm_obj.is_active,
            dry_run_default=orm_obj.dry_run_default,
            created_by_user_id=orm_obj.created_by_user_id,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )
