"""API request/response schemas for persisted workflow runs.

These map the :class:`WorkflowRun` domain entity onto the wire format for
``/api/v1/workflows/sales/runs*``. Separate from
:mod:`backend.application.workflows.schemas`, which holds the sales
workflow's own orchestration request/response, not its persisted-history view.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.domain.enums import WorkflowReviewStatus


class WorkflowRunSummary(BaseModel):
    """Compact view of a persisted workflow run, for list endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_name: str
    workflow_type: str
    status: str
    review_status: WorkflowReviewStatus
    confidence_score: float | None
    company_id: UUID | None = None
    lead_id: UUID | None = None
    contact_id: UUID | None = None
    email_draft_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class WorkflowRunDetail(WorkflowRunSummary):
    """Full view of a persisted workflow run, including input and result."""

    input_payload: dict[str, Any] = Field(
        description="The original SalesWorkflowRequest, as submitted."
    )
    result_payload: dict[str, Any] = Field(
        description="The full SalesWorkflowResponse produced for this run."
    )
    missing_information: list[str]
    compliance_notes: list[str]


class WorkflowRunListResponse(BaseModel):
    """Paginated list of workflow run summaries."""

    items: list[WorkflowRunSummary]
    limit: int
    offset: int


class UpdateWorkflowReviewStatusRequest(BaseModel):
    """Request body for changing a workflow run's review status.

    Note: setting this to ``approved`` means the run has been internally
    reviewed — it never triggers sending an email or making contact. Any
    actual outreach remains a separate, manual step outside this system.
    """

    review_status: WorkflowReviewStatus


class UpdateWorkflowReviewStatusResponse(WorkflowRunDetail):
    """Full workflow run detail returned after a review-status change."""


class WorkflowCrmLinksResponse(BaseModel):
    """CRM entity ids a persisted workflow run was linked to.

    Read-only: this response never triggers or represents sending an email,
    contacting anyone, or booking a meeting.
    """

    workflow_id: UUID
    company_id: UUID | None
    lead_id: UUID | None
    contact_id: UUID | None
    email_draft_id: UUID | None
