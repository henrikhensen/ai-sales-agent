from backend.domain.entities.contact import Contact
from backend.domain.repositories.base import AbstractRepository


class ContactRepository(AbstractRepository[Contact]):
    """Persistence port for :class:`Contact` entities."""
