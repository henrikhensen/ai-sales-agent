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


class DoNotContactEntryNotFoundError(EntityNotFoundError):
    entity_name = "DoNotContactEntry"


class DoNotContactBlockedError(DomainError):
    """Raised when an action is refused because of an active do-not-contact entry.

    Opt-out takes precedence over the Sales Workflow and Human Review: this
    is raised by review-approval paths (never by the Sales Workflow itself,
    which instead reports the block in its response so the run completes
    without crashing — see ``backend.application.workflows.sales_workflow``).
    """

    def __init__(self, matched_by: str, reason: str | None) -> None:
        self.matched_by = matched_by
        self.reason = reason
        super().__init__(
            f"Blocked by an active do-not-contact entry (matched by {matched_by})"
        )


class ExternalEmailDraftNotFoundError(EntityNotFoundError):
    entity_name = "ExternalEmailDraft"


class EmailIntegrationConfigurationError(DomainError):
    """Raised when a real email provider is requested but misconfigured
    (e.g. missing OAuth client id/secret, or no active connection)."""


class ExternalDraftBlockedError(DomainError):
    """Raised when external draft creation is refused before any provider
    call is made — do-not-contact match or missing review approval.

    ``reason`` is one of :class:`~backend.domain.enums.ExternalDraftBlockReason`.
    Opt-out and Human Review both take precedence over this integration;
    there is no override for either.
    """

    def __init__(self, reason: str, detail: str) -> None:
        self.reason = reason
        self.detail = detail
        super().__init__(detail)


class ExternalDraftProviderError(DomainError):
    """Raised when a real provider call was attempted and failed (rate
    limit, timeout, invalid/expired token, network error, other API
    error). Never carries the raw OAuth token or client secret."""


class ReplyNotFoundError(EntityNotFoundError):
    entity_name = "Reply"


class AuditLogNotFoundError(EntityNotFoundError):
    entity_name = "AuditLog"


class ICPProfileNotFoundError(EntityNotFoundError):
    entity_name = "ICPProfile"


class OfferProfileNotFoundError(EntityNotFoundError):
    entity_name = "OfferProfile"


class LeadSourcingCampaignNotFoundError(EntityNotFoundError):
    entity_name = "LeadSourcingCampaign"


class LeadSourcingRunNotFoundError(EntityNotFoundError):
    entity_name = "LeadSourcingRun"


class LeadCandidateNotFoundError(EntityNotFoundError):
    entity_name = "LeadCandidate"


class InvalidLeadSourcingProviderError(DomainError):
    """Raised when LEAD_SOURCING_PROVIDER is set to an unrecognized value."""

    def __init__(self, provider: str) -> None:
        self.provider = provider
        super().__init__(
            f"Unknown LEAD_SOURCING_PROVIDER '{provider}'. Expected one of: "
            "mock, manual, search_api."
        )


class LeadSourcingProviderNotConfiguredError(DomainError):
    """Raised when a real search provider is requested but not fully
    configured. Never includes the missing secret's value — only which
    setting is missing."""


class LeadCandidateBlockedError(DomainError):
    """Raised when approving a candidate blocked by do-not-contact —
    do-not-contact can never be bypassed, including from Lead Sourcing."""

    def __init__(self, candidate_id: UUID) -> None:
        self.candidate_id = candidate_id
        super().__init__(
            f"LeadCandidate '{candidate_id}' is blocked by do-not-contact and "
            "cannot be approved."
        )


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
