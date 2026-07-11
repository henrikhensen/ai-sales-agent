"""Lead Sourcing Provider interface.

Deliberately has no send/outreach capability anywhere: no ``send_email``,
no ``outreach_start``, and no method that contacts anyone. Implementations
must never scrape LinkedIn, never scrape behind a login, never bypass a
CAPTCHA, and never guess a personal email address that isn't already
visible on a public page.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from urllib.parse import urlparse

_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

#: Local-part substrings that mark an address as role-based/business (safe
#: to keep even when personal emails are disallowed) rather than a named
#: individual's personal address.
_ROLE_BASED_LOCAL_PARTS = (
    "info",
    "contact",
    "kontakt",
    "sales",
    "hello",
    "hi",
    "support",
    "office",
    "team",
    "mail",
    "inquiries",
    "enquiries",
    "press",
    "media",
    "admin",
)


@dataclass(frozen=True)
class LeadSourcingSearchQuery:
    """Search parameters derived from a campaign, passed to a provider."""

    search_query: str | None = None
    target_industry: str | None = None
    target_location: str | None = None
    target_keywords: list[str] = field(default_factory=list)
    excluded_keywords: list[str] = field(default_factory=list)
    max_results: int = 25


@dataclass
class RawLeadCandidate:
    """An unnormalized candidate as returned by a provider — before
    website enrichment, contact extraction, do-not-contact checking,
    duplicate detection, or ICP scoring are applied by the service."""

    company_name: str | None = None
    company_domain: str | None = None
    company_website_url: str | None = None
    industry: str | None = None
    location: str | None = None
    description: str | None = None
    source_url: str | None = None
    source_name: str | None = None
    confidence_score: float | None = None
    # Truncated, human-readable copy of the provider's raw result for this
    # candidate (e.g. the raw Brave Search API result) — an audit trail
    # only, never parsed back out. Stored on the candidate's ``notes`` by
    # the service. None for providers that have nothing extra to attach.
    raw_snapshot: str | None = None


@dataclass(frozen=True)
class LeadSourcingProviderStatus:
    provider: str
    status: str
    real_search_enabled: bool
    warnings: list[str] = field(default_factory=list)


def _domain_from_url(url: str) -> str | None:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = parsed.hostname
    return host.lower().removeprefix("www.") if host else None


def _normalize_url(url: str) -> str:
    url = url.strip()
    if "://" not in url:
        url = f"https://{url}"
    return url.rstrip("/")


class LeadSourcingProvider(ABC):
    """Finds candidate companies for a lead sourcing campaign."""

    name: str

    @abstractmethod
    async def get_provider_status(self) -> LeadSourcingProviderStatus:
        """Return whether this provider is ready to run, and why not if not."""

    @abstractmethod
    async def search_companies(
        self, query: LeadSourcingSearchQuery
    ) -> list[RawLeadCandidate]:
        """Return up to ``query.max_results`` raw candidate companies."""

    async def enrich_company_candidate(
        self, candidate: RawLeadCandidate
    ) -> RawLeadCandidate:
        """Provider-specific enrichment beyond the initial search result.

        Default is a no-op passthrough — the common case (fetching the
        candidate's own public website) is handled by the service via the
        existing, SSRF-guarded Website Research service, not here.
        """
        return candidate

    def extract_public_contact_info(
        self, extracted_text: str | None, *, allow_personal_emails: bool
    ) -> str | None:
        """Extract one public contact email already visible in
        ``extracted_text`` (e.g. Website Research output). Never guesses,
        never triggers a new fetch. Returns None if nothing suitable is
        found. When ``allow_personal_emails`` is False, only a role-based
        address (info@, sales@, contact@, ...) is returned."""
        if not extracted_text:
            return None
        for email in _EMAIL_PATTERN.findall(extracted_text):
            local_part = email.split("@", 1)[0].lower()
            is_role_based = any(role in local_part for role in _ROLE_BASED_LOCAL_PARTS)
            if is_role_based or allow_personal_emails:
                return email.lower()
        return None

    def normalize_candidate(self, candidate: RawLeadCandidate) -> RawLeadCandidate:
        """Normalize company name/domain/URL formatting. Shared,
        provider-independent logic."""
        domain = candidate.company_domain
        website_url = candidate.company_website_url
        if website_url and not domain:
            domain = _domain_from_url(website_url)
        if domain:
            domain = domain.strip().lower().removeprefix("www.")
        if website_url:
            website_url = _normalize_url(website_url)
        return RawLeadCandidate(
            company_name=(
                candidate.company_name.strip() if candidate.company_name else None
            ),
            company_domain=domain,
            company_website_url=website_url,
            industry=candidate.industry.strip() if candidate.industry else None,
            location=candidate.location.strip() if candidate.location else None,
            description=candidate.description,
            source_url=candidate.source_url,
            source_name=candidate.source_name,
            confidence_score=candidate.confidence_score,
            raw_snapshot=candidate.raw_snapshot,
        )
