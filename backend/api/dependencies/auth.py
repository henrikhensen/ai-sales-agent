"""Auth dependencies: resolve the current user from a Bearer access token.

Uses :class:`fastapi.security.HTTPBearer` rather than
``OAuth2PasswordBearer``: login in this system is a plain JSON endpoint
(``POST /api/v1/auth/login``), not an OAuth2 password-grant form, so a
bearer scheme that just extracts ``Authorization: Bearer <token>`` (and
lets Swagger's "Authorize" dialog accept a pasted token) is the correct
fit — no external identity provider, no OAuth in this phase.

Existing public endpoints are deliberately NOT hard-protected in this
phase, so the frontend keeps working unchanged. Only the new
``/api/v1/auth/me`` and ``/api/v1/users`` endpoints require a valid token.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.api.v1.dependencies import AuthServiceDep
from backend.application.auth.auth_service import AuthService
from backend.domain.entities.user import User
from backend.domain.enums import UserRole
from backend.domain.exceptions import UserNotFoundError
from backend.infrastructure.database.session import async_session_factory
from backend.infrastructure.repositories.user import SQLAlchemyUserRepository
from backend.shared.security import InvalidTokenError, decode_access_token

_bearer_scheme = HTTPBearer(auto_error=False)

_UNAUTHENTICATED = HTTPException(
    status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)
_INVALID_TOKEN = HTTPException(
    status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired access token",
    headers={"WWW-Authenticate": "Bearer"},
)


def _subject_to_user_id(token: str) -> UUID:
    try:
        payload = decode_access_token(token)
        return UUID(payload["sub"])
    except (InvalidTokenError, KeyError, ValueError) as exc:
        raise _INVALID_TOKEN from exc


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    auth_service: AuthServiceDep,
) -> User:
    """Resolve the authenticated user from a Bearer access token.

    Raises 401 if the header is missing, the token is invalid/expired, or
    the user it refers to no longer exists.
    """
    if credentials is None:
        raise _UNAUTHENTICATED

    user_id = _subject_to_user_id(credentials.credentials)
    try:
        return await auth_service.get_current_user(user_id)
    except UserNotFoundError as exc:
        raise _INVALID_TOKEN from exc


CurrentUserDep = Annotated[User, Depends(get_current_user)]


async def require_active_user(current_user: CurrentUserDep) -> User:
    """Require the authenticated user's account to still be active."""
    if not current_user.is_active:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="User account is deactivated"
        )
    return current_user


RequireActiveUserDep = Annotated[User, Depends(require_active_user)]


async def require_admin_user(current_user: RequireActiveUserDep) -> User:
    """Require the authenticated, active user to be an admin (or superuser)."""
    if current_user.role != UserRole.ADMIN and not current_user.is_superuser:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )
    return current_user


RequireAdminUserDep = Annotated[User, Depends(require_admin_user)]


async def get_optional_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> User | None:
    """Best-effort current-user resolution: returns None instead of raising.

    Used only to let already-authenticated callers default a reviewer name
    (see the reviews routes) — never required, never breaks a request.

    Deliberately does not depend on :data:`AuthServiceDep`/``SessionDep``:
    those would build a real database session for every request regardless
    of whether a token was sent, which would break existing review-endpoint
    tests and callers that never authenticate. A session is only opened
    here when a Bearer token is actually present.
    """
    if credentials is None:
        return None
    try:
        user_id = _subject_to_user_id(credentials.credentials)
    except HTTPException:
        return None

    async with async_session_factory() as session:
        auth_service = AuthService(SQLAlchemyUserRepository(session))
        try:
            return await auth_service.get_current_user(user_id)
        except UserNotFoundError:
            return None


OptionalCurrentUserDep = Annotated[User | None, Depends(get_optional_current_user)]
