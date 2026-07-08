from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.entities.outreach_queue_item import OutreachQueueItem
from backend.domain.repositories.outreach_queue_item_repository import (
    OutreachQueueItemRepository,
)
from backend.infrastructure.database.models.outreach_queue_item import (
    OutreachQueueItemModel,
)


class SQLAlchemyOutreachQueueItemRepository(OutreachQueueItemRepository):
    """SQLAlchemy-backed :class:`OutreachQueueItemRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, item: OutreachQueueItem) -> OutreachQueueItem:
        orm_obj = OutreachQueueItemModel(
            campaign_id=item.campaign_id,
            lead_id=item.lead_id,
            company_id=item.company_id,
            lead_candidate_id=item.lead_candidate_id,
            qualification_result_id=item.qualification_result_id,
            icp_profile_id=item.icp_profile_id,
            offer_profile_id=item.offer_profile_id,
            priority_rank=item.priority_rank,
            qualification_score=item.qualification_score,
            qualification_level=item.qualification_level,
            queue_status=item.queue_status,
            recommended_outreach_angle=item.recommended_outreach_angle,
            personalization_notes=item.personalization_notes,
            compliance_status=item.compliance_status,
            do_not_contact_status=item.do_not_contact_status,
            duplicate_status=item.duplicate_status,
            workflow_run_id=item.workflow_run_id,
            email_draft_id=item.email_draft_id,
            review_id=item.review_id,
            external_draft_id=item.external_draft_id,
            last_action=item.last_action,
            last_error=item.last_error,
            created_by_user_id=item.created_by_user_id,
            assigned_to_user_id=item.assigned_to_user_id,
        )
        self._session.add(orm_obj)
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def get_by_id(self, item_id: UUID) -> OutreachQueueItem | None:
        orm_obj = await self._session.get(OutreachQueueItemModel, item_id)
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        campaign_id: UUID | None = None,
        queue_status: str | None = None,
    ) -> list[OutreachQueueItem]:
        stmt = select(OutreachQueueItemModel)
        if campaign_id is not None:
            stmt = stmt.where(OutreachQueueItemModel.campaign_id == campaign_id)
        if queue_status is not None:
            stmt = stmt.where(OutreachQueueItemModel.queue_status == queue_status)
        stmt = (
            stmt.order_by(OutreachQueueItemModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def update(self, item: OutreachQueueItem) -> OutreachQueueItem | None:
        orm_obj = await self._session.get(OutreachQueueItemModel, item.id)
        if orm_obj is None:
            return None
        orm_obj.priority_rank = item.priority_rank
        orm_obj.qualification_score = item.qualification_score
        orm_obj.qualification_level = item.qualification_level
        orm_obj.queue_status = item.queue_status
        orm_obj.recommended_outreach_angle = item.recommended_outreach_angle
        orm_obj.personalization_notes = item.personalization_notes
        orm_obj.compliance_status = item.compliance_status
        orm_obj.do_not_contact_status = item.do_not_contact_status
        orm_obj.duplicate_status = item.duplicate_status
        orm_obj.workflow_run_id = item.workflow_run_id
        orm_obj.email_draft_id = item.email_draft_id
        orm_obj.review_id = item.review_id
        orm_obj.external_draft_id = item.external_draft_id
        orm_obj.last_action = item.last_action
        orm_obj.last_error = item.last_error
        orm_obj.assigned_to_user_id = item.assigned_to_user_id
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def list_by_campaign(
        self, campaign_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[OutreachQueueItem]:
        return await self.list(limit=limit, offset=offset, campaign_id=campaign_id)

    async def list_by_status(
        self, queue_status: str, limit: int = 100, offset: int = 0
    ) -> list[OutreachQueueItem]:
        return await self.list(limit=limit, offset=offset, queue_status=queue_status)

    async def list_ready_for_workflow(
        self, campaign_id: UUID, limit: int = 100
    ) -> list[OutreachQueueItem]:
        stmt = (
            select(OutreachQueueItemModel)
            .where(OutreachQueueItemModel.campaign_id == campaign_id)
            .where(
                OutreachQueueItemModel.queue_status.in_(
                    ["queued", "ready_for_workflow"]
                )
            )
            .order_by(
                OutreachQueueItemModel.priority_rank.asc().nulls_last(),
                OutreachQueueItemModel.created_at.asc(),
            )
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def find_existing_item(
        self,
        campaign_id: UUID,
        *,
        lead_id: UUID | None,
        company_id: UUID | None,
        lead_candidate_id: UUID | None,
    ) -> OutreachQueueItem | None:
        stmt = select(OutreachQueueItemModel).where(
            OutreachQueueItemModel.campaign_id == campaign_id
        )
        if lead_candidate_id is not None:
            stmt = stmt.where(
                OutreachQueueItemModel.lead_candidate_id == lead_candidate_id
            )
        elif lead_id is not None:
            stmt = stmt.where(OutreachQueueItemModel.lead_id == lead_id)
        elif company_id is not None:
            stmt = stmt.where(OutreachQueueItemModel.company_id == company_id)
        else:
            return None
        stmt = stmt.order_by(OutreachQueueItemModel.created_at.desc()).limit(1)
        result = await self._session.execute(stmt)
        orm_obj = result.scalars().first()
        return self._to_entity(orm_obj) if orm_obj is not None else None

    @staticmethod
    def _to_entity(orm_obj: OutreachQueueItemModel) -> OutreachQueueItem:
        return OutreachQueueItem(
            id=orm_obj.id,
            campaign_id=orm_obj.campaign_id,
            lead_id=orm_obj.lead_id,
            company_id=orm_obj.company_id,
            lead_candidate_id=orm_obj.lead_candidate_id,
            qualification_result_id=orm_obj.qualification_result_id,
            icp_profile_id=orm_obj.icp_profile_id,
            offer_profile_id=orm_obj.offer_profile_id,
            priority_rank=orm_obj.priority_rank,
            qualification_score=orm_obj.qualification_score,
            qualification_level=orm_obj.qualification_level,
            queue_status=orm_obj.queue_status,
            recommended_outreach_angle=orm_obj.recommended_outreach_angle,
            personalization_notes=orm_obj.personalization_notes,
            compliance_status=orm_obj.compliance_status,
            do_not_contact_status=orm_obj.do_not_contact_status,
            duplicate_status=orm_obj.duplicate_status,
            workflow_run_id=orm_obj.workflow_run_id,
            email_draft_id=orm_obj.email_draft_id,
            review_id=orm_obj.review_id,
            external_draft_id=orm_obj.external_draft_id,
            last_action=orm_obj.last_action,
            last_error=orm_obj.last_error,
            created_by_user_id=orm_obj.created_by_user_id,
            assigned_to_user_id=orm_obj.assigned_to_user_id,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )
