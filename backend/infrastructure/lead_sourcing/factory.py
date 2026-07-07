"""Resolves the configured :class:`LeadSourcingProvider`.

Enforces the safe-mode contract in one place: real search stays disabled
unless ``LEAD_SOURCING_ENABLE_REAL_SEARCH=true`` is explicitly set, even
when ``LEAD_SOURCING_PROVIDER=search_api`` — in that case this silently
falls back to the mock provider rather than ever attempting a real call.
"""

from __future__ import annotations

from backend.domain.exceptions import InvalidLeadSourcingProviderError
from backend.infrastructure.lead_sourcing.base import LeadSourcingProvider
from backend.infrastructure.lead_sourcing.manual_provider import (
    ManualLeadSourcingProvider,
)
from backend.infrastructure.lead_sourcing.mock_provider import MockLeadSourcingProvider
from backend.infrastructure.lead_sourcing.search_api_provider import (
    SearchApiLeadSourcingProvider,
)
from backend.shared.config import Settings

_VALID_PROVIDERS = ("mock", "manual", "search_api")


def get_lead_sourcing_provider(settings: Settings) -> LeadSourcingProvider:
    provider_name = settings.lead_sourcing_provider
    if provider_name not in _VALID_PROVIDERS:
        raise InvalidLeadSourcingProviderError(provider_name)

    if provider_name == "manual":
        return ManualLeadSourcingProvider()

    if provider_name == "search_api" and settings.lead_sourcing_enable_real_search:
        return SearchApiLeadSourcingProvider(settings)

    # provider_name == "mock", or "search_api" with real search disabled —
    # always falls back to mock, never makes an external call.
    return MockLeadSourcingProvider()
