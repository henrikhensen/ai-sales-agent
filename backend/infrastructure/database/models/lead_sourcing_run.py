from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.database.base import Base, TimestampMixin, UUIDMixin


class LeadSourcingRunModel(UUIDMixin, TimestampMixin, Base):
    """One execution of a lead sourcing campaign. Never sends anything and
    never creates a CRM Company/Lead by itself."""

    __tablename__ = "lead_sourcing_runs"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("lead_sourcing_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="running", index=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="mock")
    started_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_candidates_found: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    total_candidates_saved: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    total_duplicates: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_blocked_by_do_not_contact: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    total_errors: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warnings: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
