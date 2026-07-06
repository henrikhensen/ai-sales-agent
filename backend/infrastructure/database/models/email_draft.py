from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.domain.enums import EmailDraftReviewStatus
from backend.infrastructure.database.base import Base, TimestampMixin, UUIDMixin


class EmailDraftModel(UUIDMixin, TimestampMixin, Base):
    """Persisted email draft produced by a sales workflow run.

    Stores a draft only: no column on this table ever represents that an
    email was sent, scheduled, or that contact was made.
    """

    __tablename__ = "email_drafts"

    company_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Deliberately not a foreign key: `workflow_runs` also stores an optional
    # `email_draft_id` pointing back here, so a real FK constraint in both
    # directions would create a circular dependency between the two tables.
    workflow_run_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True
    )
    subject_lines: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    email_body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")

    review_status: Mapped[EmailDraftReviewStatus] = mapped_column(
        SAEnum(EmailDraftReviewStatus, name="email_draft_review_status"),
        nullable=False,
        default=EmailDraftReviewStatus.NEEDS_REVIEW,
        index=True,
    )
    reviewer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
