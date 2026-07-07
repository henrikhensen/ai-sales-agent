from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.entities.icp_profile import ICPProfile
from backend.domain.repositories.icp_profile_repository import ICPProfileRepository
from backend.infrastructure.database.models.icp_profile import ICPProfileModel


class SQLAlchemyICPProfileRepository(ICPProfileRepository):
    """SQLAlchemy-backed :class:`ICPProfileRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, profile: ICPProfile) -> ICPProfile:
        orm_obj = ICPProfileModel(
            name=profile.name,
            description=profile.description,
            target_industries=profile.target_industries,
            excluded_industries=profile.excluded_industries,
            target_company_sizes=profile.target_company_sizes,
            target_locations=profile.target_locations,
            target_languages=profile.target_languages,
            target_keywords=profile.target_keywords,
            negative_keywords=profile.negative_keywords,
            target_pain_points=profile.target_pain_points,
            buying_triggers=profile.buying_triggers,
            required_signals=profile.required_signals,
            excluded_signals=profile.excluded_signals,
            buyer_personas=profile.buyer_personas,
            preferred_titles=profile.preferred_titles,
            excluded_titles=profile.excluded_titles,
            minimum_fit_score=profile.minimum_fit_score,
            scoring_weights=profile.scoring_weights,
            is_active=profile.is_active,
            created_by_user_id=profile.created_by_user_id,
        )
        self._session.add(orm_obj)
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def list(
        self, limit: int = 100, offset: int = 0, active_only: bool = False
    ) -> list[ICPProfile]:
        stmt = select(ICPProfileModel)
        if active_only:
            stmt = stmt.where(ICPProfileModel.is_active.is_(True))
        stmt = stmt.order_by(ICPProfileModel.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def get_by_id(self, profile_id: UUID) -> ICPProfile | None:
        orm_obj = await self._session.get(ICPProfileModel, profile_id)
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def update(self, profile: ICPProfile) -> ICPProfile | None:
        orm_obj = await self._session.get(ICPProfileModel, profile.id)
        if orm_obj is None:
            return None
        orm_obj.name = profile.name
        orm_obj.description = profile.description
        orm_obj.target_industries = profile.target_industries
        orm_obj.excluded_industries = profile.excluded_industries
        orm_obj.target_company_sizes = profile.target_company_sizes
        orm_obj.target_locations = profile.target_locations
        orm_obj.target_languages = profile.target_languages
        orm_obj.target_keywords = profile.target_keywords
        orm_obj.negative_keywords = profile.negative_keywords
        orm_obj.target_pain_points = profile.target_pain_points
        orm_obj.buying_triggers = profile.buying_triggers
        orm_obj.required_signals = profile.required_signals
        orm_obj.excluded_signals = profile.excluded_signals
        orm_obj.buyer_personas = profile.buyer_personas
        orm_obj.preferred_titles = profile.preferred_titles
        orm_obj.excluded_titles = profile.excluded_titles
        orm_obj.minimum_fit_score = profile.minimum_fit_score
        orm_obj.scoring_weights = profile.scoring_weights
        orm_obj.is_active = profile.is_active
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def deactivate(self, profile_id: UUID) -> ICPProfile | None:
        orm_obj = await self._session.get(ICPProfileModel, profile_id)
        if orm_obj is None:
            return None
        orm_obj.is_active = False
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def get_active(self, profile_id: UUID) -> ICPProfile | None:
        orm_obj = await self._session.get(ICPProfileModel, profile_id)
        if orm_obj is None or not orm_obj.is_active:
            return None
        return self._to_entity(orm_obj)

    @staticmethod
    def _to_entity(orm_obj: ICPProfileModel) -> ICPProfile:
        return ICPProfile(
            id=orm_obj.id,
            name=orm_obj.name,
            description=orm_obj.description,
            target_industries=orm_obj.target_industries,
            excluded_industries=orm_obj.excluded_industries,
            target_company_sizes=orm_obj.target_company_sizes,
            target_locations=orm_obj.target_locations,
            target_languages=orm_obj.target_languages,
            target_keywords=orm_obj.target_keywords,
            negative_keywords=orm_obj.negative_keywords,
            target_pain_points=orm_obj.target_pain_points,
            buying_triggers=orm_obj.buying_triggers,
            required_signals=orm_obj.required_signals,
            excluded_signals=orm_obj.excluded_signals,
            buyer_personas=orm_obj.buyer_personas,
            preferred_titles=orm_obj.preferred_titles,
            excluded_titles=orm_obj.excluded_titles,
            minimum_fit_score=orm_obj.minimum_fit_score,
            scoring_weights=orm_obj.scoring_weights,
            is_active=orm_obj.is_active,
            created_by_user_id=orm_obj.created_by_user_id,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )
