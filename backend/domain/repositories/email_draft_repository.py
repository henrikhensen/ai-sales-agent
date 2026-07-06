from abc import abstractmethod
from uuid import UUID

from backend.domain.entities.email_draft import EmailDraft
from backend.domain.repositories.base import AbstractRepository


class EmailDraftRepository(AbstractRepository[EmailDraft]):
    """Persistence port for :class:`EmailDraft` entities."""

    @abstractmethod
    async def list_by_company(
        self, company_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[EmailDraft]:
        """Return email drafts belonging to a single company, newest first."""
