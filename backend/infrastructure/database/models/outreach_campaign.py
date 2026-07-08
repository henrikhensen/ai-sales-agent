from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.database.base import Base, TimestampMixin, UUIDMixin


class OutreachCampaignModel(UUIDMixin, TimestampMixin, Base):
    """A reusable, named container that collects qualified leads into a
    prioritized queue. Never triggers outreach by itself."""

    __tablename__ = "outreach_campaigns"

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
    target_language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    min_qualification_score: Mapped[int] = mapped_column(
        Integer, nullable=False, default=70
    )
    allowed_qualification_levels: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    excluded_statuses: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    max_queue_items: Mapped[int] = mapped_column(Integer, nullable=False, default=25)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft", index=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
