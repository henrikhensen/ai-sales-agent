from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class LeadDiscoveryRun:
    """A guided "Lead Finder" run: given a target customer, region, and
    offer, finds candidate companies, analyzes their public websites,
    scores fit against ICP/Offer, and — only as a separate, explicit
    follow-up action — prepares (never sends) an email draft for the
    qualified ones.

    This never sends anything and never contacts anyone on its own; it is
    a thin orchestrator over the existing Lead Sourcing, Lead
    Qualification, Outreach Queue, and Sales Workflow services
    (``lead_sourcing_campaign_id``/``lead_sourcing_run_id``/
    ``outreach_campaign_id`` link to the underlying records those
    services own). ``mode`` only ever governs whether real LLM output may
    be used — it never enables sending and never bypasses Do-not-contact
    or Human Review.
    """

    name: str
    target_customer: str
    region: str | None = None
    offer_profile_id: UUID | None = None
    icp_profile_id: UUID | None = None
    requested_count: int = 10
    min_score: int = 50
    mode: str = "mock"
    status: str = "pending"
    lead_sourcing_campaign_id: UUID | None = None
    lead_sourcing_run_id: UUID | None = None
    outreach_campaign_id: UUID | None = None
    found_candidates: int = 0
    analyzed_websites: int = 0
    qualified_leads: int = 0
    rejected_leads: int = 0
    created_drafts: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    created_by_user_id: UUID | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
