"""Local authentication: registration, login, and current-user lookup.

``AuthService`` hashes passwords with bcrypt (never stores or logs a plain
password), verifies credentials, and issues signed JWT access tokens. There
is no external identity provider and no OAuth in this phase — everything
here is local to this backend. Nothing here sends an email or contacts
anyone.
"""

from __future__ import annotations

from uuid import UUID

from backend.domain.entities.user import User
from backend.domain.enums import UserRole
from backend.domain.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    UserNotFoundError,
)
from backend.domain.repositories.user_repository import UserRepository
from backend.shared.security import create_access_token, hash_password, verify_password


class AuthService:
    """Registers users, authenticates logins, and issues access tokens."""

    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def register(
        self,
        email: str,
        password: str,
        full_name: str | None = None,
        role: UserRole = UserRole.SALES,
    ) -> User:
        """Create a new local user account with a securely hashed password.

        Raises :class:`EmailAlreadyRegisteredError` if the email is taken.
        """
        normalized_email = email.strip().lower()
        existing = await self._users.get_by_email(normalized_email)
        if existing is not None:
            raise EmailAlreadyRegisteredError(normalized_email)

        user = User(
            email=normalized_email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role=role,
        )
        return await self._users.create(user)

    async def authenticate(self, email: str, password: str) -> User:
        """Verify email/password and return the matching user.

        Raises :class:`InvalidCredentialsError` for any mismatch (unknown
        email, wrong password, or a deactivated account) — deliberately
        without revealing which, so accounts cannot be enumerated.
        """
        normalized_email = email.strip().lower()
        user = await self._users.get_by_email(normalized_email)
        if user is None or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError()
        if not user.is_active:
            raise InvalidCredentialsError()
        return user

    async def login(self, email: str, password: str) -> str:
        """Authenticate and return a signed JWT access token."""
        user = await self.authenticate(email, password)
        return create_access_token(subject=str(user.id))

    async def get_current_user(self, user_id: UUID) -> User:
        """Load the user a valid access token's subject refers to.

        Raises :class:`UserNotFoundError` if the account no longer exists.
        """
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id)
        return user
