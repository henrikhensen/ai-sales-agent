"""Input and output schemas for the Personalization Engine.

``PersonalizationRequest`` is the validated task input (also used as the API
request body). ``PersonalizationResponse`` is the structured personalization
strategy the agent produces (also used as the API response body).

Both extend the framework base classes from :mod:`backend.agents.schemas`.
"""

from __future__ import annotations

from pydantic import Field, HttpUrl, field_validator

from backend.agents.schemas import AgentInput, AgentOutput


def _require_non_empty(value: object) -> object:
    """Reject empty / whitespace-only strings and trim surrounding whitespace.

    Non-string values are returned unchanged so normal type validation can
    still report a helpful error.
    """
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty or whitespace only")
        return stripped
    return value


def _clean_string_list(value: object) -> object:
    """Trim list items and reject empty / whitespace-only entries.

    Non-list values are returned unchanged so normal type validation can raise.
    """
    if isinstance(value, list):
        cleaned: list[str] = []
        for item in value:
            if not isinstance(item, str):
                # Let Pydantic report the type error for the offending item.
                return value
            stripped = item.strip()
            if not stripped:
                raise ValueError("list items must not be empty or whitespace only")
            cleaned.append(stripped)
        return cleaned
    return value


class PersonalizationRequest(AgentInput):
    """Company, lead and analysis context supplied for a personalization pass.

    ``company_name`` and ``product_or_service_offered`` are mandatory; every
    other field is optional context. No data is fetched from external
    services — the agent works purely from the information supplied here.
    """

    company_name: str = Field(
        min_length=1,
        max_length=200,
        description="Name of the company the outreach would target (required).",
    )
    website_url: HttpUrl | None = Field(
        default=None,
        description="Public website URL, if known. Must be a valid http(s) URL.",
    )
    industry: str | None = Field(
        default=None, max_length=200, description="Industry or sector, if known."
    )
    location: str | None = Field(
        default=None, max_length=200, description="Primary location / market."
    )
    lead_summary: str | None = Field(
        default=None,
        max_length=5000,
        description="Summary from the Lead Research Agent, if available.",
    )
    company_intelligence_summary: str | None = Field(
        default=None,
        max_length=5000,
        description="Summary from the Company Intelligence Agent, if available.",
    )
    target_persona: str | None = Field(
        default=None,
        max_length=200,
        description="The buyer persona the personalization should address.",
    )
    product_or_service_offered: str = Field(
        min_length=1,
        max_length=500,
        description="What the seller offers to this company (required).",
    )
    value_proposition: str | None = Field(
        default=None,
        max_length=1000,
        description="The seller's value proposition, if already defined.",
    )
    known_pain_points: list[str] | None = Field(
        default=None, description="Pain points already known to the user."
    )
    known_triggers: list[str] | None = Field(
        default=None,
        description="Known buying triggers or events (e.g. funding, expansion).",
    )
    notes: str | None = Field(
        default=None, max_length=5000, description="Free-form context from the user."
    )

    @field_validator(
        "company_name",
        "industry",
        "location",
        "lead_summary",
        "company_intelligence_summary",
        "target_persona",
        "product_or_service_offered",
        "value_proposition",
        "notes",
        mode="before",
    )
    @classmethod
    def _no_empty_strings(cls, value: object) -> object:
        return _require_non_empty(value)

    @field_validator("known_pain_points", "known_triggers", mode="before")
    @classmethod
    def _no_empty_list_items(cls, value: object) -> object:
        return _clean_string_list(value)


class PersonalizationResponse(AgentOutput):
    """Structured, evidence-based personalization strategy for a human seller.

    Identity fields (``company_name``, ``website_url``, ``industry``) echo the
    validated input — they are never invented by the model. This is a
    personalization *strategy*, not a message: no field contains ready-to-send
    outreach text, and no contact is made on behalf of the user.
    """

    company_name: str = Field(description="Company the strategy is about.")
    website_url: str | None = Field(
        default=None, description="Website URL echoed from the input, if provided."
    )
    industry: str | None = Field(
        default=None, description="Industry echoed from the input, if provided."
    )
    personalization_summary: str = Field(
        description="Short summary of how to personalize the approach."
    )
    relevant_observations: list[str] = Field(
        default_factory=list,
        description="Observations grounded only in the input or supplied sources.",
    )
    possible_conversation_starters: list[str] = Field(
        default_factory=list,
        description="Conversation starter ideas, containing no fabricated facts.",
    )
    pain_point_angles: list[str] = Field(
        default_factory=list,
        description="Angles that connect the offer to plausible pain points.",
    )
    value_arguments: list[str] = Field(
        default_factory=list, description="Arguments for the offered value proposition."
    )
    credibility_points: list[str] = Field(
        default_factory=list,
        description="Points that could build credibility, grounded in the input.",
    )
    objection_risks: list[str] = Field(
        default_factory=list, description="Objections the approach may run into."
    )
    suggested_ctas: list[str] = Field(
        default_factory=list,
        description=(
            "Suggested calls-to-action as ideas only — never a ready-to-send "
            "outreach message."
        ),
    )
    do_not_use_claims: list[str] = Field(
        default_factory=list,
        description="Claims that must NOT be used because they are unverified.",
    )
    missing_information: list[str] = Field(
        default_factory=list,
        description="Important information that was unavailable.",
    )
    sources_used: list[str] = Field(
        default_factory=list, description="The basis for the strategy."
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall confidence in the strategy, from 0.0 to 1.0.",
    )

    @field_validator("confidence_score", mode="before")
    @classmethod
    def _clamp_confidence(cls, value: object) -> object:
        """Clamp the score into [0.0, 1.0].

        A model may return a slightly out-of-range value; clamping keeps the
        contract intact instead of failing the whole response. Non-numeric
        values are passed through so normal validation raises a clear error.
        """
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return min(1.0, max(0.0, float(value)))
        return value
