from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.database.base import Base, TimestampMixin, UUIDMixin


class LeadCandidateModel(UUIDMixin, TimestampMixin, Base):
    """A potential customer found by a lead sourcing run, awaiting review.

    No column here ever represents that outreach happened — becoming a CRM
    Company/Lead requires an explicit human approval (see
    ``crm_company_id``/``crm_lead_id``).
    """

    __tablename__ = "lead_candidates"

    sourcing_run_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("lead_sourcing_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("lead_sourcing_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    company_domain: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    company_website_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(200), nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="mock")
    public_contact_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    contact_page_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    icp_fit_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    icp_fit_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    matched_signals: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    negative_signals: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    do_not_contact_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="unknown"
    )
    duplicate_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="unknown"
    )
    review_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    crm_company_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
    )
    crm_lead_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    warnings: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
