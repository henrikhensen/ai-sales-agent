from abc import ABC, abstractmethod
from uuid import UUID

from backend.domain.entities.data_retention_run import DataRetentionRun


class DataRetentionRunRepository(ABC):
    """Persistence port for :class:`DataRetentionRun` records."""

    @abstractmethod
    async def create(self, run: DataRetentionRun) -> DataRetentionRun:
        """Persist a new run and return it with generated fields populated."""

    @abstractmethod
    async def get_by_id(self, run_id: UUID) -> DataRetentionRun | None:
        """Return a single run, or None if it does not exist."""

    @abstractmethod
    async def update(self, run: DataRetentionRun) -> DataRetentionRun | None:
        """Persist changes to an existing run, or None if it does not exist."""

    @abstractmethod
    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        policy_id: UUID | None = None,
    ) -> list[DataRetentionRun]:
        """Return runs, newest first, optionally filtered by policy."""
