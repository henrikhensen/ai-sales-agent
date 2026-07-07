"""ICP (Ideal Customer Profile) service: CRUD plus fit scoring.

Fit scoring only ever evaluates data already supplied to it — manually
entered fields, or website research text already fetched by the existing
Website Research feature. It never scrapes, fetches, or invents anything:
a missing field always produces a warning, never an assumption. There is
no LinkedIn scraping or any other external data collection here.
"""

from __future__ import annotations

from uuid import UUID

from backend.application.sales_strategy.schemas import (
    CreateICPProfileRequest,
    FitLevel,
    ICPFitCheckRequest,
    ICPFitCheckResponse,
    ICPProfileListResponse,
    ICPProfileResponse,
    UpdateICPProfileRequest,
)
from backend.domain.entities.icp_profile import ICPProfile
from backend.domain.exceptions import ICPProfileNotFoundError
from backend.domain.repositories.icp_profile_repository import ICPProfileRepository

# Points awarded per matched positive signal. Capped per category so no
# single long list can dominate the score.
_INDUSTRY_MATCH_POINTS = 15
_KEYWORD_MATCH_POINTS = 5
_KEYWORD_MATCH_CAP = 20
_PAIN_POINT_MATCH_POINTS = 5
_PAIN_POINT_MATCH_CAP = 15
_TRIGGER_MATCH_POINTS = 10
_TRIGGER_MATCH_CAP = 20
_REQUIRED_SIGNAL_MATCH_POINTS = 10
_REQUIRED_SIGNAL_MATCH_CAP = 30

# Points deducted per matched negative signal — deliberately much larger
# than any positive category so an exclusion criterion reliably dominates.
_EXCLUDED_INDUSTRY_PENALTY = 40
_NEGATIVE_KEYWORD_PENALTY = 10
_NEGATIVE_KEYWORD_PENALTY_CAP = 30
_EXCLUDED_SIGNAL_PENALTY = 40

_BASE_SCORE = 50


def _contains(haystack: str, needle: str) -> bool:
    return needle.strip().lower() in haystack


class ICPService:
    def __init__(self, icp_profiles: ICPProfileRepository) -> None:
        self._icp_profiles = icp_profiles

    # -- CRUD -----------------------------------------------------------------

    async def create(
        self, request: CreateICPProfileRequest, created_by_user_id: UUID | None
    ) -> ICPProfileResponse:
        profile = ICPProfile(
            name=request.name,
            description=request.description,
            target_industries=request.target_industries,
            excluded_industries=request.excluded_industries,
            target_company_sizes=request.target_company_sizes,
            target_locations=request.target_locations,
            target_languages=request.target_languages,
            target_keywords=request.target_keywords,
            negative_keywords=request.negative_keywords,
            target_pain_points=request.target_pain_points,
            buying_triggers=request.buying_triggers,
            required_signals=request.required_signals,
            excluded_signals=request.excluded_signals,
            buyer_personas=request.buyer_personas,
            preferred_titles=request.preferred_titles,
            excluded_titles=request.excluded_titles,
            minimum_fit_score=request.minimum_fit_score,
            scoring_weights=request.scoring_weights,
            is_active=request.is_active,
            created_by_user_id=created_by_user_id,
        )
        created = await self._icp_profiles.create(profile)
        return ICPProfileResponse.model_validate(created)

    async def list(
        self, limit: int = 100, offset: int = 0, active_only: bool = False
    ) -> ICPProfileListResponse:
        profiles = await self._icp_profiles.list(
            limit=limit, offset=offset, active_only=active_only
        )
        return ICPProfileListResponse(
            items=[ICPProfileResponse.model_validate(p) for p in profiles],
            limit=limit,
            offset=offset,
        )

    async def get(self, profile_id: UUID) -> ICPProfileResponse:
        profile = await self._icp_profiles.get_by_id(profile_id)
        if profile is None:
            raise ICPProfileNotFoundError(profile_id)
        return ICPProfileResponse.model_validate(profile)

    async def update(
        self, profile_id: UUID, request: UpdateICPProfileRequest
    ) -> ICPProfileResponse:
        existing = await self._icp_profiles.get_by_id(profile_id)
        if existing is None:
            raise ICPProfileNotFoundError(profile_id)

        updates = request.model_dump(exclude_unset=True)
        for field_name, value in updates.items():
            setattr(existing, field_name, value)

        updated = await self._icp_profiles.update(existing)
        if updated is None:
            raise ICPProfileNotFoundError(profile_id)
        return ICPProfileResponse.model_validate(updated)

    async def deactivate(self, profile_id: UUID) -> ICPProfileResponse:
        updated = await self._icp_profiles.deactivate(profile_id)
        if updated is None:
            raise ICPProfileNotFoundError(profile_id)
        return ICPProfileResponse.model_validate(updated)

    # -- Fit scoring ------------------------------------------------------------

    async def check_fit(self, request: ICPFitCheckRequest) -> ICPFitCheckResponse:
        """Score the supplied ad-hoc data against one ICP profile.

        Only evaluates the fields the caller supplied (manually entered, or
        already-fetched website research text) — never fetches or invents
        anything. Missing data always produces a warning, never a silent
        assumption.
        """
        profile = await self._icp_profiles.get_by_id(request.icp_profile_id)
        if profile is None:
            raise ICPProfileNotFoundError(request.icp_profile_id)

        warnings: list[str] = []
        if not profile.is_active:
            warnings.append(
                "This ICP profile is deactivated — its criteria may be outdated."
            )

        # Build one lowercase corpus of every free-text field supplied, plus
        # the explicit keyword list — matching is a simple, auditable
        # substring check, never an LLM guess.
        text_parts = [
            request.company_name or "",
            request.industry or "",
            request.location or "",
            request.company_size or "",
            request.website_text or "",
            request.notes or "",
            " ".join(request.keywords),
        ]
        corpus = " ".join(text_parts).lower()
        has_any_data = bool(corpus.strip())

        if not has_any_data:
            warnings.append(
                "No data was provided to score — fit_score reflects the "
                "absence of information, not an actual assessment."
            )

        score = _BASE_SCORE
        matched_signals: list[str] = []
        negative_signals: list[str] = []
        missing_signals: list[str] = []

        # -- positive signals ---------------------------------------------------

        if profile.target_industries:
            if request.industry:
                industry_hit = next(
                    (i for i in profile.target_industries if _contains(corpus, i)),
                    None,
                )
                if industry_hit:
                    score += _INDUSTRY_MATCH_POINTS
                    matched_signals.append(f"Industry matches target: {industry_hit}")
                else:
                    missing_signals.append(
                        "Industry does not match any target_industries."
                    )
            else:
                warnings.append(
                    "No industry provided — could not check against target_industries."
                )

        if profile.target_keywords:
            keyword_hits = [k for k in profile.target_keywords if _contains(corpus, k)]
            if keyword_hits:
                score += min(
                    len(keyword_hits) * _KEYWORD_MATCH_POINTS, _KEYWORD_MATCH_CAP
                )
                matched_signals.extend(f"Keyword matched: {k}" for k in keyword_hits)
            elif has_any_data:
                missing_signals.append("No target_keywords found in the supplied data.")

        if profile.target_pain_points:
            pain_hits = [p for p in profile.target_pain_points if _contains(corpus, p)]
            if pain_hits:
                score += min(
                    len(pain_hits) * _PAIN_POINT_MATCH_POINTS, _PAIN_POINT_MATCH_CAP
                )
                matched_signals.extend(f"Pain point matched: {p}" for p in pain_hits)
            elif has_any_data:
                missing_signals.append(
                    "No target_pain_points found in the supplied data."
                )

        if profile.buying_triggers:
            trigger_hits = [t for t in profile.buying_triggers if _contains(corpus, t)]
            if trigger_hits:
                score += min(
                    len(trigger_hits) * _TRIGGER_MATCH_POINTS, _TRIGGER_MATCH_CAP
                )
                matched_signals.extend(
                    f"Buying trigger matched: {t}" for t in trigger_hits
                )
            elif has_any_data:
                missing_signals.append("No buying_triggers found in the supplied data.")

        if profile.required_signals:
            required_hits = [
                s for s in profile.required_signals if _contains(corpus, s)
            ]
            required_misses = [
                s for s in profile.required_signals if s not in required_hits
            ]
            if required_hits:
                score += min(
                    len(required_hits) * _REQUIRED_SIGNAL_MATCH_POINTS,
                    _REQUIRED_SIGNAL_MATCH_CAP,
                )
                matched_signals.extend(
                    f"Required signal matched: {s}" for s in required_hits
                )
            missing_signals.extend(
                f"Required signal missing: {s}" for s in required_misses
            )

        # -- negative signals -----------------------------------------------------

        if profile.excluded_industries:
            excluded_hit = next(
                (i for i in profile.excluded_industries if _contains(corpus, i)), None
            )
            if excluded_hit:
                score -= _EXCLUDED_INDUSTRY_PENALTY
                negative_signals.append(f"Excluded industry matched: {excluded_hit}")

        if profile.negative_keywords:
            negative_hits = [
                k for k in profile.negative_keywords if _contains(corpus, k)
            ]
            if negative_hits:
                score -= min(
                    len(negative_hits) * _NEGATIVE_KEYWORD_PENALTY,
                    _NEGATIVE_KEYWORD_PENALTY_CAP,
                )
                negative_signals.extend(
                    f"Negative keyword matched: {k}" for k in negative_hits
                )

        if profile.excluded_signals:
            excluded_signal_hit = next(
                (s for s in profile.excluded_signals if _contains(corpus, s)), None
            )
            if excluded_signal_hit:
                score -= _EXCLUDED_SIGNAL_PENALTY
                negative_signals.append(
                    f"Excluded signal matched: {excluded_signal_hit}"
                )

        score = max(0, min(100, score))
        fit_level = self._fit_level(score, profile.minimum_fit_score)
        recommendation = self._recommendation(fit_level)

        return ICPFitCheckResponse(
            icp_profile_id=profile.id,
            fit_score=score,
            fit_level=fit_level,
            matched_signals=matched_signals,
            missing_signals=missing_signals,
            negative_signals=negative_signals,
            recommendation=recommendation,
            warnings=warnings,
        )

    @staticmethod
    def _fit_level(score: int, minimum_fit_score: int) -> FitLevel:
        """Fit level relative to this ICP's own configured threshold, so a
        stricter or looser ICP produces meaningfully different levels for
        the same raw score."""
        if score >= min(100, minimum_fit_score + 20):
            return "excellent"
        if score >= minimum_fit_score:
            return "good"
        if score >= max(0, minimum_fit_score - 20):
            return "medium"
        if score >= max(0, minimum_fit_score - 40):
            return "weak"
        return "not_fit"

    @staticmethod
    def _recommendation(fit_level: FitLevel) -> str:
        if fit_level in ("excellent", "good"):
            return (
                "This lead matches the ICP well. Outreach preparation via the "
                "Sales Workflow is reasonable, subject to Do-not-contact and "
                "Human Review as always."
            )
        if fit_level == "medium":
            return (
                "This lead is a partial match. Review manually before investing "
                "significant outreach effort."
            )
        if fit_level == "weak":
            return (
                "This lead is a weak match for this ICP. Consider deprioritizing "
                "or skipping outreach."
            )
        return (
            "This lead does not match this ICP. Outreach is not recommended "
            "based on the current criteria."
        )
