from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from backend.domain.enums import LeadSource, LeadStatus


@dataclass
class Lead:
    """A potential sales opportunity associated with a company."""

    company_id: UUID
    source: LeadSource
    status: LeadStatus = LeadStatus.NEW
    score: int = 0
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
