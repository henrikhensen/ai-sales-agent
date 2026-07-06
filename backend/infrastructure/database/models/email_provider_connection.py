import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.domain.enums import EmailProviderType
from backend.infrastructure.database.base import Base, TimestampMixin, UUIDMixin


class EmailProviderConnectionModel(UUIDMixin, TimestampMixin, Base):
    """One user's OAuth connection to a Gmail/Outlook account.

    Tokens are stored encrypted (Fernet, see
    ``backend.infrastructure.email_integration.token_crypto``) — this table
    never holds a plaintext token. Only ever grants draft-creation scope;
    there is no send capability anywhere in this integration.
    """

    __tablename__ = "email_provider_connections"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[EmailProviderType] = mapped_column(
        SAEnum(EmailProviderType, name="email_provider_type"),
        nullable=False,
    )
    encrypted_access_token: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(
        String(4000), nullable=True
    )
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scope: Mapped[str | None] = mapped_column(String(500), nullable=True)
    external_account_email: Mapped[str | None] = mapped_column(
        String(320), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
