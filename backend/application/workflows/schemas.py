"""Input and output schemas for the end-to-end Sales Workflow.

``SalesWorkflowRequest`` is the validated task input (also used as the API
request body). ``SalesWorkflowResponse`` aggregates the outputs of every
step (also used as the API response body). This is an application-layer
orchestration DTO, not an agent I/O pair — it does not extend
:mod:`backend.agents.schemas`, since no single LLM call produces it.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl, field_validator

from backend.agents.company_intelligence.schemas import CompanyIntelligenceResponse
from backend.agents.email_draft.schemas import EmailDraftResponse, EmailTone
from backend.agents.lead_research.schemas import LeadResearchResponse
from backend.agents.personalization.schemas import PersonalizationResponse


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


class SalesWorkflowRequest(BaseModel):
    """Input for the end-to-end sales workflow.

    ``company_name`` and ``product_or_service_offered`` are mandatory; every
    other field is optional context passed through to the individual agent
    steps. No data is fetched from external services.
    """

    company_name: str = Field(
        min_length=1,
        max_length=200,
        description="Name of the company to run the workflow for (required).",
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
    target_persona: str | None = Field(
        default=None,
        max_length=200,
        description="The buyer persona the workflow should address.",
    )
    recipient_name: str | None = Field(
        default=None,
        max_length=200,
        description=(
            "Name of the email recipient, if known. Used to draft the email "
            "and, if provided, to create a CRM Contact record for this run."
        ),
    )
    product_or_service_offered: str = Field(
        min_length=1,
        max_length=500,
        description="What the seller offers to this company (required).",
    )
    sender_name: str | None = Field(
        default=None, max_length=200, description="Name of the sender."
    )
    sender_company: str | None = Field(
        default=None, max_length=200, description="Company of the sender."
    )
    tone: EmailTone | None = Field(
        default="professional",
        description=(
            "Desired email tone: professional, friendly, concise, or consultative."
        ),
    )
    language: str | None = Field(
        default="German",
        max_length=50,
        description="Language the email draft should be written in.",
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
        "target_persona",
        "recipient_name",
        "product_or_service_offered",
        "sender_name",
        "sender_company",
        "language",
        "notes",
        mode="before",
    )
    @classmethod
    def _no_empty_strings(cls, value: object) -> object:
        return _require_non_empty(value)


class SalesWorkflowResponse(BaseModel):
    """Aggregated result of the end-to-end sales workflow.

    Combines the output of every step so a human reviewer sees the full
    picture in one place. This is an analysis-and-draft summary only: no
    email is sent, no contact is made, and no meeting is booked by this
    workflow — ``human_review_required`` is always ``True``.
    """

    workflow_id: str = Field(description="Unique identifier for this workflow run.")
    status: str = Field(description="'completed' once every step has succeeded.")
    company_name: str = Field(description="Company the workflow was run for.")
    lead_research: LeadResearchResponse = Field(
        description="Output of the Lead Research step."
    )
    company_intelligence: CompanyIntelligenceResponse = Field(
        description="Output of the Company Intelligence step."
    )
    personalization: PersonalizationResponse = Field(
        description="Output of the Personalization step."
    )
    email_draft: EmailDraftResponse = Field(
        description="Output of the Email Draft step."
    )
    human_review_required: bool = Field(
        default=True,
        description="Always true — every workflow output requires human review.",
    )
    review_checklist: list[str] = Field(
        default_factory=list,
        description="Concrete items a human should check before acting on this output.",
    )
    compliance_notes: list[str] = Field(
        default_factory=list,
        description="States clearly that nothing was sent or contacted automatically.",
    )
    missing_information: list[str] = Field(
        default_factory=list,
        description="Missing information collected across all workflow steps.",
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence aggregated across all workflow steps, from 0.0 to 1.0.",
    )
    crm_company_id: str | None = Field(
        default=None,
        description="Id of the CRM Company this run was linked to, if synced.",
    )
    crm_lead_id: str | None = Field(
        default=None,
        description="Id of the CRM Lead this run was linked to, if synced.",
    )
    crm_email_draft_id: str | None = Field(
        default=None,
        description="Id of the saved CRM email draft for this run, if synced.",
    )
