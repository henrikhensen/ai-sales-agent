"""Local password hashing and JWT access tokens.

No external identity provider and no OAuth: passwords are hashed with
bcrypt (never stored or logged in plain text) and access tokens are signed
locally with ``JWT_SECRET_KEY``. This module has no knowledge of users or
HTTP — it is a pure utility layer used by the auth application service and
the auth dependencies.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.shared.config import get_settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class InvalidTokenError(Exception):
    """Raised when an access token is missing, malformed, or expired."""


def hash_password(password: str) -> str:
    """Return a bcrypt hash of ``password``. Never store the plain value."""
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if ``plain_password`` matches the given bcrypt hash."""
    return _pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token for ``subject`` (typically a user id).

    Expires after ``expires_delta``, or ``ACCESS_TOKEN_EXPIRE_MINUTES`` from
    settings if not given.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {"sub": subject, "iat": now, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT access token, returning its payload.

    Raises :class:`InvalidTokenError` if the token is missing, malformed,
    expired, or signed with a different key.
    """
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise InvalidTokenError("Invalid or expired access token") from exc
