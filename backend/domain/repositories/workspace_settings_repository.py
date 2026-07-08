from abc import ABC, abstractmethod

from backend.domain.entities.workspace_settings import WorkspaceSettings


class WorkspaceSettingsRepository(ABC):
    """Persistence port for the single :class:`WorkspaceSettings` record.

    Single-tenant in this phase: there is exactly one row, so this port
    exposes a get-or-create style accessor instead of id-keyed CRUD.
    """

    @abstractmethod
    async def get(self) -> WorkspaceSettings | None:
        """Return the workspace settings row, or None if never created."""

    @abstractmethod
    async def create(self, settings: WorkspaceSettings) -> WorkspaceSettings:
        """Persist the (first and only) workspace settings row."""

    @abstractmethod
    async def update(self, settings: WorkspaceSettings) -> WorkspaceSettings | None:
        """Persist changes to the existing workspace settings row, or None
        if it does not exist."""
