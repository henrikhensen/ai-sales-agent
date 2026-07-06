from abc import abstractmethod
from uuid import UUID

from backend.domain.entities.do_not_contact_entry import DoNotContactEntry
from backend.domain.repositories.base import AbstractRepository


class DoNotContactRepository(AbstractRepository[DoNotContactEntry]):
    """Persistence port for :class:`DoNotContactEntry` records.

    No business logic lives here — matching rules (e.g. that a domain entry
    blocks every email at that domain) are the application service's job,
    not the repository's. This only ever performs plain lookups.
    """

    @abstractmethod
    async def deactivate(self, entry_id: UUID) -> DoNotContactEntry | None:
        """Set ``is_active=False`` on an entry. Returns None if it doesn't exist."""

    @abstractmethod
    async def find_active_by_email(self, email: str) -> DoNotContactEntry | None:
        """Return the active entry matching this exact (lowercase) email, if any."""

    @abstractmethod
    async def find_active_by_domain(self, domain: str) -> DoNotContactEntry | None:
        """Return the active entry matching this exact (lowercase) domain, if any."""

    @abstractmethod
    async def find_active_by_company_name(
        self, company_name_normalized: str
    ) -> DoNotContactEntry | None:
        """Return the active entry matching this normalized company name, if any."""
