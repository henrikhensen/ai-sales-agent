from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.entities.outreach_campaign import OutreachCampaign
from backend.domain.repositories.outreach_campaign_repository import (
    OutreachCampaignRepository,
)
from backend.infrastructure.database.models.outreach_campaign import (
    OutreachCampaignModel,
)


class SQLAlchemyOutreachCampaignRepository(OutreachCampaignRepository):
    """SQLAlchemy-backed :class:`OutreachCampaignRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, campaign: OutreachCampaign) -> OutreachCampaign:
        orm_obj = OutreachCampaignModel(
            name=campaign.name,
            description=campaign.description,
            icp_profile_id=campaign.icp_profile_id,
            offer_profile_id=campaign.offer_profile_id,
            target_language=campaign.target_language,
            tone=campaign.tone,
            min_qualification_score=campaign.min_qualification_score,
            allowed_qualification_levels=campaign.allowed_qualification_levels,
            excluded_statuses=campaign.excluded_statuses,
            max_queue_items=campaign.max_queue_items,
            status=campaign.status,
            created_by_user_id=campaign.created_by_user_id,
        )
        self._session.add(orm_obj)
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def get_by_id(self, campaign_id: UUID) -> OutreachCampaign | None:
        orm_obj = await self._session.get(OutreachCampaignModel, campaign_id)
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def list(
        self, limit: int = 100, offset: int = 0, status: str | None = None
    ) -> list[OutreachCampaign]:
        stmt = select(OutreachCampaignModel)
        if status:
            stmt = stmt.where(OutreachCampaignModel.status == status)
        stmt = (
            stmt.order_by(OutreachCampaignModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def update(self, campaign: OutreachCampaign) -> OutreachCampaign | None:
        orm_obj = await self._session.get(OutreachCampaignModel, campaign.id)
        if orm_obj is None:
            return None
        orm_obj.name = campaign.name
        orm_obj.description = campaign.description
        orm_obj.icp_profile_id = campaign.icp_profile_id
        orm_obj.offer_profile_id = campaign.offer_profile_id
        orm_obj.target_language = campaign.target_language
        orm_obj.tone = campaign.tone
        orm_obj.min_qualification_score = campaign.min_qualification_score
        orm_obj.allowed_qualification_levels = campaign.allowed_qualification_levels
        orm_obj.excluded_statuses = campaign.excluded_statuses
        orm_obj.max_queue_items = campaign.max_queue_items
        orm_obj.status = campaign.status
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def archive(self, campaign_id: UUID) -> OutreachCampaign | None:
        orm_obj = await self._session.get(OutreachCampaignModel, campaign_id)
        if orm_obj is None:
            return None
        orm_obj.status = "archived"
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def set_status(
        self, campaign_id: UUID, status: str
    ) -> OutreachCampaign | None:
        orm_obj = await self._session.get(OutreachCampaignModel, campaign_id)
        if orm_obj is None:
            return None
        orm_obj.status = status
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    @staticmethod
    def _to_entity(orm_obj: OutreachCampaignModel) -> OutreachCampaign:
        return OutreachCampaign(
            id=orm_obj.id,
            name=orm_obj.name,
            description=orm_obj.description,
            icp_profile_id=orm_obj.icp_profile_id,
            offer_profile_id=orm_obj.offer_profile_id,
            target_language=orm_obj.target_language,
            tone=orm_obj.tone,
            min_qualification_score=orm_obj.min_qualification_score,
            allowed_qualification_levels=orm_obj.allowed_qualification_levels,
            excluded_statuses=orm_obj.excluded_statuses,
            max_queue_items=orm_obj.max_queue_items,
            status=orm_obj.status,
            created_by_user_id=orm_obj.created_by_user_id,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )
