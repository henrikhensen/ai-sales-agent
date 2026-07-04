from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from backend.domain.enums import InteractionType


@dataclass
class Interaction:
    """A recorded touchpoint (email, call, meeting, note) against a lead."""

    lead_id: UUID
    type: InteractionType
    notes: str | None = None
    occurred_at: datetime | None = None
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
