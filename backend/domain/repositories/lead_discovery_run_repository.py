from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from backend.domain.entities.lead_discovery_run import LeadDiscoveryRun


class LeadDiscoveryRunRepository(ABC):
    """Persistence port for :class:`LeadDiscoveryRun` records."""

    @abstractmethod
    async def create(self, run: LeadDiscoveryRun) -> LeadDiscoveryRun:
        """Persist a new run and return it with generated fields populated."""

    @abstractmethod
    async def get_by_id(self, run_id: UUID) -> LeadDiscoveryRun | None:
        """Return a single run, or None if it does not exist."""

    @abstractmethod
    async def update(self, run: LeadDiscoveryRun) -> LeadDiscoveryRun | None:
        """Persist changes to an existing run, or None if it does not exist."""

    @abstractmethod
    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        status: str | None = None,
        created_by_user_id: UUID | None = None,
    ) -> list[LeadDiscoveryRun]:
        """Return runs, newest first, optionally filtered."""
