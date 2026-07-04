from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Contact:
    """A person that works at a company."""

    company_id: UUID
    first_name: str
    last_name: str
    email: str | None = None
    phone: str | None = None
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
