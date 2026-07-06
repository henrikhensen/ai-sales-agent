"""Symmetric encryption for OAuth tokens at rest.

Uses Fernet (AES-128-CBC + HMAC) keyed by ``EMAIL_TOKEN_ENCRYPTION_KEY``.
Never logs the encryption key, a plaintext token, or ciphertext.
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from backend.infrastructure.email_integration.base import EmailIntegrationConfigError


def _derive_fernet_key(raw_key: str) -> bytes:
    """Derive a valid 32-byte urlsafe-base64 Fernet key from any input string.

    Lets ``EMAIL_TOKEN_ENCRYPTION_KEY`` be an arbitrary secret string rather
    than requiring the operator to generate a Fernet key in its exact
    encoded form.
    """
    digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


class TokenCipher:
    """Encrypts/decrypts OAuth tokens for storage in
    :class:`~backend.domain.entities.email_provider_connection.EmailProviderConnection`.
    """

    def __init__(self, raw_key: str | None) -> None:
        if not raw_key:
            raise EmailIntegrationConfigError(
                "EMAIL_TOKEN_ENCRYPTION_KEY is not set; cannot store OAuth "
                "tokens securely."
            )
        self._fernet = Fernet(_derive_fernet_key(raw_key))

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise EmailIntegrationConfigError(
                "Stored OAuth token could not be decrypted — "
                "EMAIL_TOKEN_ENCRYPTION_KEY may have changed."
            ) from exc
