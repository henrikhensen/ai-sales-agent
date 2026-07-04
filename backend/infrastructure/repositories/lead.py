from uuid import UUID

from sqlalchemy import select

from backend.domain.entities.lead import Lead
from backend.domain.repositories.lead_repository import LeadRepository
from backend.infrastructure.database.models.lead import LeadModel
from backend.infrastructure.repositories.base import SQLAlchemyRepository


class SQLAlchemyLeadRepository(SQLAlchemyRepository[LeadModel, Lead], LeadRepository):
    """SQLAlchemy-backed :class:`LeadRepository`."""

    model = LeadModel

    def _to_entity(self, orm_obj: LeadModel) -> Lead:
        return Lead(
            id=orm_obj.id,
            company_id=orm_obj.company_id,
            source=orm_obj.source,
            status=orm_obj.status,
            score=orm_obj.score,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )

    def _to_orm(self, entity: Lead) -> LeadModel:
        return LeadModel(
            company_id=entity.company_id,
            source=entity.source,
            status=entity.status,
            score=entity.score,
        )

    def _apply(self, orm_obj: LeadModel, entity: Lead) -> None:
        orm_obj.source = entity.source
        orm_obj.status = entity.status
        orm_obj.score = entity.score

    async def list_by_company(
        self, company_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[Lead]:
        stmt = (
            select(LeadModel)
            .where(LeadModel.company_id == company_id)
            .order_by(LeadModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]
