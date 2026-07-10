from abc import ABC, abstractmethod
from uuid import UUID

from backend.domain.entities.beta_test_session import BetaTestSession


class BetaTestSessionRepository(ABC):
    """Persistence port for :class:`BetaTestSession` records."""

    @abstractmethod
    async def create(self, session: BetaTestSession) -> BetaTestSession:
        """Persist a new session and return it with generated fields populated."""

    @abstractmethod
    async def get_by_id(self, session_id: UUID) -> BetaTestSession | None:
        """Return a single session, or None if it does not exist."""

    @abstractmethod
    async def update(self, session: BetaTestSession) -> BetaTestSession | None:
        """Persist changes to an existing session, or None if it does not exist."""

    @abstractmethod
    async def list(
        self, limit: int = 100, offset: int = 0, status: str | None = None
    ) -> list[BetaTestSession]:
        """Return sessions, newest first, optionally filtered by status."""
