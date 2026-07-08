from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class OutreachCampaign:
    """A reusable, named container that collects qualified leads into a
    prioritized queue for a future outreach effort.

    Creating or activating a campaign never contacts anyone by itself —
    'active' only means its queue may be built/prepared; an actual Sales
    Workflow run or email draft always remains a separate, human-triggered
    action on individual queue items.
    """

    name: str
    description: str | None = None
    icp_profile_id: UUID | None = None
    offer_profile_id: UUID | None = None
    target_language: str | None = None
    tone: str | None = None
    min_qualification_score: int = 70
    allowed_qualification_levels: list[str] = field(default_factory=list)
    excluded_statuses: list[str] = field(default_factory=list)
    max_queue_items: int = 25
    status: str = "draft"
    created_by_user_id: UUID | None = None
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
