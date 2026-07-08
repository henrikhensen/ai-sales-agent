from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.entities.onboarding_status import OnboardingStatus
from backend.domain.repositories.onboarding_status_repository import (
    OnboardingStatusRepository,
)
from backend.infrastructure.database.models.onboarding_status import (
    OnboardingStatusModel,
)


class SQLAlchemyOnboardingStatusRepository(OnboardingStatusRepository):
    """SQLAlchemy-backed :class:`OnboardingStatusRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, status: OnboardingStatus) -> OnboardingStatus:
        orm_obj = OnboardingStatusModel(
            user_id=status.user_id,
            current_step=status.current_step,
            completed_steps=status.completed_steps,
            skipped_steps=status.skipped_steps,
            is_completed=status.is_completed,
            completed_at=status.completed_at,
        )
        self._session.add(orm_obj)
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def get_by_user_id(self, user_id: UUID) -> OnboardingStatus | None:
        stmt = select(OnboardingStatusModel).where(
            OnboardingStatusModel.user_id == user_id
        )
        result = await self._session.execute(stmt)
        orm_obj = result.scalars().first()
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def update(self, status: OnboardingStatus) -> OnboardingStatus | None:
        orm_obj = await self._session.get(OnboardingStatusModel, status.id)
        if orm_obj is None:
            return None
        orm_obj.current_step = status.current_step
        orm_obj.completed_steps = status.completed_steps
        orm_obj.skipped_steps = status.skipped_steps
        orm_obj.is_completed = status.is_completed
        orm_obj.completed_at = status.completed_at
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def list_all(
        self, limit: int = 100, offset: int = 0
    ) -> list[OnboardingStatus]:
        stmt = (
            select(OnboardingStatusModel)
            .order_by(OnboardingStatusModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    @staticmethod
    def _to_entity(orm_obj: OnboardingStatusModel) -> OnboardingStatus:
        return OnboardingStatus(
            id=orm_obj.id,
            user_id=orm_obj.user_id,
            current_step=orm_obj.current_step,
            completed_steps=orm_obj.completed_steps,
            skipped_steps=orm_obj.skipped_steps,
            is_completed=orm_obj.is_completed,
            completed_at=orm_obj.completed_at,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )
