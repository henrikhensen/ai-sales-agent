from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from backend.domain.enums import UserRole


@dataclass
class User:
    """A local user account.

    ``hashed_password`` is always a bcrypt hash — this entity never carries
    a plain-text password. Authentication is fully local: no external
    identity provider, no OAuth.
    """

    email: str
    hashed_password: str
    full_name: str | None = None
    role: UserRole = UserRole.SALES
    is_active: bool = True
    is_superuser: bool = False
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
