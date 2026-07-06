"""Auth dependencies: resolve the current user from a Bearer access token,
and gate endpoints by role (Role-Based Access Control).

Uses :class:`fastapi.security.HTTPBearer` rather than
``OAuth2PasswordBearer``: login in this system is a plain JSON endpoint
(``POST /api/v1/auth/login``), not an OAuth2 password-grant form, so a
bearer scheme that just extracts ``Authorization: Bearer <token>`` (and
lets Swagger's "Authorize" dialog accept a pasted token) is the correct
fit — no external identity provider, no OAuth in this phase.

Auth is introduced step by step: read-only agent endpoints stay public in
this phase (see ``backend/api/v1/routes/agents.py``) so the still-public
Agents pages in the frontend keep working, while CRM, Workflows, Reviews,
and User-management endpoints now require an authenticated, active user —
and several require a specific role. A missing/invalid token always yields
401; an authenticated user lacking the right role/status yields 403. No
role or permission check here ever sends an email, contacts anyone, or
triggers any outreach — this module only ever grants or denies access to
read/write internal data.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.api.v1.dependencies import AuthServiceDep
from backend.domain.entities.user import User
from backend.domain.enums import UserRole
from backend.domain.exceptions import UserNotFoundError
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


def _require_one_of(current_user: User, *roles: UserRole) -> User:
    if current_user.is_superuser or current_user.role in roles:
        return current_user
    raise HTTPException(
        status.HTTP_403_FORBIDDEN, detail="Insufficient role privileges"
    )


def require_roles(*roles: UserRole):
    """Build a dependency requiring the authenticated, active user to have
    one of ``roles`` (or be a superuser).

    Use this directly for one-off combinations; for the common combinations
    used across this API, prefer the ready-made
    :data:`require_reviewer_or_admin` / :data:`require_sales_or_admin` /
    :data:`require_sales_reviewer_or_admin` dependencies below so every
    route spells the same allowed-roles set the same way. The returned
    callable performs the check itself (rather than delegating to a nested
    ``Depends``), so it behaves identically whether FastAPI injects it or
    it is called directly, e.g. in a unit test.
    """

    async def _check_roles(current_user: RequireActiveUserDep) -> User:
        return _require_one_of(current_user, *roles)

    return _check_roles


async def require_reviewer_or_admin(current_user: RequireActiveUserDep) -> User:
    """Require the authenticated, active user to be a reviewer or admin."""
    return _require_one_of(current_user, UserRole.ADMIN, UserRole.REVIEWER)


RequireReviewerOrAdminDep = Annotated[User, Depends(require_reviewer_or_admin)]


async def require_sales_or_admin(current_user: RequireActiveUserDep) -> User:
    """Require the authenticated, active user to be sales or admin."""
    return _require_one_of(current_user, UserRole.ADMIN, UserRole.SALES)


RequireSalesOrAdminDep = Annotated[User, Depends(require_sales_or_admin)]


async def require_sales_reviewer_or_admin(current_user: RequireActiveUserDep) -> User:
    """Require the authenticated, active user to have any known role.

    In practice this allows any active account — admin, reviewer, or sales
    — while still enforcing "authenticated and active". Used on endpoints
    every role may use (e.g. reading Workflow History or CRM data).
    """
    return _require_one_of(
        current_user, UserRole.ADMIN, UserRole.REVIEWER, UserRole.SALES
    )


RequireSalesReviewerOrAdminDep = Annotated[
    User, Depends(require_sales_reviewer_or_admin)
]
