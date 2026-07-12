"""Deterministic, rule-based Lead Qualification scoring.

Pure computation over data already supplied — no external calls, no LLM,
no fetching. Never invents a fact: every factor either contributes to the
score from data that was actually provided, or is recorded as missing
data with a warning instead of being assumed. Works standalone without
any LLM, matching Aufgabe 5's "regelbasiert muss ohne LLM funktionieren".
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.application.lead_qualification.schemas import (
    QualificationLevel,
    QualificationScoreBreakdown,
    QualificationStatus,
    RecommendedNextAction,
)

_BASE_SCORE = 50.0


@dataclass
class QualificationInput:
    """Normalized input for scoring — built by the orchestrating service
    from either a LeadCandidate or a CRM Lead/Company, so the scoring
    logic itself never needs to know which source it came from."""

    company_name: str | None = None
    industry: str | None = None
    location: str | None = None
    company_size: str | None = None
    website_text: str | None = None
    icp_fit_score: int | None = None
    icp_fit_level: str | None = None
    icp_matched_signals: list[str] = field(default_factory=list)
    icp_negative_signals: list[str] = field(default_factory=list)
    do_not_contact_status: str = "unknown"
    duplicate_status: str = "unknown"
    public_contact_email: str | None = None
    source_confidence: float | None = None
    pipeline_status: str | None = None
    # Deterministic website-quality assessment already computed during Lead
    # Sourcing (see lead_sourcing_service.assess_website_quality) —
    # "poor"/"medium"/"good"/"unknown"/None. Reused here rather than
    # re-derived, so it's identical to what the candidate list already shows.
    website_quality_level: str | None = None
    website_quality_reasons: list[str] = field(default_factory=list)
    # True when the selected Offer's own text (name/value proposition/pain
    # points) is about a website relaunch/redesign — set by the
    # orchestrating service from the actual Offer Profile, never guessed
    # here. Flips the polarity of website_quality_level below: an outdated
    # website is the exact reason this offer fits, not a data-quality flaw.
    offer_targets_outdated_websites: bool = False


@dataclass
class QualificationScoringResult:
    score: int
    level: QualificationLevel
    status: QualificationStatus
    breakdown: QualificationScoreBreakdown
    positive_signals: list[str]
    negative_signals: list[str]
    missing_data: list[str]
    recommended_next_action: RecommendedNextAction
    disqualification_reason: str | None
    fit_summary: str
    recommended_outreach_angle: str | None


def _level_for_score(score: int) -> QualificationLevel:
    if score >= 85:
        return "excellent"
    if score >= 70:
        return "good"
    if score >= 55:
        return "medium"
    if score >= 40:
        return "weak"
    return "not_fit"


class QualificationScoringService:
    """Stateless rule-based scorer. Thresholds are passed in per call so
    callers can honor per-request overrides (e.g. a campaign-specific
    min_score) without needing a new instance."""

    def score(
        self,
        data: QualificationInput,
        *,
        min_score: int,
        priority_score: int,
        disqualify_score: int,
    ) -> QualificationScoringResult:
        breakdown = QualificationScoreBreakdown(base_score=_BASE_SCORE)
        positive_signals: list[str] = []
        negative_signals: list[str] = []
        missing_data: list[str] = []
        score = _BASE_SCORE

        # -- ICP fit --------------------------------------------------------------
        if data.icp_fit_score is not None:
            contribution = (data.icp_fit_score - 50) * 0.4
            breakdown.icp_fit_contribution = contribution
            score += contribution
            if data.icp_fit_level in ("excellent", "good"):
                positive_signals.append(
                    f"ICP fit is '{data.icp_fit_level}' (fit score {data.icp_fit_score})."
                )
            elif data.icp_fit_level in ("weak", "not_fit"):
                negative_signals.append(
                    f"ICP fit is '{data.icp_fit_level}' (fit score {data.icp_fit_score})."
                )
            positive_signals.extend(data.icp_matched_signals)
            negative_signals.extend(data.icp_negative_signals)
        else:
            missing_data.append(
                "No ICP fit data available — qualification is based on other "
                "signals only."
            )

        # -- industry / location / company size ------------------------------------
        if data.industry:
            breakdown.industry_match = 3.0
            score += 3.0
        else:
            missing_data.append("No industry identified.")

        if data.location:
            breakdown.location_match = 2.0
            score += 2.0
        else:
            missing_data.append("No location identified.")

        if not data.company_size:
            missing_data.append("No company size identified.")

        # -- website signal quality --------------------------------------------------
        text_length = len((data.website_text or "").strip())
        if text_length > 200:
            breakdown.website_signal_quality = 5.0
            score += 5.0
            positive_signals.append("Website text provides substantial signal for scoring.")
        elif text_length > 0:
            breakdown.website_signal_quality = 2.0
            score += 2.0
        else:
            missing_data.append("No website text available.")

        # -- website quality vs. offer fit -------------------------------------------
        # For an offer that is itself about fixing an outdated website, a
        # poor/medium website is the exact reason this candidate fits — the
        # opposite of every other signal above, where more/better data is
        # always better. A "good" website slightly reduces urgency instead.
        if data.offer_targets_outdated_websites and data.website_quality_level is not None:
            if data.website_quality_level in ("poor", "unknown"):
                breakdown.website_relaunch_fit = 15.0
                score += 15.0
                positive_signals.append(
                    "Website wirkt veraltet/schwach — passt zum Website-Relaunch-Angebot."
                )
                positive_signals.extend(
                    f"Relaunch-Signal: {reason}" for reason in data.website_quality_reasons
                )
            elif data.website_quality_level == "medium":
                breakdown.website_relaunch_fit = 8.0
                score += 8.0
                positive_signals.append(
                    "Website zeigt Optimierungspotenzial — passt zum "
                    "Website-Relaunch-Angebot."
                )
                positive_signals.extend(
                    f"Relaunch-Signal: {reason}" for reason in data.website_quality_reasons
                )
            else:  # "good"
                breakdown.website_relaunch_fit = -5.0
                score -= 5.0
                negative_signals.append(
                    "Website wirkt bereits modern — Relaunch-Bedarf könnte geringer sein."
                )

        # -- buying triggers / pain points / keywords (derived from ICP signals) -----
        trigger_hits = [s for s in data.icp_matched_signals if "trigger" in s.lower()]
        if trigger_hits:
            breakdown.buying_triggers = 5.0 * len(trigger_hits)
            score += breakdown.buying_triggers

        pain_hits = [s for s in data.icp_matched_signals if "pain point" in s.lower()]
        if pain_hits:
            breakdown.pain_points_match = 5.0 * len(pain_hits)
            score += breakdown.pain_points_match

        keyword_hits = [s for s in data.icp_matched_signals if "keyword" in s.lower()]
        if keyword_hits:
            breakdown.keyword_match = 3.0 * len(keyword_hits)
            score += breakdown.keyword_match

        # -- negative keywords / excluded signals -------------------------------------
        negative_keyword_hits = [
            s for s in data.icp_negative_signals if "keyword" in s.lower()
        ]
        if negative_keyword_hits:
            penalty = 10.0 * len(negative_keyword_hits)
            breakdown.negative_keywords_penalty = -penalty
            score -= penalty

        excluded_hits = [s for s in data.icp_negative_signals if "excluded" in s.lower()]
        if excluded_hits:
            penalty = 25.0 * len(excluded_hits)
            breakdown.excluded_signals_penalty = -penalty
            score -= penalty

        # -- data completeness ---------------------------------------------------------
        fields_present = sum(
            [
                bool(data.company_name),
                bool(data.industry),
                bool(data.location),
                bool(data.website_text),
                bool(data.public_contact_email),
            ]
        )
        if fields_present <= 2:
            breakdown.data_completeness_penalty = -5.0
            score -= 5.0
            missing_data.append(
                "Limited data available for this lead — score may be less reliable."
            )

        # -- contact availability ---------------------------------------------------
        if data.public_contact_email:
            positive_signals.append("A public contact email is available.")
        else:
            missing_data.append("No public contact email found.")

        # -- source confidence --------------------------------------------------------
        if data.source_confidence is not None:
            contribution = (data.source_confidence - 0.5) * 10.0
            breakdown.source_confidence_contribution = contribution
            score += contribution

        final_score = max(0, min(100, round(score)))
        breakdown.total = float(final_score)
        level = _level_for_score(final_score)

        # Only fields that actually contributed to (or reduced) the score
        # count toward "this score can't be trusted yet" — company_size and
        # public_contact_email are informational-only (never affect the
        # score above) and, for candidate-sourced leads, are structurally
        # almost never knowable at all; letting their absence alone force
        # "needs_review" regardless of an otherwise-good score was exactly
        # what made real Lead Finder candidates disappear into "needs
        # review" instead of "qualified" even at min_score=0.
        score_confidence_gaps = sum(
            [
                data.icp_fit_score is None,
                not data.industry,
                not data.location,
                text_length == 0,
            ]
        )

        status, next_action, disqualification_reason = self._determine_status(
            data=data,
            score=final_score,
            score_confidence_gaps=score_confidence_gaps,
            min_score=min_score,
            priority_score=priority_score,
            disqualify_score=disqualify_score,
        )

        fit_summary = self._build_fit_summary(
            data=data,
            score=final_score,
            level=level,
            positive_count=len(positive_signals),
            negative_count=len(negative_signals),
        )
        outreach_angle = self._build_outreach_angle(data)

        return QualificationScoringResult(
            score=final_score,
            level=level,
            status=status,
            breakdown=breakdown,
            positive_signals=positive_signals,
            negative_signals=negative_signals,
            missing_data=missing_data,
            recommended_next_action=next_action,
            disqualification_reason=disqualification_reason,
            fit_summary=fit_summary,
            recommended_outreach_angle=outreach_angle,
        )

    @staticmethod
    def _determine_status(
        *,
        data: QualificationInput,
        score: int,
        score_confidence_gaps: int,
        min_score: int,
        priority_score: int,
        disqualify_score: int,
    ) -> tuple[QualificationStatus, RecommendedNextAction, str | None]:
        # Do-not-contact and duplicates always take precedence over score.
        if data.do_not_contact_status == "blocked":
            return "blocked", "blocked_do_not_contact", None
        if data.duplicate_status == "duplicate":
            return "duplicate", "merge_duplicate", None
        if score < disqualify_score:
            return (
                "disqualified",
                "skip",
                f"Score {score} is below the disqualify threshold ({disqualify_score}).",
            )
        # Sparse data means a qualified/priority call can't be trusted yet,
        # even if the raw score looks good — never fabricate confidence.
        # Only counts gaps in fields that actually influenced the score
        # (see score_confidence_gaps above), not permanently-unknowable or
        # purely informational fields.
        if score_confidence_gaps >= 3:
            return "needs_review", "enrich_more", None
        if score >= priority_score:
            return "priority", "start_sales_workflow", None
        if score >= min_score:
            return "qualified", "start_sales_workflow", None
        return "needs_review", "review_manually", None

    @staticmethod
    def _build_fit_summary(
        *,
        data: QualificationInput,
        score: int,
        level: QualificationLevel,
        positive_count: int,
        negative_count: int,
    ) -> str:
        subject = data.company_name or "This lead"
        return (
            f"{subject} scored {score}/100 ({level}) based on {positive_count} "
            f"positive and {negative_count} negative signal(s)."
        )

    @staticmethod
    def _build_outreach_angle(data: QualificationInput) -> str | None:
        # Prefer a matched pain point or buying trigger as the angle; fall
        # back to nothing rather than inventing one.
        for signal in data.icp_matched_signals:
            lowered = signal.lower()
            if "pain point" in lowered or "trigger" in lowered:
                return signal
        if data.icp_matched_signals:
            return data.icp_matched_signals[0]
        return None
