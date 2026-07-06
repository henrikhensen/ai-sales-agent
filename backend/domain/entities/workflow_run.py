from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from backend.domain.enums import WorkflowReviewStatus


@dataclass
class WorkflowRun:
    """A persisted record of one executed workflow run (e.g. the sales workflow).

    Captures the full input and result so a human can review the run later.
    ``review_status`` tracks only internal review — even ``APPROVED`` never
    means an email was sent or contact was made. Sending or making contact
    remains a fully separate, manual step outside this system.
    """

    company_name: str
    status: str
    input_payload: dict[str, Any]
    result_payload: dict[str, Any]
    workflow_type: str = "sales"
    review_status: WorkflowReviewStatus = WorkflowReviewStatus.NEEDS_REVIEW
    confidence_score: float | None = None
    missing_information: list[str] = field(default_factory=list)
    compliance_notes: list[str] = field(default_factory=list)
    company_id: UUID | None = None
    lead_id: UUID | None = None
    contact_id: UUID | None = None
    email_draft_id: UUID | None = None
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
