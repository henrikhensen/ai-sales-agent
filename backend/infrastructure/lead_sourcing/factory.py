"""Resolves the configured :class:`LeadSourcingProvider`.

Enforces the safe-mode contract in one place: real search stays disabled
unless ``LEAD_SOURCING_ENABLE_REAL_SEARCH=true`` is explicitly set, even
when ``LEAD_SOURCING_PROVIDER=search_api`` or ``=brave`` — in that case
this silently falls back to the mock provider rather than ever
attempting a real call. Once real search *is* enabled for ``brave``, a
missing ``BRAVE_SEARCH_API_KEY`` still never falls back to mock here —
:class:`BraveLeadSourcingProvider` blocks the call itself with a clear
error instead (see its ``search_companies``).
"""

from __future__ import annotations

from backend.domain.exceptions import InvalidLeadSourcingProviderError
from backend.infrastructure.lead_sourcing.base import LeadSourcingProvider
from backend.infrastructure.lead_sourcing.brave_provider import (
    BraveLeadSourcingProvider,
)
from backend.infrastructure.lead_sourcing.manual_provider import (
    ManualLeadSourcingProvider,
)
from backend.infrastructure.lead_sourcing.mock_provider import MockLeadSourcingProvider
from backend.infrastructure.lead_sourcing.search_api_provider import (
    SearchApiLeadSourcingProvider,
)
from backend.shared.config import Settings

_VALID_PROVIDERS = ("mock", "manual", "search_api", "brave")


def get_lead_sourcing_provider(settings: Settings) -> LeadSourcingProvider:
    provider_name = settings.lead_sourcing_provider
    if provider_name not in _VALID_PROVIDERS:
        raise InvalidLeadSourcingProviderError(provider_name)

    if provider_name == "manual":
        return ManualLeadSourcingProvider()

    if provider_name == "search_api" and settings.lead_sourcing_enable_real_search:
        return SearchApiLeadSourcingProvider(settings)

    if provider_name == "brave" and settings.lead_sourcing_enable_real_search:
        return BraveLeadSourcingProvider(settings)

    # provider_name == "mock", or "search_api"/"brave" with real search
    # disabled — always falls back to mock, never makes an external call.
    return MockLeadSourcingProvider()
