from abc import ABC
from typing import Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from backend.infrastructure.database.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(ABC, Generic[ModelType]):
    """Abstract base repository.

    Provides shared persistence infrastructure (a session and the bound model
    type) for concrete repositories. Query and command methods are added by
    subclasses in later phases; no business logic lives here.
    """

    model: type[ModelType]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        """The active database session for this repository."""
        return self._session
