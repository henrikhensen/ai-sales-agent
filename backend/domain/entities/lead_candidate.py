from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class LeadCandidate:
    """A potential customer found by a lead sourcing run, awaiting review.

    Never a channel for outreach: there is no send capability anywhere
    near this entity. ``public_contact_email`` is only ever text already
    visible on a public page — never guessed, never a personal address
    unless explicitly allowed by configuration. Becomes a CRM Company/Lead
    only once a human approves it (see ``crm_company_id``/``crm_lead_id``).
    """

    sourcing_run_id: UUID
    campaign_id: UUID
    company_name: str | None = None
    company_domain: str | None = None
    company_website_url: str | None = None
    industry: str | None = None
    location: str | None = None
    description: str | None = None
    source_url: str | None = None
    source_name: str | None = None
    source_type: str = "mock"
    public_contact_email: str | None = None
    contact_page_url: str | None = None
    confidence_score: float | None = None
    icp_fit_score: int | None = None
    icp_fit_level: str | None = None
    matched_signals: list[str] = field(default_factory=list)
    negative_signals: list[str] = field(default_factory=list)
    # Deterministic, LLM-free heuristic over the same website research
    # result already fetched for ICP scoring — never a second fetch.
    # "poor" | "medium" | "good", or None if no website URL was known /
    # research could not be attempted at all.
    website_quality_level: str | None = None
    website_quality_reasons: list[str] = field(default_factory=list)
    # "unknown" (not yet checked) | "clear" | "blocked"
    do_not_contact_status: str = "unknown"
    # "unknown" (not yet checked) | "new" | "duplicate"
    duplicate_status: str = "unknown"
    # "pending" | "approved" | "rejected"
    review_status: str = "pending"
    crm_company_id: UUID | None = None
    crm_lead_id: UUID | None = None
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
