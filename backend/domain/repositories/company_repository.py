from abc import abstractmethod

from backend.domain.entities.company import Company
from backend.domain.repositories.base import AbstractRepository


class CompanyRepository(AbstractRepository[Company]):
    """Persistence port for :class:`Company` entities."""

    @abstractmethod
    async def find_by_name(self, name: str) -> Company | None:
        """Return the company matching this name case-insensitively, if any."""
