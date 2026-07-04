"""Input and output schemas for the Company Intelligence Agent.

``CompanyIntelligenceRequest`` is the validated task input (also used as the
API request body). ``CompanyIntelligenceResponse`` is the deeper, strategic
company analysis the agent produces (also used as the API response body).

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


class CompanyIntelligenceRequest(AgentInput):
    """Company information supplied by the user for a strategic analysis.

    Only ``company_name`` is mandatory; every other field is optional context.
    No data is fetched from external services — the agent works purely from the
    information supplied here.
    """

    company_name: str = Field(
        min_length=1,
        max_length=200,
        description="Name of the company to analyse (required).",
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
    company_description: str | None = Field(
        default=None,
        max_length=5000,
        description="User-provided description of the company.",
    )
    website_text: str | None = Field(
        default=None,
        max_length=20000,
        description="Text extracted from the company's public website.",
    )
    known_products: list[str] | None = Field(
        default=None, description="Products or services already known to the user."
    )
    known_customers: list[str] | None = Field(
        default=None, description="Customers or references already known to the user."
    )
    notes: str | None = Field(
        default=None, max_length=5000, description="Free-form context from the user."
    )

    @field_validator(
        "company_name",
        "industry",
        "location",
        "company_description",
        "website_text",
        "notes",
        mode="before",
    )
    @classmethod
    def _no_empty_strings(cls, value: object) -> object:
        return _require_non_empty(value)

    @field_validator("known_products", "known_customers", mode="before")
    @classmethod
    def _no_empty_list_items(cls, value: object) -> object:
        return _clean_string_list(value)


class CompanyIntelligenceResponse(AgentOutput):
    """Structured, evidence-based strategic company profile.

    Identity fields (``company_name``, ``website_url``, ``industry``,
    ``location``) echo the validated input — they are never invented by the
    model. ``missing_information`` and ``sources_used`` keep the analysis
    honest about what is grounded versus unknown.
    """

    company_name: str = Field(description="Company the profile is about.")
    website_url: str | None = Field(
        default=None, description="Website URL echoed from the input, if provided."
    )
    industry: str | None = Field(
        default=None, description="Industry echoed from the input, if provided."
    )
    location: str | None = Field(
        default=None, description="Location echoed from the input, if provided."
    )
    business_summary: str = Field(
        description="Strategic summary derived only from the supplied input."
    )
    products_and_services: list[str] = Field(
        default_factory=list,
        description="Products / services grounded in the input.",
    )
    target_segments: list[str] = Field(
        default_factory=list, description="Market segments the company serves."
    )
    likely_buyer_personas: list[str] = Field(
        default_factory=list,
        description="Plausible buyer personas, flagged as inference.",
    )
    value_proposition: list[str] = Field(
        default_factory=list, description="The company's value propositions."
    )
    positioning_summary: str = Field(
        description="How the company appears to position itself, from the input."
    )
    possible_competitive_context: list[str] = Field(
        default_factory=list,
        description=(
            "Competitors or alternatives ONLY if named in, or clearly implied by, "
            "the input. Never invented."
        ),
    )
    sales_relevance: list[str] = Field(
        default_factory=list,
        description="Why the company could be commercially relevant.",
    )
    potential_business_challenges: list[str] = Field(
        default_factory=list,
        description="Plausible business challenges, flagged as inference.",
    )
    personalization_hooks: list[str] = Field(
        default_factory=list,
        description="Factual hooks for tailoring outreach later. No fabricated facts.",
    )
    missing_information: list[str] = Field(
        default_factory=list,
        description="Important information that was unavailable.",
    )
    sources_used: list[str] = Field(
        default_factory=list, description="The basis for the analysis."
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall confidence in the profile, from 0.0 to 1.0.",
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
