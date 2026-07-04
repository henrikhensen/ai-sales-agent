from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from uuid import UUID

EntityType = TypeVar("EntityType")


class AbstractRepository(ABC, Generic[EntityType]):
    """Persistence port for a domain entity.

    Defined in the domain layer so that application use cases depend only on
    this abstraction, never on a concrete database implementation.
    """

    @abstractmethod
    async def create(self, entity: EntityType) -> EntityType:
        """Persist a new entity and return it with generated fields populated."""

    @abstractmethod
    async def get(self, entity_id: UUID) -> EntityType | None:
        """Return the entity with the given id, or None if it does not exist."""

    @abstractmethod
    async def list(self, limit: int = 100, offset: int = 0) -> list[EntityType]:
        """Return a page of entities ordered from newest to oldest."""

    @abstractmethod
    async def update(self, entity: EntityType) -> EntityType | None:
        """Persist changes to an existing entity, or None if it does not exist."""

    @abstractmethod
    async def delete(self, entity_id: UUID) -> bool:
        """Delete the entity with the given id. Returns True if one was removed."""
