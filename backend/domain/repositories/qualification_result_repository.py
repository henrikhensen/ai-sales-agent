from abc import ABC, abstractmethod
from uuid import UUID

from backend.domain.entities.qualification_result import QualificationResult


class QualificationResultRepository(ABC):
    """Persistence port for :class:`QualificationResult` records."""

    @abstractmethod
    async def create(self, result: QualificationResult) -> QualificationResult:
        """Persist a new result and return it with generated fields."""

    @abstractmethod
    async def get_by_id(self, result_id: UUID) -> QualificationResult | None:
        """Return a single result, or None if it does not exist."""

    @abstractmethod
    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        qualification_run_id: UUID | None = None,
        qualification_status: str | None = None,
    ) -> list[QualificationResult]:
        """Return results, newest first, optionally filtered."""

    @abstractmethod
    async def update(self, result: QualificationResult) -> QualificationResult | None:
        """Persist changes to an existing result, or None if it does not
        exist."""

    @abstractmethod
    async def find_latest_for_candidate(
        self, lead_candidate_id: UUID
    ) -> QualificationResult | None:
        """Return the most recent result for this candidate, if any."""

    @abstractmethod
    async def find_latest_for_lead(self, lead_id: UUID) -> QualificationResult | None:
        """Return the most recent result for this CRM lead, if any."""
