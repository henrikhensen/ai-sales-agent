from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.domain.enums import WorkflowReviewStatus
from backend.infrastructure.database.base import Base, TimestampMixin, UUIDMixin


class WorkflowRunModel(UUIDMixin, TimestampMixin, Base):
    """Persisted record of one executed workflow run (e.g. the sales workflow).

    Stores the full input and result as JSONB so a human can review exactly
    what was produced later. ``review_status`` is an internal review marker
    only — even ``approved`` never means an email was sent or contact made.
    """

    __tablename__ = "workflow_runs"

    company_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    workflow_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="sales", index=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    review_status: Mapped[WorkflowReviewStatus] = mapped_column(
        SAEnum(WorkflowReviewStatus, name="workflow_review_status"),
        nullable=False,
        default=WorkflowReviewStatus.NEEDS_REVIEW,
        index=True,
    )
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    result_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    missing_information: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    compliance_notes: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )

    company_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Deliberately not a foreign key: see the matching note on
    # `EmailDraftModel.workflow_run_id` for why this stays a plain column.
    email_draft_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True
    )
