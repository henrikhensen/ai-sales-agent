"""Offer profile service: CRUD plus a preview for Email Draft context.

An Offer profile defines what is being sold and the guardrails around how
it may be described. ``forbidden_claims`` and missing ``proof_points`` are
treated as hard warnings here, not suggestions — nothing here invents a
case study, guarantees an outcome, or fabricates a proof point.
"""

from __future__ import annotations

from uuid import UUID

from backend.application.sales_strategy.schemas import (
    CreateOfferProfileRequest,
    OfferPreviewResponse,
    OfferProfileListResponse,
    OfferProfileResponse,
    UpdateOfferProfileRequest,
)
from backend.domain.entities.offer_profile import OfferProfile
from backend.domain.exceptions import OfferProfileNotFoundError
from backend.domain.repositories.offer_profile_repository import OfferProfileRepository


class OfferService:
    def __init__(self, offer_profiles: OfferProfileRepository) -> None:
        self._offer_profiles = offer_profiles

    # -- CRUD -----------------------------------------------------------------

    async def create(
        self, request: CreateOfferProfileRequest, created_by_user_id: UUID | None
    ) -> OfferProfileResponse:
        profile = OfferProfile(
            name=request.name,
            main_value_proposition=request.main_value_proposition,
            description=request.description,
            target_outcome=request.target_outcome,
            pain_points_solved=request.pain_points_solved,
            key_benefits=request.key_benefits,
            differentiators=request.differentiators,
            proof_points=request.proof_points,
            case_study_notes=request.case_study_notes,
            pricing_notes=request.pricing_notes,
            call_to_action=request.call_to_action,
            tone=request.tone,
            language=request.language,
            forbidden_claims=request.forbidden_claims,
            required_disclaimers=request.required_disclaimers,
            is_active=request.is_active,
            created_by_user_id=created_by_user_id,
        )
        created = await self._offer_profiles.create(profile)
        return OfferProfileResponse.model_validate(created)

    async def list(
        self, limit: int = 100, offset: int = 0, active_only: bool = False
    ) -> OfferProfileListResponse:
        profiles = await self._offer_profiles.list(
            limit=limit, offset=offset, active_only=active_only
        )
        return OfferProfileListResponse(
            items=[OfferProfileResponse.model_validate(p) for p in profiles],
            limit=limit,
            offset=offset,
        )

    async def get(self, profile_id: UUID) -> OfferProfileResponse:
        profile = await self._offer_profiles.get_by_id(profile_id)
        if profile is None:
            raise OfferProfileNotFoundError(profile_id)
        return OfferProfileResponse.model_validate(profile)

    async def get_entity(self, profile_id: UUID) -> OfferProfile:
        """Return the raw domain entity — for internal use by other
        services (e.g. the Sales Workflow) that need every field, not the
        API response shape."""
        profile = await self._offer_profiles.get_by_id(profile_id)
        if profile is None:
            raise OfferProfileNotFoundError(profile_id)
        return profile

    async def update(
        self, profile_id: UUID, request: UpdateOfferProfileRequest
    ) -> OfferProfileResponse:
        existing = await self._offer_profiles.get_by_id(profile_id)
        if existing is None:
            raise OfferProfileNotFoundError(profile_id)

        updates = request.model_dump(exclude_unset=True)
        for field_name, value in updates.items():
            setattr(existing, field_name, value)

        updated = await self._offer_profiles.update(existing)
        if updated is None:
            raise OfferProfileNotFoundError(profile_id)
        return OfferProfileResponse.model_validate(updated)

    async def deactivate(self, profile_id: UUID) -> OfferProfileResponse:
        updated = await self._offer_profiles.deactivate(profile_id)
        if updated is None:
            raise OfferProfileNotFoundError(profile_id)
        return OfferProfileResponse.model_validate(updated)

    # -- Preview ----------------------------------------------------------------

    async def preview(self, profile_id: UUID) -> OfferPreviewResponse:
        """Build a short, honest preview of how this offer would be
        positioned in an email draft. Never fabricates a case study,
        guarantees an outcome, or hides a missing proof point."""
        profile = await self._offer_profiles.get_by_id(profile_id)
        if profile is None:
            raise OfferProfileNotFoundError(profile_id)

        warnings: list[str] = []
        if not profile.is_active:
            warnings.append(
                "This offer profile is deactivated — review before using it."
            )
        if not profile.proof_points:
            warnings.append(
                "No proof_points are defined — avoid implying credibility that "
                "hasn't been established."
            )
        if profile.forbidden_claims:
            warnings.append(
                "forbidden_claims are defined for this offer — the Sales "
                "Workflow actively avoids them; never add them back manually."
            )
        if not profile.case_study_notes:
            warnings.append(
                "No case study notes are defined — do not invent one."
            )

        summary_parts = [profile.main_value_proposition]
        if profile.key_benefits:
            summary_parts.append(
                "Key benefits: " + "; ".join(profile.key_benefits)
            )
        summary = " ".join(summary_parts)

        positioning_parts: list[str] = []
        if profile.target_outcome:
            positioning_parts.append(f"Target outcome: {profile.target_outcome}")
        if profile.pain_points_solved:
            positioning_parts.append(
                "Solves: " + "; ".join(profile.pain_points_solved)
            )
        if profile.differentiators:
            positioning_parts.append(
                "Differentiators: " + "; ".join(profile.differentiators)
            )
        positioning = (
            " ".join(positioning_parts)
            if positioning_parts
            else "No positioning details defined yet."
        )

        return OfferPreviewResponse(
            offer_profile_id=profile.id,
            summary=summary,
            positioning=positioning,
            suggested_cta=profile.call_to_action,
            warnings=warnings,
        )
