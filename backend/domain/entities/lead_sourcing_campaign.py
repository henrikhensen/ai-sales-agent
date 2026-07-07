from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class LeadSourcingCampaign:
    """A reusable, named lead sourcing search definition.

    Optionally references an ICP/Offer profile for scoring and context, but
    never triggers outreach by itself — a campaign only ever produces
    candidates for human review.
    """

    name: str
    description: str | None = None
    icp_profile_id: UUID | None = None
    offer_profile_id: UUID | None = None
    source_type: str = "mock"
    search_query: str | None = None
    target_industry: str | None = None
    target_location: str | None = None
    target_keywords: list[str] = field(default_factory=list)
    excluded_keywords: list[str] = field(default_factory=list)
    max_results: int = 25
    status: str = "draft"
    created_by_user_id: UUID | None = None
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
