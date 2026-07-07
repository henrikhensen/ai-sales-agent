"""Optional LLM advisor that improves the wording of an already-computed,
rule-based Lead Qualification result.

Only ever asked to rewrite ``fit_summary``/``recommended_outreach_angle``/
``missing_data`` — it never computes or changes the score, level, or
status itself (those stay fully rule-based, per Aufgabe 5/6). Mock
provider is the default (via the shared LLM factory); real calls only
happen when the app-wide ``LLM_PROVIDER=anthropic`` and
``LLM_ENABLE_REAL_CALLS=true`` are both already set. Any failure (timeout,
malformed response, provider error) falls back to the unmodified
rule-based result — this must never crash the qualification workflow.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from backend.application.lead_qualification.qualification_scoring_service import (
    QualificationScoringResult,
)
from backend.infrastructure.llm.base import LLMProvider

_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "fit_summary": {"type": "string"},
        "recommended_outreach_angle": {"type": "string"},
        "missing_data_notes": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["fit_summary", "recommended_outreach_angle", "missing_data_notes"],
}

_SYSTEM_PROMPT = (
    "You are a sales qualification assistant. You improve the wording of an "
    "already-computed lead qualification result. You NEVER invent facts not "
    "present in the input, NEVER guarantee outcomes or results, NEVER claim "
    "anything the input doesn't support, and NEVER state or imply any "
    "forbidden claim listed in the input. Keep responses short and grounded "
    "strictly in the data provided."
)

#: Prompt text is capped at roughly 4x the configured notes-char limit —
#: generous for the structured summary this builds, while still bounded.
_PROMPT_SIZE_MULTIPLIER = 4


class QualificationLLMAdvisor:
    """Wraps one :class:`LLMProvider` call with a fixed schema and a
    strict, silent fallback to the original rule-based result."""

    def __init__(self, llm: LLMProvider, *, max_notes_chars: int) -> None:
        self._llm = llm
        self._max_notes_chars = max_notes_chars

    async def enhance(
        self,
        scoring_result: QualificationScoringResult,
        *,
        company_name: str | None,
        industry: str | None,
        offer_value_proposition: str | None = None,
        offer_forbidden_claims: list[str] | None = None,
    ) -> QualificationScoringResult:
        prompt = self._build_prompt(
            scoring_result,
            company_name=company_name,
            industry=industry,
            offer_value_proposition=offer_value_proposition,
            offer_forbidden_claims=offer_forbidden_claims,
        )
        try:
            raw = await self._llm.generate_json(
                system=_SYSTEM_PROMPT,
                prompt=prompt,
                schema=_OUTPUT_SCHEMA,
                max_tokens=400,
            )
        except Exception:
            # Any failure (LLMError subclasses, timeouts, malformed
            # responses) falls back to the unmodified rule-based result —
            # this advisor must never crash the qualification workflow.
            return scoring_result

        updated = replace(scoring_result)

        fit_summary = raw.get("fit_summary")
        if isinstance(fit_summary, str) and fit_summary.strip():
            updated.fit_summary = fit_summary.strip()[: self._max_notes_chars]

        outreach_angle = raw.get("recommended_outreach_angle")
        if isinstance(outreach_angle, str) and outreach_angle.strip():
            updated.recommended_outreach_angle = outreach_angle.strip()[
                : self._max_notes_chars
            ]

        missing_notes = raw.get("missing_data_notes")
        if isinstance(missing_notes, list):
            cleaned = [n.strip() for n in missing_notes if isinstance(n, str) and n.strip()]
            if cleaned:
                updated.missing_data = list(dict.fromkeys([*updated.missing_data, *cleaned]))

        return updated

    def _build_prompt(
        self,
        scoring_result: QualificationScoringResult,
        *,
        company_name: str | None,
        industry: str | None,
        offer_value_proposition: str | None,
        offer_forbidden_claims: list[str] | None,
    ) -> str:
        lines = [
            f"Company: {company_name or 'unknown'}",
            f"Industry: {industry or 'unknown'}",
            f"Score: {scoring_result.score}/100 ({scoring_result.level})",
            f"Status: {scoring_result.status}",
            "Positive signals: "
            + ("; ".join(scoring_result.positive_signals) or "none"),
            "Negative signals: "
            + ("; ".join(scoring_result.negative_signals) or "none"),
            "Missing data: " + ("; ".join(scoring_result.missing_data) or "none"),
        ]
        if offer_value_proposition:
            lines.append(f"Offer value proposition: {offer_value_proposition}")
        if offer_forbidden_claims:
            lines.append(
                "Never state or imply any of these claims: "
                + "; ".join(offer_forbidden_claims)
            )
        lines.append(
            "Task: write a short (1-2 sentence) fit_summary, a short "
            "recommended_outreach_angle grounded only in the signals above, "
            "and up to 3 short missing_data_notes describing what additional "
            "information would improve confidence. Do not invent facts, do "
            "not guarantee outcomes."
        )
        text = "\n".join(lines)
        return text[: self._max_notes_chars * _PROMPT_SIZE_MULTIPLIER]
