from abc import ABC, abstractmethod
from uuid import UUID

from backend.domain.entities.review_event import ReviewEvent


class ReviewEventRepository(ABC):
    """Persistence port for :class:`ReviewEvent` audit records.

    Deliberately narrower than :class:`AbstractRepository`: review events are
    an append-only audit log, never updated or deleted through the API.
    """

    @abstractmethod
    async def create(self, event: ReviewEvent) -> ReviewEvent:
        """Persist a new review event and return it with generated fields populated."""

    @abstractmethod
    async def list_by_workflow_run(
        self, workflow_run_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[ReviewEvent]:
        """Return events recorded against a single workflow run, newest first."""

    @abstractmethod
    async def list_by_email_draft(
        self, email_draft_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[ReviewEvent]:
        """Return events recorded against a single email draft, newest first."""
