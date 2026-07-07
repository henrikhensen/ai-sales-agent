from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.entities.lead_sourcing_run import LeadSourcingRun
from backend.domain.repositories.lead_sourcing_run_repository import (
    LeadSourcingRunRepository,
)
from backend.infrastructure.database.models.lead_sourcing_run import (
    LeadSourcingRunModel,
)


class SQLAlchemyLeadSourcingRunRepository(LeadSourcingRunRepository):
    """SQLAlchemy-backed :class:`LeadSourcingRunRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, run: LeadSourcingRun) -> LeadSourcingRun:
        orm_obj = LeadSourcingRunModel(
            campaign_id=run.campaign_id,
            status=run.status,
            provider=run.provider,
            started_by_user_id=run.started_by_user_id,
            started_at=run.started_at,
            completed_at=run.completed_at,
            total_candidates_found=run.total_candidates_found,
            total_candidates_saved=run.total_candidates_saved,
            total_duplicates=run.total_duplicates,
            total_blocked_by_do_not_contact=run.total_blocked_by_do_not_contact,
            total_errors=run.total_errors,
            warnings=run.warnings,
        )
        self._session.add(orm_obj)
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def get_by_id(self, run_id: UUID) -> LeadSourcingRun | None:
        orm_obj = await self._session.get(LeadSourcingRunModel, run_id)
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def list(
        self, limit: int = 100, offset: int = 0, campaign_id: UUID | None = None
    ) -> list[LeadSourcingRun]:
        stmt = select(LeadSourcingRunModel)
        if campaign_id is not None:
            stmt = stmt.where(LeadSourcingRunModel.campaign_id == campaign_id)
        stmt = (
            stmt.order_by(LeadSourcingRunModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def update(self, run: LeadSourcingRun) -> LeadSourcingRun | None:
        orm_obj = await self._session.get(LeadSourcingRunModel, run.id)
        if orm_obj is None:
            return None
        orm_obj.status = run.status
        orm_obj.completed_at = run.completed_at
        orm_obj.total_candidates_found = run.total_candidates_found
        orm_obj.total_candidates_saved = run.total_candidates_saved
        orm_obj.total_duplicates = run.total_duplicates
        orm_obj.total_blocked_by_do_not_contact = run.total_blocked_by_do_not_contact
        orm_obj.total_errors = run.total_errors
        orm_obj.warnings = run.warnings
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    @staticmethod
    def _to_entity(orm_obj: LeadSourcingRunModel) -> LeadSourcingRun:
        return LeadSourcingRun(
            id=orm_obj.id,
            campaign_id=orm_obj.campaign_id,
            status=orm_obj.status,
            provider=orm_obj.provider,
            started_by_user_id=orm_obj.started_by_user_id,
            started_at=orm_obj.started_at,
            completed_at=orm_obj.completed_at,
            total_candidates_found=orm_obj.total_candidates_found,
            total_candidates_saved=orm_obj.total_candidates_saved,
            total_duplicates=orm_obj.total_duplicates,
            total_blocked_by_do_not_contact=orm_obj.total_blocked_by_do_not_contact,
            total_errors=orm_obj.total_errors,
            warnings=orm_obj.warnings,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )
