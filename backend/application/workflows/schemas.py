"""Input and output schemas for the end-to-end Sales Workflow.

``SalesWorkflowRequest`` is the validated task input (also used as the API
request body). ``SalesWorkflowResponse`` aggregates the outputs of every
step (also used as the API response body). This is an application-layer
orchestration DTO, not an agent I/O pair — it does not extend
:mod:`backend.agents.schemas`, since no single LLM call produces it.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator, model_validator

from backend.agents.company_intelligence.schemas import CompanyIntelligenceResponse
from backend.agents.email_draft.schemas import EmailDraftResponse, EmailTone
from backend.agents.lead_research.schemas import LeadResearchResponse
from backend.agents.personalization.schemas import PersonalizationResponse
from backend.application.compliance.schemas import DoNotContactCheckResponse
from backend.application.sales_strategy.schemas import FitLevel


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
    recipient_email: EmailStr | None = Field(
        default=None,
        description=(
            "Email of the recipient, if known. Checked against the "
            "do-not-contact list before an email draft is created — a "
            "matching entry blocks draft creation for this run."
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
    use_website_research: bool = Field(
        default=False,
        description=(
            "Reserved for a future phase: whether the workflow should fetch "
            "website_url and use the extracted text as additional context. "
            "Has no effect yet — no website is fetched in this phase, "
            "regardless of this flag."
        ),
    )
    website_research_max_pages: int | None = Field(
        default=1,
        ge=1,
        le=3,
        description=(
            "Reserved for a future same-domain crawl once website research is "
            "wired into the workflow. Has no effect yet."
        ),
    )
    icp_profile_id: UUID | None = Field(
        default=None,
        description=(
            "Optional Ideal Customer Profile to score this company/lead "
            "against. The workflow runs identically without it — this only "
            "adds an ICP fit assessment to the response and history."
        ),
    )
    offer_profile_id: UUID | None = Field(
        default=None,
        description=(
            "Optional Offer profile to steer Personalization and the Email "
            "Draft towards. The workflow runs identically without it — "
            "product_or_service_offered above is still required either way."
        ),
    )

    @model_validator(mode="after")
    def _require_website_url_when_research_requested(self) -> "SalesWorkflowRequest":
        if self.use_website_research and self.website_url is None:
            raise ValueError(
                "website_url is required when use_website_research is true"
            )
        return self

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

    ``personalization`` and ``email_draft`` are ``None`` when
    ``do_not_contact_block.is_blocked`` is ``True``: Lead Research and
    Company Intelligence still run, but outreach preparation stops there —
    see ``backend.application.workflows.sales_workflow.SalesWorkflowService``.
    """

    workflow_id: str = Field(description="Unique identifier for this workflow run.")
    status: str = Field(
        description=(
            "'completed' once every step has succeeded, or 'blocked' if a "
            "do-not-contact match stopped outreach preparation."
        )
    )
    company_name: str = Field(description="Company the workflow was run for.")
    lead_research: LeadResearchResponse = Field(
        description="Output of the Lead Research step."
    )
    company_intelligence: CompanyIntelligenceResponse = Field(
        description="Output of the Company Intelligence step."
    )
    personalization: PersonalizationResponse | None = Field(
        default=None,
        description=(
            "Output of the Personalization step, or None if skipped "
            "because of an active do-not-contact match."
        ),
    )
    email_draft: EmailDraftResponse | None = Field(
        default=None,
        description=(
            "Output of the Email Draft step, or None if skipped because of "
            "an active do-not-contact match — no draft is created in that "
            "case."
        ),
    )
    do_not_contact_block: DoNotContactCheckResponse | None = Field(
        default=None,
        description=(
            "Set when the recipient email, company domain, or company name "
            "matched an active do-not-contact entry. Outreach preparation "
            "(Personalization, Email Draft) is skipped in that case; "
            "Lead Research and Company Intelligence still complete."
        ),
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
    website_research_used: bool = Field(
        default=False,
        description=(
            "Reserved for a future phase: whether website research actually "
            "ran for this workflow. Always false in this phase — no website "
            "is fetched yet, regardless of what the request requested."
        ),
    )
    website_research: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Reserved for a future phase: the extracted website research "
            "result (see WebsiteResearchResponse), once wired into this "
            "workflow. Always null in this phase."
        ),
    )
    website_research_warnings: list[str] = Field(
        default_factory=list,
        description=(
            "Reserved for a future phase: non-fatal notices from website "
            "research (e.g. truncation). Always empty in this phase."
        ),
    )
    icp_profile_id: str | None = Field(
        default=None,
        description="Echoed from the request if an ICP profile was used.",
    )
    icp_fit_score: int | None = Field(
        default=None, description="Fit score (0-100) against the selected ICP, if any."
    )
    icp_fit_level: FitLevel | None = Field(
        default=None, description="Fit level against the selected ICP, if any."
    )
    icp_fit_summary: str | None = Field(
        default=None,
        description="The ICP fit check's recommendation text, if an ICP was used.",
    )
    icp_warnings: list[str] = Field(
        default_factory=list,
        description="Warnings from the ICP fit check (e.g. missing data), if any.",
    )
    offer_profile_id: str | None = Field(
        default=None,
        description="Echoed from the request if an Offer profile was used.",
    )
    offer_summary: str | None = Field(
        default=None,
        description="The offer's positioning summary, if an Offer profile was used.",
    )
    offer_warnings: list[str] = Field(
        default_factory=list,
        description=(
            "Warnings from the offer (e.g. missing proof points), if an "
            "Offer profile was used."
        ),
    )
    workflow_quality_score: int | None = Field(
        default=None,
        description=(
            "Rule-based quality score (0-100) for this workflow run, if "
            "QUALITY_AUTO_SCORE_WORKFLOWS is enabled. Decision support "
            "only, never a guarantee."
        ),
    )
    email_draft_quality_score: int | None = Field(
        default=None,
        description=(
            "Rule-based quality score (0-100) for the produced email "
            "draft, if any and if QUALITY_AUTO_SCORE_DRAFTS is enabled."
        ),
    )
    quality_warnings: list[str] = Field(
        default_factory=list,
        description=(
            "Non-fatal notices from quality scoring (e.g. a scoring "
            "failure) — quality scoring never fails the workflow itself."
        ),
    )
