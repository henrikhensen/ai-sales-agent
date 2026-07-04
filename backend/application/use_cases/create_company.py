from dataclasses import dataclass

from backend.domain.entities.company import Company
from backend.domain.repositories.company_repository import CompanyRepository


@dataclass(frozen=True)
class CreateCompanyCommand:
    """Input for creating a company."""

    name: str
    domain: str | None = None
    industry: str | None = None


class CreateCompanyUseCase:
    """Create a new company."""

    def __init__(self, company_repository: CompanyRepository) -> None:
        self._companies = company_repository

    async def execute(self, command: CreateCompanyCommand) -> Company:
        company = Company(
            name=command.name,
            domain=command.domain,
            industry=command.industry,
        )
        return await self._companies.create(company)
