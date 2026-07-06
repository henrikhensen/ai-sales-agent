from abc import ABC, abstractmethod
from uuid import UUID

from backend.domain.entities.user import User


class UserRepository(ABC):
    """Persistence port for :class:`User` accounts.

    Deliberately narrower than :class:`AbstractRepository`: accounts are
    never hard-deleted through the API, only deactivated.
    """

    @abstractmethod
    async def create(self, user: User) -> User:
        """Persist a new user and return it with generated fields populated."""

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None:
        """Return the user with the given id, or None if it does not exist."""

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        """Return the user with this exact email, or None if it does not exist."""

    @abstractmethod
    async def list(self, limit: int = 100, offset: int = 0) -> list[User]:
        """Return a page of users, newest first."""

    @abstractmethod
    async def update(self, user: User) -> User | None:
        """Persist changes to an existing user, or None if it does not exist."""

    @abstractmethod
    async def deactivate(self, user_id: UUID) -> User | None:
        """Set a user's ``is_active`` to False. Returns None if not found."""
