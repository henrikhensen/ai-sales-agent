from datetime import timedelta

import pytest

from backend.shared.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password_returns_a_bcrypt_hash_not_the_plain_value():
    hashed = hash_password("supersecret123")
    assert hashed != "supersecret123"
    assert hashed.startswith("$2b$")


def test_hash_password_is_not_deterministic():
    # bcrypt salts each hash, so hashing the same password twice differs.
    first = hash_password("supersecret123")
    second = hash_password("supersecret123")
    assert first != second


def test_verify_password_accepts_the_correct_password():
    hashed = hash_password("supersecret123")
    assert verify_password("supersecret123", hashed) is True


def test_verify_password_rejects_the_wrong_password():
    hashed = hash_password("supersecret123")
    assert verify_password("wrong-password", hashed) is False


def test_create_access_token_encodes_subject_and_expiry():
    token = create_access_token(subject="user-123")
    payload = decode_access_token(token)
    assert payload["sub"] == "user-123"
    assert "exp" in payload
    assert "iat" in payload


def test_decode_access_token_rejects_garbage_token():
    with pytest.raises(InvalidTokenError):
        decode_access_token("not-a-real-token")


def test_decode_access_token_rejects_expired_token():
    token = create_access_token(subject="user-123", expires_delta=timedelta(seconds=-1))
    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_create_access_token_respects_custom_expires_delta():
    token = create_access_token(subject="user-123", expires_delta=timedelta(minutes=5))
    payload = decode_access_token(token)
    assert payload["exp"] - payload["iat"] == 300
