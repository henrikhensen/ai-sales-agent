from abc import ABC, abstractmethod
from uuid import UUID

from backend.domain.entities.workflow_run import WorkflowRun
from backend.domain.enums import WorkflowReviewStatus


class WorkflowRunRepository(ABC):
    """Persistence port for :class:`WorkflowRun` records.

    Deliberately narrower than :class:`AbstractRepository`: workflow runs are
    never fully replaced or deleted through the API, only created, read, and
    transitioned through their review lifecycle.
    """

    @abstractmethod
    async def create(self, run: WorkflowRun) -> WorkflowRun:
        """Persist a new workflow run and return it with generated fields populated."""

    @abstractmethod
    async def get_by_id(self, run_id: UUID) -> WorkflowRun | None:
        """Return the workflow run with the given id, or None if it does not exist."""

    @abstractmethod
    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        company_name: str | None = None,
        review_status: WorkflowReviewStatus | None = None,
    ) -> list[WorkflowRun]:
        """Return a page of workflow runs, newest first, optionally filtered."""

    @abstractmethod
    async def update_review_status(
        self, run_id: UUID, review_status: WorkflowReviewStatus
    ) -> WorkflowRun | None:
        """Transition a run's review status. Returns None if it does not exist."""
