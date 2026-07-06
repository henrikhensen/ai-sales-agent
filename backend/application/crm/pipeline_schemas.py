"""Input and output schemas for the CRM Pipeline board.

Groups leads by :class:`~backend.domain.enums.PipelineStatus` into columns.
Changing a lead's pipeline status is bookkeeping only — it never sends an
email or makes contact, and ``approved`` here means only that a human has
internally reviewed the lead's workflow run, never that anything was sent.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.domain.enums import PipelineStatus


class LeadPipelineSummary(BaseModel):
    """A single lead's pipeline-relevant fields, for display on the board."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    pipeline_status: PipelineStatus
    pipeline_updated_at: datetime | None
    score: int
    created_at: datetime
    updated_at: datetime


class PipelineColumn(BaseModel):
    """One pipeline stage and the leads currently in it."""

    pipeline_status: PipelineStatus
    leads: list[LeadPipelineSummary] = Field(default_factory=list)


class PipelineBoardResponse(BaseModel):
    """All leads grouped by pipeline stage, one column per known status."""

    columns: list[PipelineColumn] = Field(default_factory=list)


class UpdateLeadPipelineStatusRequest(BaseModel):
    """Request body for changing a lead's pipeline status."""

    pipeline_status: PipelineStatus


class UpdateLeadPipelineStatusResponse(BaseModel):
    """Result of changing a lead's pipeline status."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    pipeline_status: PipelineStatus
    pipeline_updated_at: datetime | None
