from abc import ABC, abstractmethod
from uuid import UUID

from backend.domain.entities.data_retention_policy import DataRetentionPolicy


class DataRetentionPolicyRepository(ABC):
    """Persistence port for :class:`DataRetentionPolicy` records."""

    @abstractmethod
    async def create(self, policy: DataRetentionPolicy) -> DataRetentionPolicy:
        """Persist a new policy and return it with generated fields populated."""

    @abstractmethod
    async def get_by_id(self, policy_id: UUID) -> DataRetentionPolicy | None:
        """Return a single policy, or None if it does not exist."""

    @abstractmethod
    async def update(
        self, policy: DataRetentionPolicy
    ) -> DataRetentionPolicy | None:
        """Persist changes to an existing policy, or None if it does not exist."""

    @abstractmethod
    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        active_only: bool = False,
        entity_type: str | None = None,
    ) -> list[DataRetentionPolicy]:
        """Return policies, newest first, optionally filtered."""
