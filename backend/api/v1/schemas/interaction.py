from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from backend.domain.enums import InteractionType


class InteractionResponse(BaseModel):
    """Serialized interaction/activity returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_id: UUID
    type: InteractionType
    status: str | None
    notes: str | None
    occurred_at: datetime
    created_at: datetime
    updated_at: datetime
