from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.database.base import Base, TimestampMixin, UUIDMixin


class QualificationResultModel(UUIDMixin, TimestampMixin, Base):
    """The scored outcome for a single Lead Candidate or CRM Lead. A
    recommendation only — never a record of outreach happening."""

    __tablename__ = "qualification_results"

    qualification_run_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("qualification_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lead_candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("lead_candidates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
    )
    icp_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("icp_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    offer_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("offer_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    qualification_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    qualification_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="not_fit"
    )
    qualification_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="needs_review", index=True
    )
    priority_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fit_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    score_breakdown: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    positive_signals: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    negative_signals: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    missing_data: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    recommended_next_action: Mapped[str] = mapped_column(
        String(30), nullable=False, default="review_manually"
    )
    recommended_outreach_angle: Mapped[str | None] = mapped_column(Text, nullable=True)
    disqualification_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    compliance_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="clear"
    )
    do_not_contact_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="unknown"
    )
    duplicate_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="unknown"
    )
    pipeline_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
