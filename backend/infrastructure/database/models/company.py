from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.infrastructure.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.infrastructure.database.models.contact import ContactModel
    from backend.infrastructure.database.models.lead import LeadModel


class CompanyModel(UUIDMixin, TimestampMixin, Base):
    """Company table. One company has many leads and many contacts."""

    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)

    leads: Mapped[list["LeadModel"]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
    )
    contacts: Mapped[list["ContactModel"]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
    )
