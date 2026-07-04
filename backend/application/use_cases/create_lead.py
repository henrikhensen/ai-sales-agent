from dataclasses import dataclass
from uuid import UUID

from backend.domain.entities.lead import Lead
from backend.domain.enums import LeadSource, LeadStatus
from backend.domain.exceptions import CompanyNotFoundError
from backend.domain.repositories.company_repository import CompanyRepository
from backend.domain.repositories.lead_repository import LeadRepository


@dataclass(frozen=True)
class CreateLeadCommand:
    """Input for creating a lead."""

    company_id: UUID
    source: LeadSource
    score: int = 0


class CreateLeadUseCase:
    """Create a new lead for an existing company.

    Enforces the invariant that a lead must reference a company that exists
    and starts every new lead in the ``NEW`` status.
    """

    def __init__(
        self,
        lead_repository: LeadRepository,
        company_repository: CompanyRepository,
    ) -> None:
        self._leads = lead_repository
        self._companies = company_repository

    async def execute(self, command: CreateLeadCommand) -> Lead:
        company = await self._companies.get(command.company_id)
        if company is None:
            raise CompanyNotFoundError(command.company_id)

        lead = Lead(
            company_id=command.company_id,
            source=command.source,
            status=LeadStatus.NEW,
            score=command.score,
        )
        return await self._leads.create(lead)
