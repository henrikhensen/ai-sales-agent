"""Provider-agnostic interface for Controlled Outreach Dispatch.

Deliberately narrow: a provider can only ever (1) create an external draft
for a specific, already-approved email draft (delegating to the existing
Gmail/Outlook/Mock draft integration — see
``backend.application.integrations.email_draft_integration_service``), or
(2) attempt a single, already-confirmed manual send for a specific queue
item/email draft. There is no method that accepts arbitrary content, no
batch-send method, and no method that could send anything without a
caller-supplied, already-approved ``email_draft_id`` plus an explicit
confirmation upstream. Real sending is never available for Gmail/Outlook
in this codebase — no send scope (``gmail.send``/``Mail.Send``) is ever
requested anywhere — so those providers always report a clear safe-mode
result for :meth:`DispatchProvider.send_manual_confirmed_message`; only
the mock provider ever simulates a confirmed send, and it never makes a
real network call while doing so.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class DispatchProviderStatus:
    """Whether this dispatch provider is currently usable, and for what."""

    provider: str
    configured: bool
    safe_mode: bool
    connected: bool = False
    supports_manual_send: bool = False
    message: str = ""


@dataclass(frozen=True)
class DispatchActionResult:
    """Outcome of a single provider action (draft creation or manual send).

    ``status`` is one of the ``OutreachDispatch.dispatch_status`` values —
    never anything resembling an automatic "sent" outcome; a real send is
    only ever reflected here when the caller already confirmed it.
    """

    status: str
    blocked: bool = False
    provider_message_id: str | None = None
    provider_draft_id: str | None = None
    provider_url: str | None = None
    message: str = ""


class DispatchProvider(ABC):
    """Port for a Controlled Outreach Dispatch backend (mock, Gmail, Outlook)."""

    #: Stable identifier for the provider, surfaced in API responses.
    name: str

    @abstractmethod
    async def get_provider_status(self, user_id: UUID) -> DispatchProviderStatus:
        """Report whether this provider is configured/connected for
        ``user_id``, and whether it actually supports manual send (it
        never does for Gmail/Outlook in this codebase)."""

    @abstractmethod
    async def create_external_draft(
        self, *, user_id: UUID, email_draft_id: UUID
    ) -> DispatchActionResult:
        """Create an external draft for an already-approved email draft.

        Delegates to the existing, already-gated Email Draft Integration
        service — never re-implements its do-not-contact/review checks.
        """

    @abstractmethod
    async def send_manual_confirmed_message(
        self, *, user_id: UUID, email_draft_id: UUID, dispatch_id: UUID
    ) -> DispatchActionResult:
        """Attempt a single, already-confirmed manual send.

        Callers must have already verified do-not-contact, review
        approval, compliance acknowledgement, and final confirmation —
        this method performs no automation and is never invoked from a
        batch or loop. Gmail/Outlook always return a safe-mode ``blocked``
        result here since no send scope is ever requested; only the mock
        provider simulates success, and never over a real network call.
        """

    @abstractmethod
    async def get_dispatch_status(
        self, *, provider_message_id: str | None, provider_draft_id: str | None
    ) -> DispatchProviderStatus:
        """Report the provider's current view of a previously created
        draft/send — read-only, never triggers a new action."""
