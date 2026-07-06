import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.domain.enums import EmailProviderType, ExternalDraftProviderStatus
from backend.infrastructure.database.base import Base, TimestampMixin, UUIDMixin


class ExternalEmailDraftModel(UUIDMixin, TimestampMixin, Base):
    """External (Gmail/Outlook/Mock) draft metadata table.

    One row per ``email_draft_id``. ``provider_status`` never takes a value
    meaning "sent" — see :class:`ExternalDraftProviderStatus`.
    """

    __tablename__ = "external_email_drafts"

    email_draft_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("email_drafts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    provider: Mapped[EmailProviderType] = mapped_column(
        SAEnum(EmailProviderType, name="email_provider_type"),
        nullable=False,
    )
    provider_status: Mapped[ExternalDraftProviderStatus] = mapped_column(
        SAEnum(ExternalDraftProviderStatus, name="external_draft_provider_status"),
        nullable=False,
        default=ExternalDraftProviderStatus.BLOCKED,
    )
    provider_draft_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_draft_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
