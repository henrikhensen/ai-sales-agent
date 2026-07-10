from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from backend.domain.entities.quality_score import QualityScore


class QualityScoreRepository(ABC):
    """Persistence port for :class:`QualityScore` records."""

    @abstractmethod
    async def create(self, score: QualityScore) -> QualityScore:
        """Persist a new score and return it with generated fields populated."""

    @abstractmethod
    async def get_by_id(self, score_id: UUID) -> QualityScore | None:
        """Return a single score, or None if it does not exist."""

    @abstractmethod
    async def update(self, score: QualityScore) -> QualityScore | None:
        """Persist changes to an existing score, or None if it does not exist."""

    @abstractmethod
    async def find_latest_for_entity(
        self, entity_type: str, entity_id: UUID
    ) -> QualityScore | None:
        """Return the most recent score for this entity, if any."""

    @abstractmethod
    async def list_for_entity(
        self, entity_type: str, entity_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[QualityScore]:
        """Return every score recorded for this entity, newest first."""

    @abstractmethod
    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        entity_type: str | None = None,
        score_level: str | None = None,
    ) -> list[QualityScore]:
        """Return scores, newest first, optionally filtered."""

    @abstractmethod
    async def list_all_latest(
        self, entity_type: str | None = None, limit: int = 1000
    ) -> list[QualityScore]:
        """Return the latest score per entity (for dashboard aggregation),
        optionally filtered by entity type."""
