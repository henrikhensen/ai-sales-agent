from abc import ABC, abstractmethod
from uuid import UUID

from backend.domain.entities.lead_sourcing_campaign import LeadSourcingCampaign


class LeadSourcingCampaignRepository(ABC):
    """Persistence port for :class:`LeadSourcingCampaign` records."""

    @abstractmethod
    async def create(self, campaign: LeadSourcingCampaign) -> LeadSourcingCampaign:
        """Persist a new campaign and return it with generated fields."""

    @abstractmethod
    async def list(
        self, limit: int = 100, offset: int = 0, status: str | None = None
    ) -> list[LeadSourcingCampaign]:
        """Return campaigns, newest first, optionally filtered by status."""

    @abstractmethod
    async def get_by_id(self, campaign_id: UUID) -> LeadSourcingCampaign | None:
        """Return a single campaign, or None if it does not exist."""

    @abstractmethod
    async def update(
        self, campaign: LeadSourcingCampaign
    ) -> LeadSourcingCampaign | None:
        """Persist changes to an existing campaign, or None if it does not
        exist."""

    @abstractmethod
    async def archive(self, campaign_id: UUID) -> LeadSourcingCampaign | None:
        """Set status to 'archived', or None if the campaign does not exist."""
