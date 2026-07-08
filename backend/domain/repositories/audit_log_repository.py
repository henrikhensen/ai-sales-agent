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
    async def create_independent(self, entry: AuditLog) -> AuditLog:
        """Persist a new audit log entry durably, independent of whatever
        ambient request transaction the caller may be part of.

        For implementations backed by a shared per-request session (see
        ``SQLAlchemyAuditLogRepository``), this must commit on its own
        schedule so the entry survives even if the caller's own request
        goes on to raise and roll back everything else. In-memory test
        doubles have no notion of a surrounding transaction, so they may
        implement this identically to :meth:`create`.
        """

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
