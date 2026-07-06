"""Provider-agnostic interface for creating external (Gmail/Outlook/Mock)
email drafts.

Deliberately has no ``send_email``/``send_draft`` method, and no method is
ever added that could send anything — this interface can only ever create
a draft at a provider or report on one that already exists. Sending
remains a fully separate, manual step entirely outside this system.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from backend.domain.enums import ExternalDraftProviderStatus


class EmailIntegrationError(Exception):
    """Base class for email integration provider errors."""


class EmailIntegrationConfigError(EmailIntegrationError):
    """Raised when OAuth configuration (client id/secret/key) is missing."""


class EmailIntegrationAuthError(EmailIntegrationError):
    """Raised for a missing, expired, or invalid OAuth token."""


class EmailIntegrationRateLimitError(EmailIntegrationError):
    """Raised when the provider reports its rate limit was exceeded."""


class EmailIntegrationTimeoutError(EmailIntegrationError):
    """Raised when a request to the provider times out."""


class EmailIntegrationConnectionError(EmailIntegrationError):
    """Raised when the provider cannot be reached (network failure)."""


class EmailIntegrationProviderError(EmailIntegrationError):
    """Raised for any other provider-side API error."""


@dataclass(frozen=True)
class ProviderConnectionStatus:
    """Whether a user currently has an active connection to a provider."""

    provider: str
    connected: bool
    external_account_email: str | None = None
    message: str = ""


@dataclass(frozen=True)
class OAuthStartResult:
    """Where to send the user's browser to begin an OAuth authorization."""

    authorization_url: str
    state: str


@dataclass(frozen=True)
class ExternalDraftRequest:
    """Content for a single external draft. Draft only — never sent."""

    subject: str
    body: str
    recipient_email: str | None = None


@dataclass(frozen=True)
class ExternalDraftResult:
    """Outcome of creating (or checking) one external draft."""

    provider: str
    status: ExternalDraftProviderStatus
    provider_draft_id: str | None = None
    provider_draft_url: str | None = None
    message: str = ""


class EmailDraftProvider(ABC):
    """Port for an email-draft-creation backend (mock, Gmail, Outlook).

    Every method here only ever creates or inspects a *draft* — none of
    them can send anything, and no send-capable method is ever added to
    this interface.
    """

    #: Stable identifier for the provider, surfaced in API responses.
    name: str

    @abstractmethod
    async def get_provider_status(self, user_id: UUID) -> ProviderConnectionStatus:
        """Return whether ``user_id`` currently has an active connection."""

    @abstractmethod
    async def start_oauth_connection(
        self, user_id: UUID, redirect_uri: str
    ) -> OAuthStartResult:
        """Begin an OAuth authorization for ``user_id``.

        Requests only draft-creation scope (e.g. Gmail's
        ``gmail.compose``), never a send scope.
        """

    @abstractmethod
    async def handle_oauth_callback(
        self, user_id: UUID, code: str, state: str, redirect_uri: str
    ) -> ProviderConnectionStatus:
        """Exchange an authorization code for tokens and persist them
        (encrypted) as ``user_id``'s active connection."""

    @abstractmethod
    async def disconnect_provider(self, user_id: UUID) -> None:
        """Deactivate ``user_id``'s connection. Idempotent."""

    @abstractmethod
    async def create_external_draft(
        self, user_id: UUID, request: ExternalDraftRequest
    ) -> ExternalDraftResult:
        """Create a draft at the provider. Never sends it."""

    @abstractmethod
    async def get_external_draft_status(
        self, user_id: UUID, provider_draft_id: str
    ) -> ExternalDraftResult:
        """Look up a previously created draft's current status at the
        provider. Never sends it."""
