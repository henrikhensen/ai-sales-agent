from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from backend.domain.entities.audit_log import AuditLog


class AuditLogRepository(ABC):
    """Persistence port for :class:`AuditLog` records.

    Deliberately narrower than ``AbstractRepository``: audit logs are an
    append-only trail, never updated or deleted through the API.
    """

    @abstractmethod
    async def create(self, entry: AuditLog) -> AuditLog:
        """Persist a new audit log entry and return it with generated fields."""

    @abstractmethod
    async def get(self, entry_id: UUID) -> AuditLog | None:
        """Return a single audit log entry, or None if it does not exist."""

    @abstractmethod
    async def list_filtered(
        self,
        *,
        actor_user_id: UUID | None = None,
        action: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        result: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """Return audit log entries matching every given filter, newest first."""
