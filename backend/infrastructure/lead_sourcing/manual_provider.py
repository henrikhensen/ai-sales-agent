"""Manual/Import Lead Sourcing Provider.

Marks candidates as coming from a human-entered list rather than a search
— see :meth:`LeadSourcingService.import_candidates`, which parses raw text
directly into :class:`RawLeadCandidate` objects and never calls
``search_companies`` on this provider (there is nothing to search: the
candidates are already fully specified by the user).
"""

from __future__ import annotations

from backend.infrastructure.lead_sourcing.base import (
    LeadSourcingProvider,
    LeadSourcingProviderStatus,
    LeadSourcingSearchQuery,
    RawLeadCandidate,
)


class ManualLeadSourcingProvider(LeadSourcingProvider):
    name = "manual"

    async def get_provider_status(self) -> LeadSourcingProviderStatus:
        return LeadSourcingProviderStatus(
            provider="manual",
            status="ready",
            real_search_enabled=False,
            warnings=[],
        )

    async def search_companies(
        self, query: LeadSourcingSearchQuery
    ) -> list[RawLeadCandidate]:
        # Manual import supplies candidates directly (see
        # LeadSourcingService.import_candidates) — this provider is never
        # asked to search.
        return []
