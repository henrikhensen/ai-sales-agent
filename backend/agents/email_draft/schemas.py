"""Input and output schemas for the Email Draft Agent.

``EmailDraftRequest`` is the validated task input (also used as the API
request body). ``EmailDraftResponse`` is the structured email draft the agent
produces (also used as the API response body).

Both extend the framework base classes from :mod:`backend.agents.schemas`.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, HttpUrl, field_validator

from backend.agents.schemas import AgentInput, AgentOutput

EmailTone = Literal["professional", "friendly", "concise", "consultative"]


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


class EmailDraftRequest(AgentInput):
    """Company, lead and personalization context supplied for an email draft.

    ``company_name`` and ``product_or_service_offered`` are mandatory; every
    other field is optional context. No data is fetched from external
    services and no email is ever sent — the agent produces a draft only.
    """

    company_name: str = Field(
        min_length=1,
        max_length=200,
        description="Name of the recipient's company (required).",
    )
    website_url: HttpUrl | None = Field(
        default=None,
        description="Public website URL, if known. Must be a valid http(s) URL.",
    )
    industry: str | None = Field(
        default=None, max_length=200, description="Industry or sector, if known."
    )
    recipient_role: str | None = Field(
        default=None, max_length=200, description="Role of the email recipient."
    )
    recipient_name: str | None = Field(
        default=None,
        max_length=200,
        description="Name of the email recipient, if known to the user.",
    )
    sender_name: str | None = Field(
        default=None, max_length=200, description="Name of the sender."
    )
    sender_company: str | None = Field(
        default=None, max_length=200, description="Company of the sender."
    )
    product_or_service_offered: str = Field(
        min_length=1,
        max_length=500,
        description="What the sender offers to this company (required).",
    )
    personalization_summary: str | None = Field(
        default=None,
        max_length=2000,
        description="Summary from the Personalization Engine, if available.",
    )
    relevant_observations: list[str] | None = Field(
        default=None, description="Observations from the Personalization Engine."
    )
    pain_point_angles: list[str] | None = Field(
        default=None, description="Pain point angles from the Personalization Engine."
    )
    value_arguments: list[str] | None = Field(
        default=None, description="Value arguments from the Personalization Engine."
    )
    credibility_points: list[str] | None = Field(
        default=None,
        description="Credibility points from the Personalization Engine.",
    )
    suggested_ctas: list[str] | None = Field(
        default=None,
        description="Suggested calls-to-action from the Personalization Engine.",
    )
    tone: EmailTone | None = Field(
        default=None,
        description=(
            "Desired tone: professional, friendly, concise, or consultative."
        ),
    )
    language: str | None = Field(
        default="German",
        max_length=50,
        description="Language the draft should be written in.",
    )
    notes: str | None = Field(
        default=None, max_length=5000, description="Free-form context from the user."
    )

    @field_validator(
        "company_name",
        "industry",
        "recipient_role",
        "recipient_name",
        "sender_name",
        "sender_company",
        "product_or_service_offered",
        "personalization_summary",
        "language",
        "notes",
        mode="before",
    )
    @classmethod
    def _no_empty_strings(cls, value: object) -> object:
        return _require_non_empty(value)

    @field_validator(
        "relevant_observations",
        "pain_point_angles",
        "value_arguments",
        "credibility_points",
        "suggested_ctas",
        mode="before",
    )
    @classmethod
    def _no_empty_list_items(cls, value: object) -> object:
        return _clean_string_list(value)


class EmailDraftResponse(AgentOutput):
    """Structured, human-reviewable email draft with supporting metadata.

    This is a draft only: no email is sent by this agent, and the response
    always carries the information a human reviewer needs before sending
    anything (``claims_to_verify``, ``do_not_send_if``, ``compliance_notes``).
    """

    company_name: str = Field(description="Recipient company the draft is for.")
    subject_lines: list[str] = Field(
        default_factory=list,
        description="Three subject line variants for the reviewer to choose from.",
    )
    email_body: str = Field(
        description="The drafted email body. Requires human review before sending."
    )
    alternative_openings: list[str] = Field(
        default_factory=list,
        description="Three alternative opening line variants.",
    )
    alternative_ctas: list[str] = Field(
        default_factory=list,
        description="Three alternative call-to-action variants.",
    )
    personalization_used: list[str] = Field(
        default_factory=list,
        description="Which supplied personalization inputs were used in the draft.",
    )
    claims_to_verify: list[str] = Field(
        default_factory=list,
        description="Statements in the draft that must be verified before sending.",
    )
    do_not_send_if: list[str] = Field(
        default_factory=list,
        description="Conditions under which this draft should NOT be sent.",
    )
    compliance_notes: list[str] = Field(
        default_factory=list,
        description="Why human review is required before this draft is sent.",
    )
    missing_information: list[str] = Field(
        default_factory=list,
        description="Important information that was unavailable.",
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall confidence in the draft, from 0.0 to 1.0.",
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
