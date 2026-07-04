from backend.domain.entities.company import Company
from backend.domain.repositories.base import AbstractRepository


class CompanyRepository(AbstractRepository[Company]):
    """Persistence port for :class:`Company` entities."""
