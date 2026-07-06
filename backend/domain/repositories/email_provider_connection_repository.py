from abc import abstractmethod
from uuid import UUID

from backend.domain.entities.email_provider_connection import EmailProviderConnection
from backend.domain.enums import EmailProviderType
from backend.domain.repositories.base import AbstractRepository


class EmailProviderConnectionRepository(AbstractRepository[EmailProviderConnection]):
    """Persistence port for :class:`EmailProviderConnection` records.

    No business logic lives here — token encryption/decryption and OAuth
    flow orchestration are the application/infrastructure layers' job.
    """

    @abstractmethod
    async def get_active_for_user(
        self, user_id: UUID, provider: EmailProviderType
    ) -> EmailProviderConnection | None:
        """Return the user's active connection for ``provider``, if any."""

    @abstractmethod
    async def deactivate_for_user(
        self, user_id: UUID, provider: EmailProviderType
    ) -> EmailProviderConnection | None:
        """Deactivate the user's connection for ``provider``, if any."""
