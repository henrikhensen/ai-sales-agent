"""Input and output schemas for the Reply Analysis Agent.

``ReplyAnalysisRequest`` is the validated task input (also used as the API
request body). ``ReplyAnalysisResponse`` is the structured classification and
recommendation the agent produces (also used as the API response body).

Both extend the framework base classes from :mod:`backend.agents.schemas`.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator

from backend.agents.schemas import AgentInput, AgentOutput

ReplyClassification = Literal[
    "interested",
    "meeting_request",
    "question",
    "objection",
    "not_interested",
    "out_of_office",
    "unclear",
]
ReplySentiment = Literal["positive", "neutral", "negative", "unclear"]
ReplyUrgency = Literal["low", "medium", "high", "unclear"]


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


class ReplyAnalysisRequest(AgentInput):
    """A lead's reply plus the surrounding context needed to analyse it.

    ``company_name`` and ``reply_text`` are mandatory; every other field is
    optional context. No data is fetched from external services — the agent
    works purely from the information supplied here.
    """

    company_name: str = Field(
        min_length=1,
        max_length=200,
        description="Name of the company the lead is from (required).",
    )
    lead_name: str | None = Field(
        default=None, max_length=200, description="Name of the replying lead."
    )
    lead_role: str | None = Field(
        default=None, max_length=200, description="Role of the replying lead."
    )
    original_email_subject: str | None = Field(
        default=None,
        max_length=300,
        description="Subject of the email the lead is replying to.",
    )
    original_email_body: str | None = Field(
        default=None,
        max_length=20000,
        description="Body of the email the lead is replying to.",
    )
    reply_text: str = Field(
        min_length=1,
        max_length=20000,
        description="The lead's reply text to analyse (required).",
    )
    previous_context: str | None = Field(
        default=None,
        max_length=5000,
        description="Prior context, e.g. earlier thread summary or CRM notes.",
    )
    product_or_service_offered: str | None = Field(
        default=None,
        max_length=500,
        description="What was offered to this lead, if relevant to the analysis.",
    )
    notes: str | None = Field(
        default=None, max_length=5000, description="Free-form context from the user."
    )

    @field_validator(
        "company_name",
        "lead_name",
        "lead_role",
        "original_email_subject",
        "original_email_body",
        "reply_text",
        "previous_context",
        "product_or_service_offered",
        "notes",
        mode="before",
    )
    @classmethod
    def _no_empty_strings(cls, value: object) -> object:
        return _require_non_empty(value)


class ReplyAnalysisResponse(AgentOutput):
    """Structured, human-reviewable analysis of a lead's reply.

    This is an analysis and recommendation only: no reply is sent, no meeting
    is booked, and no contact is made by this agent. ``suggested_reply`` is a
    draft for a human to review, never an executed action.
    """

    company_name: str = Field(description="Company the analysis is about.")
    classification: ReplyClassification = Field(
        description="Objective classification of the reply."
    )
    sentiment: ReplySentiment = Field(description="Overall sentiment of the reply.")
    urgency: ReplyUrgency = Field(
        description="How urgently a human should act on this reply."
    )
    summary: str = Field(description="Short, factual summary of the reply.")
    detected_intent: list[str] = Field(
        default_factory=list, description="Intents detected in the reply."
    )
    recommended_next_action: str = Field(
        description="Recommended next action for a human to take."
    )
    suggested_reply: str | None = Field(
        default=None,
        description=(
            "A draft reply for human review only. Never sent automatically."
        ),
    )
    suggested_reply_subject: str | None = Field(
        default=None, description="Subject line for the suggested reply draft."
    )
    questions_to_answer: list[str] = Field(
        default_factory=list,
        description="Questions from the lead that still need an answer.",
    )
    objections_detected: list[str] = Field(
        default_factory=list, description="Objections raised in the reply."
    )
    buying_signals: list[str] = Field(
        default_factory=list, description="Buying signals detected in the reply."
    )
    do_not_continue_if: list[str] = Field(
        default_factory=list,
        description="Conditions under which no further contact should be made.",
    )
    compliance_notes: list[str] = Field(
        default_factory=list,
        description="Why human review is required before acting on this analysis.",
    )
    missing_information: list[str] = Field(
        default_factory=list,
        description="Important information that was unavailable.",
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall confidence in the analysis, from 0.0 to 1.0.",
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
