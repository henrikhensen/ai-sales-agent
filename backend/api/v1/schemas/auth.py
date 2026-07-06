"""API request/response schemas for local authentication and user accounts.

No external identity provider, no OAuth: registration and login are fully
local to this backend. ``UserRead``/``CurrentUserResponse`` never include
the password hash.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from backend.domain.enums import UserRole


def _require_non_empty(value: object) -> object:
    """Reject empty / whitespace-only strings and trim surrounding whitespace.

    Non-string values are returned unchanged so normal type validation can
    still report a helpful error.
    """
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty or whitespace only")
        return stripped
    return value


class UserCreate(BaseModel):
    """Request body for registering a new local user account."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    full_name: str | None = Field(default=None, max_length=200)
    role: UserRole = UserRole.SALES

    @field_validator("full_name", mode="before")
    @classmethod
    def _no_blank_full_name(cls, value: object) -> object:
        return _require_non_empty(value)


class UserRead(BaseModel):
    """Serialized user account. Never includes the password hash."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str | None
    role: UserRole
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime


class UserListResponse(BaseModel):
    """A page of user accounts."""

    items: list[UserRead]


class LoginRequest(BaseModel):
    """Request body for logging in with email + password."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class TokenResponse(BaseModel):
    """A signed JWT access token. Use it as ``Authorization: Bearer <token>``."""

    access_token: str
    token_type: str = "bearer"


class CurrentUserResponse(UserRead):
    """The currently authenticated user, resolved from the access token."""
