from abc import abstractmethod
from uuid import UUID

from backend.domain.entities.reply import Reply
from backend.domain.enums import EmailProviderType, ReplyCategory, ReplySentiment
from backend.domain.repositories.base import AbstractRepository


class ReplyRepository(AbstractRepository[Reply]):
    """Persistence port for :class:`Reply` records.

    No business logic lives here — reply analysis, do-not-contact signal
    detection, and pipeline recommendations are all the application
    service's job, not the repository's.
    """

    @abstractmethod
    async def get_by_provider_message_id(
        self, provider: EmailProviderType, provider_message_id: str
    ) -> Reply | None:
        """Return the reply already stored for this provider message, if
        any — used to avoid storing the same message twice."""

    @abstractmethod
    async def list_by_lead(
        self, lead_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[Reply]:
        """Return replies for a single lead, newest first."""

    @abstractmethod
    async def list_by_email_draft(
        self, email_draft_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[Reply]:
        """Return replies linked to a single email draft, newest first."""

    @abstractmethod
    async def list_filtered(
        self,
        *,
        category: ReplyCategory | None = None,
        sentiment: ReplySentiment | None = None,
        is_read: bool | None = None,
        is_archived: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Reply]:
        """Return replies matching every given filter, newest first."""

    @abstractmethod
    async def mark_read(self, reply_id: UUID, is_read: bool = True) -> Reply | None:
        """Set a reply's read flag. Returns None if it does not exist."""

    @abstractmethod
    async def archive(
        self, reply_id: UUID, is_archived: bool = True
    ) -> Reply | None:
        """Set a reply's archived flag. Returns None if it does not exist."""
