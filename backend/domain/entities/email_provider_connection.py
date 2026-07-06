from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from backend.domain.enums import EmailProviderType


@dataclass
class EmailProviderConnection:
    """One user's OAuth connection to a Gmail/Outlook account.

    Tokens are stored encrypted at rest (see
    ``backend.infrastructure.email_integration.token_crypto``) — this
    entity only ever carries the encrypted ciphertext, never a plaintext
    token. A connection only ever grants draft-creation scope (e.g. Gmail's
    ``gmail.compose``, never ``gmail.send``); there is no send capability
    anywhere in this integration.
    """

    user_id: UUID
    provider: EmailProviderType
    encrypted_access_token: str | None = None
    encrypted_refresh_token: str | None = None
    token_expires_at: datetime | None = None
    scope: str | None = None
    external_account_email: str | None = None
    is_active: bool = True
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
