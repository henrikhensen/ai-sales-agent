import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.database.base import Base, TimestampMixin, UUIDMixin


class DoNotContactEntryModel(UUIDMixin, TimestampMixin, Base):
    """Do-not-contact / opt-out table.

    At least one of ``email``, ``domain``, or ``company_name`` is always set
    (enforced by the application service, not a DB constraint — consistent
    with how this project validates elsewhere). ``email`` and ``domain`` are
    always stored lowercase; ``company_name`` keeps the caller's original
    casing while ``company_name_normalized`` is the lowercase,
    whitespace-collapsed form used for matching.
    """

    __tablename__ = "do_not_contact_entries"

    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    company_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    company_name_normalized: Mapped[str | None] = mapped_column(
        String(200), nullable=True, index=True
    )
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False, default="manual")
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
