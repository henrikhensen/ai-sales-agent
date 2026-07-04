"""Input and output schemas for the Lead Research Agent.

``LeadResearchRequest`` is the validated task input (also used as the API
request body). ``LeadResearchResponse`` is the structured lead profile the
agent produces (also used as the API response body).

Both extend the framework base classes from :mod:`backend.agents.schemas`, so
the agent runner can treat them like any other agent I/O.
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


class LeadResearchRequest(AgentInput):
    """User-provided information about a company to analyse.

    Only ``company_name`` is mandatory; every other field is optional context
    that improves the quality of the produced profile. No data is fetched from
    external services — the agent works purely from what is supplied here.
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
        default=None,
        max_length=200,
        description="Industry or sector, if known.",
    )
    location: str | None = Field(
        default=None,
        max_length=200,
        description="Primary location / market, if known.",
    )
    notes: str | None = Field(
        default=None,
        max_length=5000,
        description="Free-form context provided by the user.",
    )

    @field_validator("company_name", "industry", "location", "notes", mode="before")
    @classmethod
    def _no_empty_strings(cls, value: object) -> object:
        return _require_non_empty(value)


class LeadResearchResponse(AgentOutput):
    """Structured, evidence-based lead profile.

    Identity fields (``company_name``, ``website_url``, ``industry``,
    ``location``) echo the validated input — they are never invented by the
    model. The remaining fields hold the model's analysis, with explicit
    ``missing_information`` and ``sources_used`` so the reader can judge how
    grounded the profile is.
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
    short_summary: str = Field(
        description="Brief, factual summary derived only from the supplied input."
    )
    target_customers: list[str] = Field(
        default_factory=list,
        description="Likely customer segments the company serves.",
    )
    likely_pain_points: list[str] = Field(
        default_factory=list,
        description="Plausible business pain points, flagged as inference.",
    )
    possible_sales_angles: list[str] = Field(
        default_factory=list,
        description="Analytical sales angles. Never a proposal to make contact.",
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall confidence in the profile, from 0.0 to 1.0.",
    )
    missing_information: list[str] = Field(
        default_factory=list,
        description="Information that was unavailable and would improve the profile.",
    )
    sources_used: list[str] = Field(
        default_factory=list,
        description="The basis for the analysis (e.g. 'user-provided notes').",
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
