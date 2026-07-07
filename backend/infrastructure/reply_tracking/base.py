"""Provider-agnostic interface for reading replies from Gmail/Outlook/Mock.

Deliberately has no ``send_email``/``reply_email``/``send_reply`` method,
and no method is ever added that could send anything — this interface can
only ever read messages that already exist in a connected mailbox. Sending
a reply, or any email, remains a fully separate, manual step entirely
outside this system.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


class ReplyTrackingError(Exception):
    """Base class for reply tracking provider errors."""


class ReplyTrackingConfigError(ReplyTrackingError):
    """Raised when OAuth configuration (client id/secret/key) is missing."""


class ReplyTrackingAuthError(ReplyTrackingError):
    """Raised for a missing, expired, or invalid OAuth token."""


class ReplyTrackingPermissionError(ReplyTrackingError):
    """Raised when the connected account's OAuth grant is missing the read
    scope this provider needs (e.g. only draft-compose scope was granted)."""


class ReplyTrackingRateLimitError(ReplyTrackingError):
    """Raised when the provider reports its rate limit was exceeded."""


class ReplyTrackingTimeoutError(ReplyTrackingError):
    """Raised when a request to the provider times out."""


class ReplyTrackingConnectionError(ReplyTrackingError):
    """Raised when the provider cannot be reached (network failure)."""


class ReplyTrackingProviderError(ReplyTrackingError):
    """Raised for any other provider-side API error."""


@dataclass(frozen=True)
class ProviderConnectionStatus:
    """Whether a user currently has an active connection to a provider."""

    provider: str
    connected: bool
    external_account_email: str | None = None
    message: str = ""


@dataclass(frozen=True)
class SyncedReplyMessage:
    """One message read from a provider, before it is stored as a Reply.

    ``body_text`` is the full message body as read from the provider — the
    caller (the reply tracking service) is responsible for truncating it to
    a preview, or discarding it entirely, per
    ``REPLY_TRACKING_STORE_BODY_PREVIEW_ONLY``. No attachment data is ever
    included here.
    """

    provider_message_id: str
    from_email: str
    received_at: datetime
    provider_thread_id: str | None = None
    from_name: str | None = None
    to_email: str | None = None
    subject: str | None = None
    body_text: str = ""
    provider_message_url: str | None = None


@dataclass(frozen=True)
class ReplySyncRequest:
    """Bounds for a single sync call — always respected by every provider."""

    known_emails: list[str] = field(default_factory=list)
    since: datetime | None = None
    max_messages: int = 25


class ReplyTrackingProvider(ABC):
    """Port for a reply-reading backend (mock, Gmail, Outlook).

    Every method here only ever reads messages that already exist in a
    connected mailbox — none of them can send anything, and no send-capable
    method is ever added to this interface.
    """

    #: Stable identifier for the provider, surfaced in API responses.
    name: str

    @abstractmethod
    async def get_provider_status(self, user_id: UUID) -> ProviderConnectionStatus:
        """Return whether ``user_id`` currently has an active connection
        with sufficient read permission for reply tracking."""

    @abstractmethod
    async def sync_replies_for_draft(
        self, user_id: UUID, request: ReplySyncRequest
    ) -> list[SyncedReplyMessage]:
        """Read messages from ``request.known_emails`` relevant to one
        email draft's thread(s)."""

    @abstractmethod
    async def sync_replies_for_lead(
        self, user_id: UUID, request: ReplySyncRequest
    ) -> list[SyncedReplyMessage]:
        """Read messages from ``request.known_emails`` relevant to one lead."""

    @abstractmethod
    async def sync_recent_replies(
        self, user_id: UUID, request: ReplySyncRequest
    ) -> list[SyncedReplyMessage]:
        """Read recent messages from any of ``request.known_emails``."""

    @abstractmethod
    async def get_thread_messages(
        self, user_id: UUID, provider_thread_id: str
    ) -> list[SyncedReplyMessage]:
        """Return every message in a single thread, oldest first."""

    @abstractmethod
    def get_reply_provider_message_url(self, provider_message_id: str) -> str | None:
        """Build a deep link to a message in the provider's own web UI."""
