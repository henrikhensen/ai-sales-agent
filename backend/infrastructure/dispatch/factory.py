"""Factory for the active Controlled Outreach Dispatch provider.

Mirrors ``backend.infrastructure.email_integration.factory``: never
raises — an unrecognized or unconfigured provider name simply yields the
mock provider so the app never crashes on bad configuration.
"""

from __future__ import annotations

from backend.application.integrations.email_draft_integration_service import (
    EmailDraftIntegrationService,
)
from backend.domain.repositories.email_provider_connection_repository import (
    EmailProviderConnectionRepository,
)
from backend.infrastructure.dispatch.base import DispatchProvider
from backend.infrastructure.dispatch.mock_provider import MockDispatchProvider
from backend.infrastructure.dispatch.real_provider import (
    GmailDispatchProvider,
    OutlookDispatchProvider,
)
from backend.shared.config import Settings


def create_dispatch_provider(
    connections: EmailProviderConnectionRepository,
    email_draft_integration: EmailDraftIntegrationService,
    settings: Settings,
) -> DispatchProvider:
    provider_name = settings.outreach_dispatch_provider.strip().lower()
    if provider_name == "gmail":
        return GmailDispatchProvider(email_draft_integration, connections, settings)
    if provider_name == "outlook":
        return OutlookDispatchProvider(email_draft_integration, connections, settings)
    return MockDispatchProvider(email_draft_integration)
