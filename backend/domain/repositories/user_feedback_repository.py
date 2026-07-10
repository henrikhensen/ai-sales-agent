from abc import ABC, abstractmethod
from uuid import UUID

from backend.domain.entities.user_feedback import UserFeedback


class UserFeedbackRepository(ABC):
    """Persistence port for :class:`UserFeedback` records."""

    @abstractmethod
    async def create(self, feedback: UserFeedback) -> UserFeedback:
        """Persist new feedback and return it with generated fields populated."""

    @abstractmethod
    async def get_by_id(self, feedback_id: UUID) -> UserFeedback | None:
        """Return a single feedback item, or None if it does not exist."""

    @abstractmethod
    async def update(self, feedback: UserFeedback) -> UserFeedback | None:
        """Persist changes to existing feedback, or None if it does not exist."""

    @abstractmethod
    async def list_for_entity(
        self, entity_type: str, entity_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[UserFeedback]:
        """Return every feedback item for this entity, newest first."""

    @abstractmethod
    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        entity_type: str | None = None,
        feedback_type: str | None = None,
        rating: int | None = None,
        review_status: str | None = None,
        is_blocking: bool | None = None,
        priority: str | None = None,
    ) -> list[UserFeedback]:
        """Return feedback items, newest first, optionally filtered."""

    @abstractmethod
    async def count_blocking_for_entity(
        self, entity_type: str, entity_id: UUID
    ) -> int:
        """Count open, blocking feedback items for this entity — used by
        Dispatch Readiness and Review warnings."""
