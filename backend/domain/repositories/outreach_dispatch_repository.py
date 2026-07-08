from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from backend.domain.entities.outreach_dispatch import OutreachDispatch


class OutreachDispatchRepository(ABC):
    """Persistence port for :class:`OutreachDispatch` records."""

    @abstractmethod
    async def create(self, dispatch: OutreachDispatch) -> OutreachDispatch:
        """Persist a new dispatch attempt and return it with generated fields."""

    @abstractmethod
    async def get_by_id(self, dispatch_id: UUID) -> OutreachDispatch | None:
        """Return a single dispatch attempt, or None if it does not exist."""

    @abstractmethod
    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        queue_item_id: UUID | None = None,
        dispatch_status: str | None = None,
    ) -> list[OutreachDispatch]:
        """Return dispatch attempts, newest first, optionally filtered."""

    @abstractmethod
    async def update(self, dispatch: OutreachDispatch) -> OutreachDispatch | None:
        """Persist changes to an existing dispatch attempt, or None if it
        does not exist."""

    @abstractmethod
    async def find_active_for_queue_item(
        self, queue_item_id: UUID
    ) -> OutreachDispatch | None:
        """Return the most recent non-terminal dispatch attempt for this
        queue item, if any (used to avoid creating a duplicate in-flight
        attempt for the same item)."""

    @abstractmethod
    async def count_since(
        self, created_by_user_id: UUID | None, since: datetime
    ) -> int:
        """Count non-cancelled/failed dispatch attempts created by this
        user since ``since`` — the business-level hourly/daily volume cap,
        distinct from the per-user API rate limit."""
