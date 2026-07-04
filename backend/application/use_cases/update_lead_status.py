from dataclasses import dataclass
from uuid import UUID

from backend.domain.entities.lead import Lead
from backend.domain.enums import LeadStatus
from backend.domain.exceptions import LeadNotFoundError
from backend.domain.repositories.lead_repository import LeadRepository


@dataclass(frozen=True)
class UpdateLeadStatusCommand:
    """Input for changing a lead's status."""

    lead_id: UUID
    status: LeadStatus


class UpdateLeadStatusUseCase:
    """Transition an existing lead to a new status."""

    def __init__(self, lead_repository: LeadRepository) -> None:
        self._leads = lead_repository

    async def execute(self, command: UpdateLeadStatusCommand) -> Lead:
        lead = await self._leads.get(command.lead_id)
        if lead is None:
            raise LeadNotFoundError(command.lead_id)

        lead.status = command.status
        updated = await self._leads.update(lead)
        if updated is None:
            raise LeadNotFoundError(command.lead_id)
        return updated
