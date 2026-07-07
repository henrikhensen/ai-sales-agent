from abc import ABC, abstractmethod
from uuid import UUID

from backend.domain.entities.lead_sourcing_run import LeadSourcingRun


class LeadSourcingRunRepository(ABC):
    """Persistence port for :class:`LeadSourcingRun` records."""

    @abstractmethod
    async def create(self, run: LeadSourcingRun) -> LeadSourcingRun:
        """Persist a new run and return it with generated fields."""

    @abstractmethod
    async def get_by_id(self, run_id: UUID) -> LeadSourcingRun | None:
        """Return a single run, or None if it does not exist."""

    @abstractmethod
    async def list(
        self, limit: int = 100, offset: int = 0, campaign_id: UUID | None = None
    ) -> list[LeadSourcingRun]:
        """Return runs, newest first, optionally filtered by campaign."""

    @abstractmethod
    async def update(self, run: LeadSourcingRun) -> LeadSourcingRun | None:
        """Persist changes to an existing run, or None if it does not exist."""
