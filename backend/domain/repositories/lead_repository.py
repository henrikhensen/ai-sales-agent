from abc import abstractmethod
from uuid import UUID

from backend.domain.entities.lead import Lead
from backend.domain.repositories.base import AbstractRepository


class LeadRepository(AbstractRepository[Lead]):
    """Persistence port for :class:`Lead` entities."""

    @abstractmethod
    async def list_by_company(
        self, company_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[Lead]:
        """Return leads belonging to a single company, newest first."""
