from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.domain.enums import LeadSource, LeadStatus, PipelineStatus
from backend.infrastructure.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.infrastructure.database.models.company import CompanyModel
    from backend.infrastructure.database.models.interaction import InteractionModel


class LeadModel(UUIDMixin, TimestampMixin, Base):
    """Lead table. Belongs to one company and has many interactions."""

    __tablename__ = "leads"

    company_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source: Mapped[LeadSource] = mapped_column(
        SAEnum(LeadSource, name="lead_source"),
        nullable=False,
    )
    status: Mapped[LeadStatus] = mapped_column(
        SAEnum(LeadStatus, name="lead_status"),
        nullable=False,
        default=LeadStatus.NEW,
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pipeline_status: Mapped[PipelineStatus] = mapped_column(
        SAEnum(PipelineStatus, name="lead_pipeline_status"),
        nullable=False,
        default=PipelineStatus.NEW,
        index=True,
    )
    pipeline_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    company: Mapped["CompanyModel"] = relationship(back_populates="leads")
    interactions: Mapped[list["InteractionModel"]] = relationship(
        back_populates="lead",
        cascade="all, delete-orphan",
    )
