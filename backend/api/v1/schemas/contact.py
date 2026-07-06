from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ContactResponse(BaseModel):
    """Serialized contact returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    first_name: str
    last_name: str
    email: str | None
    phone: str | None
    created_at: datetime
    updated_at: datetime
