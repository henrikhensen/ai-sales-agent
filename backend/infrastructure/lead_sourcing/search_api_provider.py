"""Search API Lead Sourcing Provider — safe-mode structure only.

No concrete third-party search API client exists in this project yet. This
class exists so the interface and config plumbing (``LEAD_SOURCING_PROVIDER
=search_api``, ``LEAD_SOURCING_ENABLE_REAL_SEARCH=true``) are fully wired
and testable, without ever performing an unsafe, ToS-violating, or
uncredentialed external call. It never scrapes a search engine's HTML
directly and never scrapes LinkedIn.

The factory (see :mod:`backend.infrastructure.lead_sourcing.factory`)
already falls back to the mock provider whenever real search is disabled,
so this class is only ever instantiated when a caller has explicitly
opted in — and even then, :meth:`search_companies` raises a clear,
secret-free error until a real client is configured, rather than crashing
or silently returning nothing.
"""

from __future__ import annotations

from backend.domain.exceptions import LeadSourcingProviderNotConfiguredError
from backend.infrastructure.lead_sourcing.base import (
    LeadSourcingProvider,
    LeadSourcingProviderStatus,
    LeadSourcingSearchQuery,
    RawLeadCandidate,
)
from backend.shared.config import Settings


class SearchApiLeadSourcingProvider(LeadSourcingProvider):
    name = "search_api"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def get_provider_status(self) -> LeadSourcingProviderStatus:
        return LeadSourcingProviderStatus(
            provider="search_api",
            status="not_configured",
            real_search_enabled=self._settings.lead_sourcing_enable_real_search,
            warnings=[
                "No search API client is configured in this project yet. "
                "Real search calls will fail with a clear error until one is added."
            ],
        )

    async def search_companies(
        self, query: LeadSourcingSearchQuery
    ) -> list[RawLeadCandidate]:
        raise LeadSourcingProviderNotConfiguredError(
            "LEAD_SOURCING_PROVIDER=search_api requires a configured search API "
            "client, which is not yet implemented in this project. Use "
            "LEAD_SOURCING_PROVIDER=mock or LEAD_SOURCING_PROVIDER=manual instead, "
            "or implement a client and wire it in here."
        )
