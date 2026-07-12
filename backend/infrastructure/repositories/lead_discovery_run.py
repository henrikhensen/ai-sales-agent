from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.entities.lead_discovery_run import LeadDiscoveryRun
from backend.domain.repositories.lead_discovery_run_repository import (
    LeadDiscoveryRunRepository,
)
from backend.infrastructure.database.models.lead_discovery_run import (
    LeadDiscoveryRunModel,
)


class SQLAlchemyLeadDiscoveryRunRepository(LeadDiscoveryRunRepository):
    """SQLAlchemy-backed :class:`LeadDiscoveryRunRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, run: LeadDiscoveryRun) -> LeadDiscoveryRun:
        orm_obj = LeadDiscoveryRunModel(
            name=run.name,
            target_customer=run.target_customer,
            region=run.region,
            offer_profile_id=run.offer_profile_id,
            icp_profile_id=run.icp_profile_id,
            requested_count=run.requested_count,
            min_score=run.min_score,
            mode=run.mode,
            status=run.status,
            lead_sourcing_campaign_id=run.lead_sourcing_campaign_id,
            lead_sourcing_run_id=run.lead_sourcing_run_id,
            outreach_campaign_id=run.outreach_campaign_id,
            found_candidates=run.found_candidates,
            analyzed_websites=run.analyzed_websites,
            qualified_leads=run.qualified_leads,
            rejected_leads=run.rejected_leads,
            needs_review_leads=run.needs_review_leads,
            created_drafts=run.created_drafts,
            warnings=run.warnings,
            errors=run.errors,
            created_by_user_id=run.created_by_user_id,
            started_at=run.started_at,
            completed_at=run.completed_at,
        )
        self._session.add(orm_obj)
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def get_by_id(self, run_id: UUID) -> LeadDiscoveryRun | None:
        orm_obj = await self._session.get(LeadDiscoveryRunModel, run_id)
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def update(self, run: LeadDiscoveryRun) -> LeadDiscoveryRun | None:
        orm_obj = await self._session.get(LeadDiscoveryRunModel, run.id)
        if orm_obj is None:
            return None
        orm_obj.name = run.name
        orm_obj.target_customer = run.target_customer
        orm_obj.region = run.region
        orm_obj.offer_profile_id = run.offer_profile_id
        orm_obj.icp_profile_id = run.icp_profile_id
        orm_obj.requested_count = run.requested_count
        orm_obj.min_score = run.min_score
        orm_obj.mode = run.mode
        orm_obj.status = run.status
        orm_obj.lead_sourcing_campaign_id = run.lead_sourcing_campaign_id
        orm_obj.lead_sourcing_run_id = run.lead_sourcing_run_id
        orm_obj.outreach_campaign_id = run.outreach_campaign_id
        orm_obj.found_candidates = run.found_candidates
        orm_obj.analyzed_websites = run.analyzed_websites
        orm_obj.qualified_leads = run.qualified_leads
        orm_obj.rejected_leads = run.rejected_leads
        orm_obj.needs_review_leads = run.needs_review_leads
        orm_obj.created_drafts = run.created_drafts
        orm_obj.warnings = run.warnings
        orm_obj.errors = run.errors
        orm_obj.started_at = run.started_at
        orm_obj.completed_at = run.completed_at
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        status: str | None = None,
        created_by_user_id: UUID | None = None,
    ) -> list[LeadDiscoveryRun]:
        stmt = select(LeadDiscoveryRunModel)
        if status is not None:
            stmt = stmt.where(LeadDiscoveryRunModel.status == status)
        if created_by_user_id is not None:
            stmt = stmt.where(
                LeadDiscoveryRunModel.created_by_user_id == created_by_user_id
            )
        stmt = (
            stmt.order_by(LeadDiscoveryRunModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    @staticmethod
    def _to_entity(orm_obj: LeadDiscoveryRunModel) -> LeadDiscoveryRun:
        return LeadDiscoveryRun(
            id=orm_obj.id,
            name=orm_obj.name,
            target_customer=orm_obj.target_customer,
            region=orm_obj.region,
            offer_profile_id=orm_obj.offer_profile_id,
            icp_profile_id=orm_obj.icp_profile_id,
            requested_count=orm_obj.requested_count,
            min_score=orm_obj.min_score,
            mode=orm_obj.mode,
            status=orm_obj.status,
            lead_sourcing_campaign_id=orm_obj.lead_sourcing_campaign_id,
            lead_sourcing_run_id=orm_obj.lead_sourcing_run_id,
            outreach_campaign_id=orm_obj.outreach_campaign_id,
            found_candidates=orm_obj.found_candidates,
            analyzed_websites=orm_obj.analyzed_websites,
            qualified_leads=orm_obj.qualified_leads,
            rejected_leads=orm_obj.rejected_leads,
            needs_review_leads=orm_obj.needs_review_leads,
            created_drafts=orm_obj.created_drafts,
            warnings=orm_obj.warnings,
            errors=orm_obj.errors,
            created_by_user_id=orm_obj.created_by_user_id,
            started_at=orm_obj.started_at,
            completed_at=orm_obj.completed_at,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )
