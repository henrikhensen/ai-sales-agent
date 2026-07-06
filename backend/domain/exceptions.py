from uuid import UUID


class DomainError(Exception):
    """Base class for all domain-level errors."""


class EntityNotFoundError(DomainError):
    """Raised when a requested entity does not exist."""

    entity_name: str = "Entity"

    def __init__(self, entity_id: UUID) -> None:
        self.entity_id = entity_id
        super().__init__(f"{self.entity_name} with id '{entity_id}' was not found")


class CompanyNotFoundError(EntityNotFoundError):
    entity_name = "Company"


class LeadNotFoundError(EntityNotFoundError):
    entity_name = "Lead"


class ContactNotFoundError(EntityNotFoundError):
    entity_name = "Contact"


class WorkflowRunNotFoundError(EntityNotFoundError):
    entity_name = "WorkflowRun"


class EmailDraftNotFoundError(EntityNotFoundError):
    entity_name = "EmailDraft"
