"""Website Research Service: fetches a single public URL and extracts
readable text for human review.

Analysis only — this service never sends an email, never contacts anyone,
never submits a form, and never calls an LLM. It fetches exactly the URL
the caller supplies (via the SSRF-guarded ``WebFetcher``); it deliberately
does *not* crawl same-domain links yet, even if requested, since automatic
mass research is an explicit non-goal of this phase.
"""

from __future__ import annotations

from urllib.parse import urlparse

from backend.application.research.exceptions import (
    InvalidWebsiteURLError,
    WebsiteFetchFailedError,
)
from backend.application.research.schemas import (
    WebsiteResearchRequest,
    WebsiteResearchResponse,
)
from backend.infrastructure.web.exceptions import (
    BlockedHostError,
    InvalidURLError,
    WebFetchError,
)
from backend.infrastructure.web.fetcher import WebFetcher
from backend.infrastructure.web.sanitizer import extract_readable_text

#: Hard cap on the extracted text returned to the caller, independent of
#: the raw response byte cap enforced by WebFetcher (that limits what is
#: downloaded; this limits what is handed back after extraction).
_MAX_EXTRACTED_TEXT_LENGTH = 20_000


class WebsiteResearchService:
    """Fetches a user-supplied public URL and extracts readable text from it."""

    def __init__(self, fetcher: WebFetcher, *, max_pages_cap: int = 1) -> None:
        self._fetcher = fetcher
        self._max_pages_cap = max_pages_cap

    async def research(self, request: WebsiteResearchRequest) -> WebsiteResearchResponse:
        try:
            page = await self._fetcher.fetch(request.url)
        except (InvalidURLError, BlockedHostError) as exc:
            raise InvalidWebsiteURLError(str(exc)) from exc
        except WebFetchError as exc:
            raise WebsiteFetchFailedError(str(exc)) from exc

        extracted = extract_readable_text(page.html)
        text = extracted.text
        warnings: list[str] = []

        if len(text) > _MAX_EXTRACTED_TEXT_LENGTH:
            text = text[:_MAX_EXTRACTED_TEXT_LENGTH]
            warnings.append(
                f"Extracted text was truncated to {_MAX_EXTRACTED_TEXT_LENGTH} characters."
            )

        requested_pages = request.max_pages or 1
        if requested_pages > self._max_pages_cap:
            warnings.append(
                f"max_pages={requested_pages} was requested, but this server allows at "
                f"most {self._max_pages_cap}; only the requested URL was fetched."
            )
        elif requested_pages > 1 or request.include_same_domain_links:
            warnings.append(
                "Multi-page / same-domain crawling is not implemented in this phase "
                "(no automatic mass research) — only the requested URL was fetched."
            )

        domain = urlparse(page.final_url).hostname or urlparse(request.url).hostname or ""

        return WebsiteResearchResponse(
            url=request.url,
            final_url=page.final_url,
            domain=domain,
            title=extracted.title,
            meta_description=extracted.meta_description,
            extracted_text=text,
            text_length=len(text),
            has_viewport_meta=extracted.has_viewport_meta,
            pages_fetched=1,
            sources_used=[page.final_url],
            warnings=warnings,
        )
