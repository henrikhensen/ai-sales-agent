from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.entities.lead_sourcing_campaign import LeadSourcingCampaign
from backend.domain.repositories.lead_sourcing_campaign_repository import (
    LeadSourcingCampaignRepository,
)
from backend.infrastructure.database.models.lead_sourcing_campaign import (
    LeadSourcingCampaignModel,
)


class SQLAlchemyLeadSourcingCampaignRepository(LeadSourcingCampaignRepository):
    """SQLAlchemy-backed :class:`LeadSourcingCampaignRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, campaign: LeadSourcingCampaign) -> LeadSourcingCampaign:
        orm_obj = LeadSourcingCampaignModel(
            name=campaign.name,
            description=campaign.description,
            icp_profile_id=campaign.icp_profile_id,
            offer_profile_id=campaign.offer_profile_id,
            source_type=campaign.source_type,
            search_query=campaign.search_query,
            target_industry=campaign.target_industry,
            target_location=campaign.target_location,
            target_keywords=campaign.target_keywords,
            excluded_keywords=campaign.excluded_keywords,
            max_results=campaign.max_results,
            status=campaign.status,
            created_by_user_id=campaign.created_by_user_id,
        )
        self._session.add(orm_obj)
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def list(
        self, limit: int = 100, offset: int = 0, status: str | None = None
    ) -> list[LeadSourcingCampaign]:
        stmt = select(LeadSourcingCampaignModel)
        if status:
            stmt = stmt.where(LeadSourcingCampaignModel.status == status)
        stmt = (
            stmt.order_by(LeadSourcingCampaignModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def get_by_id(self, campaign_id: UUID) -> LeadSourcingCampaign | None:
        orm_obj = await self._session.get(LeadSourcingCampaignModel, campaign_id)
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def update(
        self, campaign: LeadSourcingCampaign
    ) -> LeadSourcingCampaign | None:
        orm_obj = await self._session.get(LeadSourcingCampaignModel, campaign.id)
        if orm_obj is None:
            return None
        orm_obj.name = campaign.name
        orm_obj.description = campaign.description
        orm_obj.icp_profile_id = campaign.icp_profile_id
        orm_obj.offer_profile_id = campaign.offer_profile_id
        orm_obj.search_query = campaign.search_query
        orm_obj.target_industry = campaign.target_industry
        orm_obj.target_location = campaign.target_location
        orm_obj.target_keywords = campaign.target_keywords
        orm_obj.excluded_keywords = campaign.excluded_keywords
        orm_obj.max_results = campaign.max_results
        orm_obj.status = campaign.status
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def archive(self, campaign_id: UUID) -> LeadSourcingCampaign | None:
        orm_obj = await self._session.get(LeadSourcingCampaignModel, campaign_id)
        if orm_obj is None:
            return None
        orm_obj.status = "archived"
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    @staticmethod
    def _to_entity(orm_obj: LeadSourcingCampaignModel) -> LeadSourcingCampaign:
        return LeadSourcingCampaign(
            id=orm_obj.id,
            name=orm_obj.name,
            description=orm_obj.description,
            icp_profile_id=orm_obj.icp_profile_id,
            offer_profile_id=orm_obj.offer_profile_id,
            source_type=orm_obj.source_type,
            search_query=orm_obj.search_query,
            target_industry=orm_obj.target_industry,
            target_location=orm_obj.target_location,
            target_keywords=orm_obj.target_keywords,
            excluded_keywords=orm_obj.excluded_keywords,
            max_results=orm_obj.max_results,
            status=orm_obj.status,
            created_by_user_id=orm_obj.created_by_user_id,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )
