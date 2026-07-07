from abc import ABC, abstractmethod
from uuid import UUID

from backend.domain.entities.offer_profile import OfferProfile


class OfferProfileRepository(ABC):
    """Persistence port for :class:`OfferProfile` records."""

    @abstractmethod
    async def create(self, profile: OfferProfile) -> OfferProfile:
        """Persist a new offer profile and return it with generated fields."""

    @abstractmethod
    async def list(
        self, limit: int = 100, offset: int = 0, active_only: bool = False
    ) -> list[OfferProfile]:
        """Return offer profiles, newest first, optionally filtered to active ones."""

    @abstractmethod
    async def get_by_id(self, profile_id: UUID) -> OfferProfile | None:
        """Return a single offer profile, or None if it does not exist."""

    @abstractmethod
    async def update(self, profile: OfferProfile) -> OfferProfile | None:
        """Persist changes to an existing offer profile, or None if it
        does not exist."""

    @abstractmethod
    async def deactivate(self, profile_id: UUID) -> OfferProfile | None:
        """Set ``is_active=False``, or None if the profile does not exist."""

    @abstractmethod
    async def get_active(self, profile_id: UUID) -> OfferProfile | None:
        """Return the profile only if it exists and ``is_active`` is True."""
