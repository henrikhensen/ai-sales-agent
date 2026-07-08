from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.entities.audit_log import AuditLog
from backend.domain.repositories.audit_log_repository import AuditLogRepository
from backend.infrastructure.database.models.audit_log import AuditLogModel
from backend.infrastructure.database.session import independent_session


class SQLAlchemyAuditLogRepository(AuditLogRepository):
    """SQLAlchemy-backed :class:`AuditLogRepository`. Append-only audit log."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _build_orm(entry: AuditLog) -> AuditLogModel:
        return AuditLogModel(
            actor_user_id=entry.actor_user_id,
            actor_role=entry.actor_role,
            action=entry.action,
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            result=entry.result,
            reason=entry.reason,
            request_id=entry.request_id,
            ip_hash=entry.ip_hash,
            user_agent=entry.user_agent,
            audit_metadata=entry.metadata,
        )

    async def create(self, entry: AuditLog) -> AuditLog:
        orm_obj = self._build_orm(entry)
        self._session.add(orm_obj)
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def create_independent(self, entry: AuditLog) -> AuditLog:
        """Commit through a fresh, independent session — see
        ``AuditLogRepository.create_independent`` for why."""
        orm_obj = self._build_orm(entry)
        async with independent_session() as session:
            session.add(orm_obj)
            await session.flush()
            await session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def get(self, entry_id: UUID) -> AuditLog | None:
        orm_obj = await self._session.get(AuditLogModel, entry_id)
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def list_filtered(
        self,
        *,
        actor_user_id: UUID | None = None,
        action: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        result: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        stmt = select(AuditLogModel)
        if actor_user_id is not None:
            stmt = stmt.where(AuditLogModel.actor_user_id == actor_user_id)
        if action is not None:
            stmt = stmt.where(AuditLogModel.action == action)
        if entity_type is not None:
            stmt = stmt.where(AuditLogModel.entity_type == entity_type)
        if entity_id is not None:
            stmt = stmt.where(AuditLogModel.entity_id == entity_id)
        if result is not None:
            stmt = stmt.where(AuditLogModel.result == result)
        if date_from is not None:
            stmt = stmt.where(AuditLogModel.created_at >= date_from)
        if date_to is not None:
            stmt = stmt.where(AuditLogModel.created_at <= date_to)
        stmt = stmt.order_by(AuditLogModel.created_at.desc()).limit(limit).offset(offset)
        result_rows = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result_rows.scalars().all()]

    @staticmethod
    def _to_entity(orm_obj: AuditLogModel) -> AuditLog:
        return AuditLog(
            id=orm_obj.id,
            actor_user_id=orm_obj.actor_user_id,
            actor_role=orm_obj.actor_role,
            action=orm_obj.action,
            entity_type=orm_obj.entity_type,
            entity_id=orm_obj.entity_id,
            result=orm_obj.result,
            reason=orm_obj.reason,
            request_id=orm_obj.request_id,
            ip_hash=orm_obj.ip_hash,
            user_agent=orm_obj.user_agent,
            metadata=orm_obj.audit_metadata,
            created_at=orm_obj.created_at,
        )
