from abc import ABC, abstractmethod
from uuid import UUID

from backend.domain.entities.qualification_run import QualificationRun


class QualificationRunRepository(ABC):
    """Persistence port for :class:`QualificationRun` records."""

    @abstractmethod
    async def create(self, run: QualificationRun) -> QualificationRun:
        """Persist a new run and return it with generated fields."""

    @abstractmethod
    async def get_by_id(self, run_id: UUID) -> QualificationRun | None:
        """Return a single run, or None if it does not exist."""

    @abstractmethod
    async def list(self, limit: int = 100, offset: int = 0) -> list[QualificationRun]:
        """Return runs, newest first."""

    @abstractmethod
    async def update(self, run: QualificationRun) -> QualificationRun | None:
        """Persist changes to an existing run, or None if it does not exist."""
