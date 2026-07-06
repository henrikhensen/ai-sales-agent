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


class UserNotFoundError(EntityNotFoundError):
    entity_name = "User"


class EmailAlreadyRegisteredError(DomainError):
    """Raised when registering with an email that already has an account."""

    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(f"A user with email '{email}' is already registered")


class InvalidCredentialsError(DomainError):
    """Raised on login when the email/password combination is invalid.

    Deliberately does not distinguish between "unknown email" and "wrong
    password" so a caller cannot enumerate registered accounts.
    """

    def __init__(self) -> None:
        super().__init__("Invalid email or password")
