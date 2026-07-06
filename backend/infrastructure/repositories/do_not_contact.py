from uuid import UUID

from sqlalchemy import select

from backend.domain.entities.do_not_contact_entry import DoNotContactEntry
from backend.domain.repositories.do_not_contact_repository import (
    DoNotContactRepository,
)
from backend.infrastructure.database.models.do_not_contact_entry import (
    DoNotContactEntryModel,
)
from backend.infrastructure.repositories.base import SQLAlchemyRepository


class SQLAlchemyDoNotContactRepository(
    SQLAlchemyRepository[DoNotContactEntryModel, DoNotContactEntry],
    DoNotContactRepository,
):
    """SQLAlchemy-backed :class:`DoNotContactRepository`."""

    model = DoNotContactEntryModel

    def _to_entity(self, orm_obj: DoNotContactEntryModel) -> DoNotContactEntry:
        return DoNotContactEntry(
            id=orm_obj.id,
            email=orm_obj.email,
            domain=orm_obj.domain,
            company_name=orm_obj.company_name,
            company_name_normalized=orm_obj.company_name_normalized,
            reason=orm_obj.reason,
            source=orm_obj.source,
            is_active=orm_obj.is_active,
            created_by_user_id=orm_obj.created_by_user_id,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )

    def _to_orm(self, entity: DoNotContactEntry) -> DoNotContactEntryModel:
        return DoNotContactEntryModel(
            email=entity.email,
            domain=entity.domain,
            company_name=entity.company_name,
            company_name_normalized=entity.company_name_normalized,
            reason=entity.reason,
            source=entity.source,
            is_active=entity.is_active,
            created_by_user_id=entity.created_by_user_id,
        )

    def _apply(self, orm_obj: DoNotContactEntryModel, entity: DoNotContactEntry) -> None:
        orm_obj.email = entity.email
        orm_obj.domain = entity.domain
        orm_obj.company_name = entity.company_name
        orm_obj.company_name_normalized = entity.company_name_normalized
        orm_obj.reason = entity.reason
        orm_obj.source = entity.source
        orm_obj.is_active = entity.is_active

    async def deactivate(self, entry_id: UUID) -> DoNotContactEntry | None:
        orm_obj = await self._session.get(self.model, entry_id)
        if orm_obj is None:
            return None
        orm_obj.is_active = False
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def find_active_by_email(self, email: str) -> DoNotContactEntry | None:
        stmt = select(DoNotContactEntryModel).where(
            DoNotContactEntryModel.email == email,
            DoNotContactEntryModel.is_active.is_(True),
        )
        result = await self._session.execute(stmt)
        orm_obj = result.scalars().first()
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def find_active_by_domain(self, domain: str) -> DoNotContactEntry | None:
        stmt = select(DoNotContactEntryModel).where(
            DoNotContactEntryModel.domain == domain,
            DoNotContactEntryModel.is_active.is_(True),
        )
        result = await self._session.execute(stmt)
        orm_obj = result.scalars().first()
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def find_active_by_company_name(
        self, company_name_normalized: str
    ) -> DoNotContactEntry | None:
        stmt = select(DoNotContactEntryModel).where(
            DoNotContactEntryModel.company_name_normalized == company_name_normalized,
            DoNotContactEntryModel.is_active.is_(True),
        )
        result = await self._session.execute(stmt)
        orm_obj = result.scalars().first()
        return self._to_entity(orm_obj) if orm_obj is not None else None
