from abc import ABC, abstractmethod
from uuid import UUID

from backend.domain.entities.onboarding_status import OnboardingStatus


class OnboardingStatusRepository(ABC):
    """Persistence port for :class:`OnboardingStatus` records — one per user."""

    @abstractmethod
    async def create(self, status: OnboardingStatus) -> OnboardingStatus:
        """Persist a new onboarding status and return it with generated fields."""

    @abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> OnboardingStatus | None:
        """Return this user's onboarding status, or None if never started."""

    @abstractmethod
    async def update(self, status: OnboardingStatus) -> OnboardingStatus | None:
        """Persist changes to an existing onboarding status, or None if it
        does not exist."""

    @abstractmethod
    async def list_all(
        self, limit: int = 100, offset: int = 0
    ) -> list[OnboardingStatus]:
        """Return every user's onboarding status, newest first (admin-only
        use case)."""
