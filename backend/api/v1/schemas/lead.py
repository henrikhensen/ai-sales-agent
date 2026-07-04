from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.domain.enums import LeadSource, LeadStatus


class LeadCreate(BaseModel):
    """Request body for creating a lead."""

    company_id: UUID
    source: LeadSource
    score: int = Field(default=0, ge=0, le=100)


class LeadStatusUpdate(BaseModel):
    """Request body for changing a lead's status."""

    status: LeadStatus


class LeadResponse(BaseModel):
    """Serialized lead returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    source: LeadSource
    status: LeadStatus
    score: int
    created_at: datetime
    updated_at: datetime
