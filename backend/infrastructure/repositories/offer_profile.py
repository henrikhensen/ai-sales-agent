from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.entities.offer_profile import OfferProfile
from backend.domain.repositories.offer_profile_repository import OfferProfileRepository
from backend.infrastructure.database.models.offer_profile import OfferProfileModel


class SQLAlchemyOfferProfileRepository(OfferProfileRepository):
    """SQLAlchemy-backed :class:`OfferProfileRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, profile: OfferProfile) -> OfferProfile:
        orm_obj = OfferProfileModel(
            name=profile.name,
            main_value_proposition=profile.main_value_proposition,
            description=profile.description,
            target_outcome=profile.target_outcome,
            pain_points_solved=profile.pain_points_solved,
            key_benefits=profile.key_benefits,
            differentiators=profile.differentiators,
            proof_points=profile.proof_points,
            case_study_notes=profile.case_study_notes,
            pricing_notes=profile.pricing_notes,
            call_to_action=profile.call_to_action,
            tone=profile.tone,
            language=profile.language,
            forbidden_claims=profile.forbidden_claims,
            required_disclaimers=profile.required_disclaimers,
            is_active=profile.is_active,
            created_by_user_id=profile.created_by_user_id,
        )
        self._session.add(orm_obj)
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def list(
        self, limit: int = 100, offset: int = 0, active_only: bool = False
    ) -> list[OfferProfile]:
        stmt = select(OfferProfileModel)
        if active_only:
            stmt = stmt.where(OfferProfileModel.is_active.is_(True))
        stmt = stmt.order_by(OfferProfileModel.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def get_by_id(self, profile_id: UUID) -> OfferProfile | None:
        orm_obj = await self._session.get(OfferProfileModel, profile_id)
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def update(self, profile: OfferProfile) -> OfferProfile | None:
        orm_obj = await self._session.get(OfferProfileModel, profile.id)
        if orm_obj is None:
            return None
        orm_obj.name = profile.name
        orm_obj.main_value_proposition = profile.main_value_proposition
        orm_obj.description = profile.description
        orm_obj.target_outcome = profile.target_outcome
        orm_obj.pain_points_solved = profile.pain_points_solved
        orm_obj.key_benefits = profile.key_benefits
        orm_obj.differentiators = profile.differentiators
        orm_obj.proof_points = profile.proof_points
        orm_obj.case_study_notes = profile.case_study_notes
        orm_obj.pricing_notes = profile.pricing_notes
        orm_obj.call_to_action = profile.call_to_action
        orm_obj.tone = profile.tone
        orm_obj.language = profile.language
        orm_obj.forbidden_claims = profile.forbidden_claims
        orm_obj.required_disclaimers = profile.required_disclaimers
        orm_obj.is_active = profile.is_active
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def deactivate(self, profile_id: UUID) -> OfferProfile | None:
        orm_obj = await self._session.get(OfferProfileModel, profile_id)
        if orm_obj is None:
            return None
        orm_obj.is_active = False
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def get_active(self, profile_id: UUID) -> OfferProfile | None:
        orm_obj = await self._session.get(OfferProfileModel, profile_id)
        if orm_obj is None or not orm_obj.is_active:
            return None
        return self._to_entity(orm_obj)

    @staticmethod
    def _to_entity(orm_obj: OfferProfileModel) -> OfferProfile:
        return OfferProfile(
            id=orm_obj.id,
            name=orm_obj.name,
            main_value_proposition=orm_obj.main_value_proposition,
            description=orm_obj.description,
            target_outcome=orm_obj.target_outcome,
            pain_points_solved=orm_obj.pain_points_solved,
            key_benefits=orm_obj.key_benefits,
            differentiators=orm_obj.differentiators,
            proof_points=orm_obj.proof_points,
            case_study_notes=orm_obj.case_study_notes,
            pricing_notes=orm_obj.pricing_notes,
            call_to_action=orm_obj.call_to_action,
            tone=orm_obj.tone,
            language=orm_obj.language,
            forbidden_claims=orm_obj.forbidden_claims,
            required_disclaimers=orm_obj.required_disclaimers,
            is_active=orm_obj.is_active,
            created_by_user_id=orm_obj.created_by_user_id,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )
