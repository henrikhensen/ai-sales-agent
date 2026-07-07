from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.database.base import Base, TimestampMixin, UUIDMixin


class ICPProfileModel(UUIDMixin, TimestampMixin, Base):
    """An Ideal Customer Profile used to score companies/leads for fit.

    Scoring is read-only analysis over existing data — this table never
    represents that any outreach happened by itself.
    """

    __tablename__ = "icp_profiles"

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_industries: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    excluded_industries: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    target_company_sizes: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    target_locations: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    target_languages: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    target_keywords: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    negative_keywords: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    target_pain_points: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    buying_triggers: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    required_signals: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    excluded_signals: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    buyer_personas: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    preferred_titles: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    excluded_titles: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    minimum_fit_score: Mapped[int] = mapped_column(
        Integer, nullable=False, default=70
    )
    scoring_weights: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
