from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Company:
    """A business organisation that leads and contacts belong to."""

    name: str
    domain: str | None = None
    industry: str | None = None
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
