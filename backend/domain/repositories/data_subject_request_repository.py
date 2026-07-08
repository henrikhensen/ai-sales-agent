from abc import ABC, abstractmethod
from uuid import UUID

from backend.domain.entities.data_subject_request import DataSubjectRequest


class DataSubjectRequestRepository(ABC):
    """Persistence port for :class:`DataSubjectRequest` records."""

    @abstractmethod
    async def create(self, request: DataSubjectRequest) -> DataSubjectRequest:
        """Persist a new request and return it with generated fields populated."""

    @abstractmethod
    async def get_by_id(self, request_id: UUID) -> DataSubjectRequest | None:
        """Return a single request, or None if it does not exist."""

    @abstractmethod
    async def update(
        self, request: DataSubjectRequest
    ) -> DataSubjectRequest | None:
        """Persist changes to an existing request, or None if it does not exist."""

    @abstractmethod
    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        status: str | None = None,
        request_type: str | None = None,
    ) -> list[DataSubjectRequest]:
        """Return requests, newest first, optionally filtered."""
