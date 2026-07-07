from abc import ABC, abstractmethod
from uuid import UUID

from backend.domain.entities.lead_candidate import LeadCandidate


class LeadCandidateRepository(ABC):
    """Persistence port for :class:`LeadCandidate` records."""

    @abstractmethod
    async def create(self, candidate: LeadCandidate) -> LeadCandidate:
        """Persist a new candidate and return it with generated fields."""

    @abstractmethod
    async def get_by_id(self, candidate_id: UUID) -> LeadCandidate | None:
        """Return a single candidate, or None if it does not exist."""

    @abstractmethod
    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        campaign_id: UUID | None = None,
        sourcing_run_id: UUID | None = None,
        review_status: str | None = None,
    ) -> list[LeadCandidate]:
        """Return candidates, newest first, optionally filtered."""

    @abstractmethod
    async def update(self, candidate: LeadCandidate) -> LeadCandidate | None:
        """Persist changes to an existing candidate, or None if it does not
        exist."""

    @abstractmethod
    async def find_existing(
        self, *, company_domain: str | None, company_name: str | None
    ) -> LeadCandidate | None:
        """Return a previously stored candidate matching this domain (first)
        or company name, if any — used for candidate-level duplicate
        detection across campaigns/runs."""
