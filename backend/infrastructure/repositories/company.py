from sqlalchemy import func, select

from backend.domain.entities.company import Company
from backend.domain.repositories.company_repository import CompanyRepository
from backend.infrastructure.database.models.company import CompanyModel
from backend.infrastructure.repositories.base import SQLAlchemyRepository


class SQLAlchemyCompanyRepository(
    SQLAlchemyRepository[CompanyModel, Company], CompanyRepository
):
    """SQLAlchemy-backed :class:`CompanyRepository`."""

    model = CompanyModel

    def _to_entity(self, orm_obj: CompanyModel) -> Company:
        return Company(
            id=orm_obj.id,
            name=orm_obj.name,
            domain=orm_obj.domain,
            industry=orm_obj.industry,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )

    def _to_orm(self, entity: Company) -> CompanyModel:
        return CompanyModel(
            name=entity.name,
            domain=entity.domain,
            industry=entity.industry,
        )

    def _apply(self, orm_obj: CompanyModel, entity: Company) -> None:
        orm_obj.name = entity.name
        orm_obj.domain = entity.domain
        orm_obj.industry = entity.industry

    async def find_by_name(self, name: str) -> Company | None:
        stmt = select(CompanyModel).where(func.lower(CompanyModel.name) == name.strip().lower())
        result = await self._session.execute(stmt)
        orm_obj = result.scalars().first()
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def find_by_domain(self, domain: str) -> Company | None:
        stmt = select(CompanyModel).where(
            func.lower(CompanyModel.domain) == domain.strip().lower()
        )
        result = await self._session.execute(stmt)
        orm_obj = result.scalars().first()
        return self._to_entity(orm_obj) if orm_obj is not None else None
