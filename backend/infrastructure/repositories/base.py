from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.infrastructure.database.base import Base

ORMType = TypeVar("ORMType", bound=Base)
EntityType = TypeVar("EntityType")


class SQLAlchemyRepository(ABC, Generic[ORMType, EntityType]):
    """Async SQLAlchemy implementation of the generic CRUD contract.

    Concrete repositories bind ``model`` and provide the mapping between the
    ORM row and the pure domain entity. No business logic lives here.
    """

    model: type[ORMType]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -- mapping hooks (implemented per concrete repository) --------------

    @abstractmethod
    def _to_entity(self, orm_obj: ORMType) -> EntityType:
        """Map an ORM row to its domain entity."""

    @abstractmethod
    def _to_orm(self, entity: EntityType) -> ORMType:
        """Build a new ORM row from a domain entity (for inserts)."""

    @abstractmethod
    def _apply(self, orm_obj: ORMType, entity: EntityType) -> None:
        """Copy mutable fields from a domain entity onto an existing ORM row."""

    # -- CRUD --------------------------------------------------------------

    async def create(self, entity: EntityType) -> EntityType:
        orm_obj = self._to_orm(entity)
        self._session.add(orm_obj)
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def get(self, entity_id: UUID) -> EntityType | None:
        orm_obj = await self._session.get(self.model, entity_id)
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def list(self, limit: int = 100, offset: int = 0) -> list[EntityType]:
        stmt = (
            select(self.model)
            .order_by(self.model.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def update(self, entity: EntityType) -> EntityType | None:
        orm_obj = await self._session.get(self.model, entity.id)
        if orm_obj is None:
            return None
        self._apply(orm_obj, entity)
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def delete(self, entity_id: UUID) -> bool:
        orm_obj = await self._session.get(self.model, entity_id)
        if orm_obj is None:
            return False
        await self._session.delete(orm_obj)
        await self._session.flush()
        return True
