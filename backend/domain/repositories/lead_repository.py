from abc import abstractmethod
from uuid import UUID

from backend.domain.entities.lead import Lead
from backend.domain.enums import PipelineStatus
from backend.domain.repositories.base import AbstractRepository


class LeadRepository(AbstractRepository[Lead]):
    """Persistence port for :class:`Lead` entities."""

    @abstractmethod
    async def list_by_company(
        self, company_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[Lead]:
        """Return leads belonging to a single company, newest first."""

    @abstractmethod
    async def list_by_pipeline_status(
        self, pipeline_status: PipelineStatus, limit: int = 100, offset: int = 0
    ) -> list[Lead]:
        """Return leads currently in a single pipeline stage, newest first."""

    @abstractmethod
    async def update_pipeline_status(
        self, lead_id: UUID, pipeline_status: PipelineStatus
    ) -> Lead | None:
        """Transition a lead's pipeline stage and stamp ``pipeline_updated_at``.

        Returns None if the lead does not exist. Never sends an email or
        makes contact — this only ever updates bookkeeping fields.
        """

    @abstractmethod
    async def list_pipeline_board(self) -> list[Lead]:
        """Return every lead needed to build the pipeline board.

        No grouping happens here — that is the application service's job,
        not the repository's; this just returns the raw rows.
        """
