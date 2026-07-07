from abc import ABC, abstractmethod
from uuid import UUID

from backend.domain.entities.icp_profile import ICPProfile


class ICPProfileRepository(ABC):
    """Persistence port for :class:`ICPProfile` records."""

    @abstractmethod
    async def create(self, profile: ICPProfile) -> ICPProfile:
        """Persist a new ICP profile and return it with generated fields."""

    @abstractmethod
    async def list(
        self, limit: int = 100, offset: int = 0, active_only: bool = False
    ) -> list[ICPProfile]:
        """Return ICP profiles, newest first, optionally filtered to active ones."""

    @abstractmethod
    async def get_by_id(self, profile_id: UUID) -> ICPProfile | None:
        """Return a single ICP profile, or None if it does not exist."""

    @abstractmethod
    async def update(self, profile: ICPProfile) -> ICPProfile | None:
        """Persist changes to an existing ICP profile, or None if it does
        not exist."""

    @abstractmethod
    async def deactivate(self, profile_id: UUID) -> ICPProfile | None:
        """Set ``is_active=False``, or None if the profile does not exist."""

    @abstractmethod
    async def get_active(self, profile_id: UUID) -> ICPProfile | None:
        """Return the profile only if it exists and ``is_active`` is True."""
