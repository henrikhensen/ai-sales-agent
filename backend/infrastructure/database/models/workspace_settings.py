from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.database.base import Base, TimestampMixin, UUIDMixin


class WorkspaceSettingsModel(UUIDMixin, TimestampMixin, Base):
    """Single-tenant workspace settings singleton — declared admin intent
    only, never a substitute for environment provider configuration."""

    __tablename__ = "workspace_settings"

    workspace_name: Mapped[str] = mapped_column(String(200), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    company_website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    default_language: Mapped[str] = mapped_column(
        String(10), nullable=False, default="de"
    )
    default_tone: Mapped[str] = mapped_column(
        String(50), nullable=False, default="professional"
    )
    default_icp_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("icp_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    default_offer_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("offer_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    require_human_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    require_do_not_contact_check: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    allow_real_llm_calls: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    allow_real_email_drafts: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    allow_real_reply_reads: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    allow_real_dispatch: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    dispatch_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft_only"
    )
    data_retention_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    anonymize_instead_of_delete: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    data_export_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    data_subject_requests_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
