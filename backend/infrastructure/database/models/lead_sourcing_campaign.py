from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.database.base import Base, TimestampMixin, UUIDMixin


class LeadSourcingCampaignModel(UUIDMixin, TimestampMixin, Base):
    """A reusable, named lead sourcing search definition. Never triggers
    outreach by itself — only ever produces candidates for human review."""

    __tablename__ = "lead_sourcing_campaigns"

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="mock")
    search_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_industry: Mapped[str | None] = mapped_column(String(200), nullable=True)
    target_location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    target_keywords: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    excluded_keywords: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    max_results: Mapped[int] = mapped_column(Integer, nullable=False, default=25)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="draft", index=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
