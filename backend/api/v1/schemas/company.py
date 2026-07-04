from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CompanyCreate(BaseModel):
    """Request body for creating a company."""

    name: str = Field(min_length=1, max_length=255)
    domain: str | None = Field(default=None, max_length=255)
    industry: str | None = Field(default=None, max_length=255)


class CompanyResponse(BaseModel):
    """Serialized company returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    domain: str | None
    industry: str | None
    created_at: datetime
    updated_at: datetime
