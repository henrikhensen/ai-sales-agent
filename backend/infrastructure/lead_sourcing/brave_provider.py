"""Brave Search Lead Sourcing Provider — a real web-search-backed provider.

Prepared for real use but only ever invoked when
``LEAD_SOURCING_PROVIDER=brave`` and ``LEAD_SOURCING_ENABLE_REAL_SEARCH=
true`` are both set (enforced by
``backend.infrastructure.lead_sourcing.factory``, not by this class).
``BRAVE_SEARCH_API_KEY`` is read once from ``Settings`` and is never
logged, returned in an API response, or exposed to the frontend — a
missing key blocks :meth:`search_companies` with a clear error rather
than silently falling back to mock results.

Calls the public Brave Search Web API (``api.search.brave.com``) only —
never scrapes a search engine's HTML directly, never touches LinkedIn,
never fetches anything behind a login or a CAPTCHA. This class has no
send/outreach capability of any kind.
"""

from __future__ import annotations

import logging

import httpx

from backend.domain.exceptions import LeadSourcingProviderNotConfiguredError
from backend.infrastructure.lead_sourcing.base import (
    LeadSourcingProvider,
    LeadSourcingProviderStatus,
    LeadSourcingSearchQuery,
    RawLeadCandidate,
)
from backend.shared.config import Settings

logger = logging.getLogger(__name__)

_BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
_MAX_RESULTS_PER_REQUEST = 20  # Brave's own per-request cap.
_RAW_SNAPSHOT_MAX_LENGTH = 500


def _build_query_string(query: LeadSourcingSearchQuery) -> str:
    """Builds a Brave query from target industry, region, and keywords.
    Excluded keywords are appended as Brave's own ``-term`` exclusion
    syntax *and* re-checked by ``_matches_excluded_keywords`` below after
    the response comes back — never trusted to the remote API alone."""
    parts: list[str] = []
    if query.search_query:
        parts.append(query.search_query)
    if query.target_industry:
        parts.append(query.target_industry)
    if query.target_location:
        parts.append(query.target_location)
    parts.extend(k for k in query.target_keywords if k.strip())
    parts.extend(f"-{k}" for k in query.excluded_keywords if k.strip())
    return " ".join(parts).strip()


def _matches_excluded_keywords(result: dict, excluded_keywords: list[str]) -> bool:
    if not excluded_keywords:
        return False
    haystack = f"{result.get('title', '')} {result.get('description', '')}".lower()
    return any(
        keyword.strip().lower() in haystack
        for keyword in excluded_keywords
        if keyword.strip()
    )


class BraveLeadSourcingProvider(LeadSourcingProvider):
    name = "brave"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def get_provider_status(self) -> LeadSourcingProviderStatus:
        has_key = bool(self._settings.brave_search_api_key)
        return LeadSourcingProviderStatus(
            provider="brave",
            status="ready" if has_key else "not_configured",
            real_search_enabled=self._settings.lead_sourcing_enable_real_search,
            warnings=(
                []
                if has_key
                else [
                    "BRAVE_SEARCH_API_KEY is not set — real Brave Search calls "
                    "will be blocked, not silently redirected to mock data."
                ]
            ),
        )

    async def search_companies(
        self, query: LeadSourcingSearchQuery
    ) -> list[RawLeadCandidate]:
        api_key = self._settings.brave_search_api_key
        if not api_key:
            raise LeadSourcingProviderNotConfiguredError(
                "LEAD_SOURCING_PROVIDER=brave requires BRAVE_SEARCH_API_KEY to be "
                "set — refusing to silently fall back to mock results."
            )

        query_string = _build_query_string(query)
        if not query_string:
            return []

        count = max(1, min(query.max_results, _MAX_RESULTS_PER_REQUEST))

        async with httpx.AsyncClient(
            timeout=self._settings.lead_sourcing_request_timeout_seconds
        ) as client:
            try:
                response = await client.get(
                    _BRAVE_SEARCH_URL,
                    headers={
                        "Accept": "application/json",
                        "X-Subscription-Token": api_key,
                    },
                    params={"q": query_string, "count": count},
                )
            except httpx.TimeoutException as exc:
                raise LeadSourcingProviderNotConfiguredError(
                    "Timed out calling the Brave Search API."
                ) from exc
            except httpx.HTTPError as exc:
                raise LeadSourcingProviderNotConfiguredError(
                    "Could not reach the Brave Search API."
                ) from exc

        if response.status_code == 401 or response.status_code == 403:
            logger.warning(
                "brave search rejected the request with status %s",
                response.status_code,
            )
            raise LeadSourcingProviderNotConfiguredError(
                "Brave rejected BRAVE_SEARCH_API_KEY (status "
                f"{response.status_code}) — check the key, never its value."
            )
        if response.status_code == 429:
            raise LeadSourcingProviderNotConfiguredError(
                "Brave Search API rate limit reached (status 429) — try again later."
            )
        if response.status_code >= 400:
            logger.warning(
                "brave search failed with status %s", response.status_code
            )
            raise LeadSourcingProviderNotConfiguredError(
                f"Brave Search API returned an error (status {response.status_code})."
            )

        payload = response.json()
        web_results = (payload.get("web") or {}).get("results") or []

        candidates: list[RawLeadCandidate] = []
        for result in web_results[: query.max_results]:
            if _matches_excluded_keywords(result, query.excluded_keywords):
                continue
            url = result.get("url")
            if not url:
                continue
            candidates.append(
                RawLeadCandidate(
                    company_name=result.get("title") or url,
                    company_website_url=url,
                    industry=query.target_industry,
                    location=query.target_location,
                    description=result.get("description"),
                    source_url=url,
                    source_name="brave",
                    confidence_score=0.5,
                    raw_snapshot=str(result)[:_RAW_SNAPSHOT_MAX_LENGTH],
                )
            )
        return candidates
