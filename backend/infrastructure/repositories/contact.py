from uuid import UUID

from sqlalchemy import func, select

from backend.domain.entities.contact import Contact
from backend.domain.repositories.contact_repository import ContactRepository
from backend.infrastructure.database.models.contact import ContactModel
from backend.infrastructure.repositories.base import SQLAlchemyRepository


class SQLAlchemyContactRepository(
    SQLAlchemyRepository[ContactModel, Contact], ContactRepository
):
    """SQLAlchemy-backed :class:`ContactRepository`."""

    model = ContactModel

    def _to_entity(self, orm_obj: ContactModel) -> Contact:
        return Contact(
            id=orm_obj.id,
            company_id=orm_obj.company_id,
            first_name=orm_obj.first_name,
            last_name=orm_obj.last_name,
            email=orm_obj.email,
            phone=orm_obj.phone,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )

    def _to_orm(self, entity: Contact) -> ContactModel:
        return ContactModel(
            company_id=entity.company_id,
            first_name=entity.first_name,
            last_name=entity.last_name,
            email=entity.email,
            phone=entity.phone,
        )

    def _apply(self, orm_obj: ContactModel, entity: Contact) -> None:
        orm_obj.first_name = entity.first_name
        orm_obj.last_name = entity.last_name
        orm_obj.email = entity.email
        orm_obj.phone = entity.phone

    async def find_by_company_and_name(
        self, company_id: UUID, first_name: str, last_name: str
    ) -> Contact | None:
        stmt = select(ContactModel).where(
            ContactModel.company_id == company_id,
            func.lower(ContactModel.first_name) == first_name.strip().lower(),
            func.lower(ContactModel.last_name) == last_name.strip().lower(),
        )
        result = await self._session.execute(stmt)
        orm_obj = result.scalars().first()
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def list_by_company(
        self, company_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[Contact]:
        stmt = (
            select(ContactModel)
            .where(ContactModel.company_id == company_id)
            .order_by(ContactModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]
