from abc import ABC, abstractmethod
from uuid import UUID

from backend.domain.entities.outreach_campaign import OutreachCampaign


class OutreachCampaignRepository(ABC):
    """Persistence port for :class:`OutreachCampaign` records."""

    @abstractmethod
    async def create(self, campaign: OutreachCampaign) -> OutreachCampaign:
        """Persist a new campaign and return it with generated fields."""

    @abstractmethod
    async def get_by_id(self, campaign_id: UUID) -> OutreachCampaign | None:
        """Return a single campaign, or None if it does not exist."""

    @abstractmethod
    async def list(
        self, limit: int = 100, offset: int = 0, status: str | None = None
    ) -> list[OutreachCampaign]:
        """Return campaigns, newest first, optionally filtered by status."""

    @abstractmethod
    async def update(self, campaign: OutreachCampaign) -> OutreachCampaign | None:
        """Persist changes to an existing campaign, or None if it does not
        exist."""

    @abstractmethod
    async def archive(self, campaign_id: UUID) -> OutreachCampaign | None:
        """Set status to 'archived', or None if the campaign does not exist."""

    @abstractmethod
    async def set_status(
        self, campaign_id: UUID, status: str
    ) -> OutreachCampaign | None:
        """Set the campaign's status, or None if it does not exist."""
