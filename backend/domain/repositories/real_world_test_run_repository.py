from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from backend.domain.entities.real_world_test_run import RealWorldTestRun


class RealWorldTestRunRepository(ABC):
    """Persistence port for :class:`RealWorldTestRun` records."""

    @abstractmethod
    async def create(self, run: RealWorldTestRun) -> RealWorldTestRun:
        """Persist a new test run and return it with generated fields populated."""

    @abstractmethod
    async def get_by_id(self, run_id: UUID) -> RealWorldTestRun | None:
        """Return a single test run, or None if it does not exist."""

    @abstractmethod
    async def update(self, run: RealWorldTestRun) -> RealWorldTestRun | None:
        """Persist changes to an existing test run, or None if it does not exist."""

    @abstractmethod
    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        status: str | None = None,
        created_by_user_id: UUID | None = None,
    ) -> list[RealWorldTestRun]:
        """Return test runs, newest first, optionally filtered."""
