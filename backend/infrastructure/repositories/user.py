from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.entities.user import User
from backend.domain.repositories.user_repository import UserRepository
from backend.infrastructure.database.models.user import UserModel


class SQLAlchemyUserRepository(UserRepository):
    """SQLAlchemy-backed :class:`UserRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user: User) -> User:
        orm_obj = UserModel(
            email=user.email,
            full_name=user.full_name,
            hashed_password=user.hashed_password,
            role=user.role,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
        )
        self._session.add(orm_obj)
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def get_by_id(self, user_id: UUID) -> User | None:
        orm_obj = await self._session.get(UserModel, user_id)
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(UserModel).where(UserModel.email == email)
        result = await self._session.execute(stmt)
        orm_obj = result.scalars().first()
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def list(self, limit: int = 100, offset: int = 0) -> list[User]:
        stmt = (
            select(UserModel)
            .order_by(UserModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def update(self, user: User) -> User | None:
        orm_obj = await self._session.get(UserModel, user.id)
        if orm_obj is None:
            return None
        orm_obj.full_name = user.full_name
        orm_obj.hashed_password = user.hashed_password
        orm_obj.role = user.role
        orm_obj.is_active = user.is_active
        orm_obj.is_superuser = user.is_superuser
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def deactivate(self, user_id: UUID) -> User | None:
        orm_obj = await self._session.get(UserModel, user_id)
        if orm_obj is None:
            return None
        orm_obj.is_active = False
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    @staticmethod
    def _to_entity(orm_obj: UserModel) -> User:
        return User(
            id=orm_obj.id,
            email=orm_obj.email,
            full_name=orm_obj.full_name,
            hashed_password=orm_obj.hashed_password,
            role=orm_obj.role,
            is_active=orm_obj.is_active,
            is_superuser=orm_obj.is_superuser,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )
