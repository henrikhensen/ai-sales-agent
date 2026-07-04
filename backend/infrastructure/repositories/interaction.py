from uuid import UUID

from sqlalchemy import select

from backend.domain.entities.interaction import Interaction
from backend.domain.repositories.interaction_repository import InteractionRepository
from backend.infrastructure.database.models.interaction import InteractionModel
from backend.infrastructure.repositories.base import SQLAlchemyRepository


class SQLAlchemyInteractionRepository(
    SQLAlchemyRepository[InteractionModel, Interaction], InteractionRepository
):
    """SQLAlchemy-backed :class:`InteractionRepository`."""

    model = InteractionModel

    def _to_entity(self, orm_obj: InteractionModel) -> Interaction:
        return Interaction(
            id=orm_obj.id,
            lead_id=orm_obj.lead_id,
            type=orm_obj.type,
            notes=orm_obj.notes,
            occurred_at=orm_obj.occurred_at,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )

    def _to_orm(self, entity: Interaction) -> InteractionModel:
        data = {
            "lead_id": entity.lead_id,
            "type": entity.type,
            "notes": entity.notes,
        }
        if entity.occurred_at is not None:
            data["occurred_at"] = entity.occurred_at
        return InteractionModel(**data)

    def _apply(self, orm_obj: InteractionModel, entity: Interaction) -> None:
        orm_obj.type = entity.type
        orm_obj.notes = entity.notes
        if entity.occurred_at is not None:
            orm_obj.occurred_at = entity.occurred_at

    async def list_by_lead(
        self, lead_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[Interaction]:
        stmt = (
            select(InteractionModel)
            .where(InteractionModel.lead_id == lead_id)
            .order_by(InteractionModel.occurred_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]
