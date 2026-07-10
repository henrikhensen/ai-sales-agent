from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.database.base import Base, TimestampMixin, UUIDMixin


class LeadDiscoveryRunModel(UUIDMixin, TimestampMixin, Base):
    """A guided "Lead Finder" run — thin orchestration bookkeeping over the
    existing Lead Sourcing, Lead Qualification, and Outreach Queue tables.
    Never a channel for sending anything."""

    __tablename__ = "lead_discovery_runs"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    target_customer: Mapped[str] = mapped_column(String(200), nullable=False)
    region: Mapped[str | None] = mapped_column(String(200), nullable=True)
    offer_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("offer_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    icp_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("icp_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    requested_count: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    min_score: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="mock")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    lead_sourcing_campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("lead_sourcing_campaigns.id", ondelete="SET NULL"),
        nullable=True,
    )
    lead_sourcing_run_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("lead_sourcing_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    outreach_campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("outreach_campaigns.id", ondelete="SET NULL"),
        nullable=True,
    )
    found_candidates: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    analyzed_websites: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    qualified_leads: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejected_leads: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_drafts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warnings: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    errors: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
