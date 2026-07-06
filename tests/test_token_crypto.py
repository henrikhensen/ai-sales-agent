"""Tests for OAuth token encryption at rest."""

import pytest

from backend.infrastructure.email_integration.base import EmailIntegrationConfigError
from backend.infrastructure.email_integration.token_crypto import TokenCipher


def test_encrypt_decrypt_roundtrip():
    cipher = TokenCipher("a-test-encryption-key")
    ciphertext = cipher.encrypt("super-secret-refresh-token")

    assert ciphertext != "super-secret-refresh-token"
    assert cipher.decrypt(ciphertext) == "super-secret-refresh-token"


def test_missing_key_raises_configuration_error():
    with pytest.raises(EmailIntegrationConfigError):
        TokenCipher(None)


def test_empty_key_raises_configuration_error():
    with pytest.raises(EmailIntegrationConfigError):
        TokenCipher("")


def test_decrypting_with_a_different_key_fails_cleanly():
    ciphertext = TokenCipher("key-one").encrypt("a-token")

    with pytest.raises(EmailIntegrationConfigError):
        TokenCipher("key-two").decrypt(ciphertext)
