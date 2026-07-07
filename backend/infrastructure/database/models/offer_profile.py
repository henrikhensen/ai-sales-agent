from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.database.base import Base, TimestampMixin, UUIDMixin


class OfferProfileModel(UUIDMixin, TimestampMixin, Base):
    """A definition of what is being sold — value proposition, benefits,
    proof, and guardrails (forbidden_claims, required_disclaimers) against
    overselling. Never represents that anything was sent."""

    __tablename__ = "offer_profiles"

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    main_value_proposition: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    pain_points_solved: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    key_benefits: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    differentiators: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    proof_points: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    case_study_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    pricing_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    call_to_action: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tone: Mapped[str] = mapped_column(String(50), nullable=False, default="professional")
    language: Mapped[str] = mapped_column(String(50), nullable=False, default="de")
    forbidden_claims: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    required_disclaimers: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
