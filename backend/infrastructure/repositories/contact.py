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
