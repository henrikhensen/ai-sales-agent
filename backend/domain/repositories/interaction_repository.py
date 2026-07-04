from abc import abstractmethod
from uuid import UUID

from backend.domain.entities.interaction import Interaction
from backend.domain.repositories.base import AbstractRepository


class InteractionRepository(AbstractRepository[Interaction]):
    """Persistence port for :class:`Interaction` entities."""

    @abstractmethod
    async def list_by_lead(
        self, lead_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[Interaction]:
        """Return interactions recorded against a single lead, newest first."""
