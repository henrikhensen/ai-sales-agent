from abc import abstractmethod
from uuid import UUID

from backend.domain.entities.contact import Contact
from backend.domain.repositories.base import AbstractRepository


class ContactRepository(AbstractRepository[Contact]):
    """Persistence port for :class:`Contact` entities."""

    @abstractmethod
    async def find_by_company_and_name(
        self, company_id: UUID, first_name: str, last_name: str
    ) -> Contact | None:
        """Return the contact at this company matching this name, if any."""

    @abstractmethod
    async def list_by_company(
        self, company_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[Contact]:
        """Return contacts belonging to a single company, newest first."""
