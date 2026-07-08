from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from backend.domain.entities.outreach_queue_item import OutreachQueueItem


class OutreachQueueItemRepository(ABC):
    """Persistence port for :class:`OutreachQueueItem` records."""

    @abstractmethod
    async def create(self, item: OutreachQueueItem) -> OutreachQueueItem:
        """Persist a new queue item and return it with generated fields."""

    @abstractmethod
    async def get_by_id(self, item_id: UUID) -> OutreachQueueItem | None:
        """Return a single queue item, or None if it does not exist."""

    @abstractmethod
    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        campaign_id: UUID | None = None,
        queue_status: str | None = None,
    ) -> list[OutreachQueueItem]:
        """Return queue items, newest first, optionally filtered."""

    @abstractmethod
    async def update(self, item: OutreachQueueItem) -> OutreachQueueItem | None:
        """Persist changes to an existing queue item, or None if it does not
        exist."""

    @abstractmethod
    async def list_by_campaign(
        self, campaign_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[OutreachQueueItem]:
        """Return every queue item for a single campaign, newest first."""

    @abstractmethod
    async def list_by_status(
        self, queue_status: str, limit: int = 100, offset: int = 0
    ) -> list[OutreachQueueItem]:
        """Return every queue item currently in a single status, newest first."""

    @abstractmethod
    async def list_ready_for_workflow(
        self, campaign_id: UUID, limit: int = 100
    ) -> list[OutreachQueueItem]:
        """Return items in this campaign eligible for workflow preparation
        (``queued`` or ``ready_for_workflow``), newest first."""

    @abstractmethod
    async def find_existing_item(
        self,
        campaign_id: UUID,
        *,
        lead_id: UUID | None,
        company_id: UUID | None,
        lead_candidate_id: UUID | None,
    ) -> OutreachQueueItem | None:
        """Return a previously queued item for this campaign matching the
        same lead/company/candidate, if any — used to update rather than
        duplicate an entry when a queue is rebuilt."""
