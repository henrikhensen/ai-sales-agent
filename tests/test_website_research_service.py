"""Tests for WebsiteResearchService using a fake WebFetcher — no real
network call, no LLM call, no external service of any kind.
"""

import pytest

from backend.application.research.exceptions import (
    InvalidWebsiteURLError,
    WebsiteFetchFailedError,
)
from backend.application.research.schemas import WebsiteResearchRequest
from backend.application.research.website_research_service import (
    WebsiteResearchService,
)
from backend.infrastructure.web.exceptions import BlockedHostError, FetchTimeoutError
from backend.infrastructure.web.fetcher import FetchedPage


class _FakeFetcher:
    def __init__(self, page: FetchedPage | None = None, error: Exception | None = None):
        self._page = page
        self._error = error
        self.fetched_urls: list[str] = []

    async def fetch(self, url: str) -> FetchedPage:
        self.fetched_urls.append(url)
        if self._error is not None:
            raise self._error
        assert self._page is not None
        return self._page


_SAMPLE_HTML = """
<html>
  <head>
    <title>Acme GmbH</title>
    <meta name="description" content="Logistics software for the mid-market.">
    <style>body { color: red; }</style>
  </head>
  <body>
    <nav><a href="/">Home</a></nav>
    <script>track();</script>
    <p>Acme builds visibility software for freight companies.</p>
  </body>
</html>
"""


async def test_research_extracts_readable_content():
    page = FetchedPage(
        requested_url="https://acme.example.com/",
        final_url="https://acme.example.com/",
        status_code=200,
        content_type="text/html",
        html=_SAMPLE_HTML,
    )
    service = WebsiteResearchService(_FakeFetcher(page=page))

    result = await service.research(
        WebsiteResearchRequest(url="https://acme.example.com/")
    )

    assert result.url == "https://acme.example.com/"
    assert result.final_url == "https://acme.example.com/"
    assert result.domain == "acme.example.com"
    assert result.title == "Acme GmbH"
    assert result.meta_description == "Logistics software for the mid-market."
    assert "Acme builds visibility software for freight companies." in result.extracted_text
    assert "track()" not in result.extracted_text
    assert "color: red" not in result.extracted_text
    assert "Home" not in result.extracted_text
    assert result.text_length == len(result.extracted_text)
    assert result.pages_fetched == 1
    assert result.sources_used == ["https://acme.example.com/"]


async def test_research_truncates_very_long_text_and_warns():
    long_paragraph = "word " * 10_000  # far beyond the 20,000-character cap
    page = FetchedPage(
        requested_url="https://big.example.com/",
        final_url="https://big.example.com/",
        status_code=200,
        content_type="text/html",
        html=f"<body><p>{long_paragraph}</p></body>",
    )
    service = WebsiteResearchService(_FakeFetcher(page=page))

    result = await service.research(
        WebsiteResearchRequest(url="https://big.example.com/")
    )

    assert result.text_length <= 20_000
    assert any("truncated" in warning for warning in result.warnings)


async def test_research_warns_when_max_pages_exceeds_server_cap():
    page = FetchedPage(
        requested_url="https://acme.example.com/",
        final_url="https://acme.example.com/",
        status_code=200,
        content_type="text/html",
        html="<body><p>Hello.</p></body>",
    )
    service = WebsiteResearchService(_FakeFetcher(page=page), max_pages_cap=1)

    result = await service.research(
        WebsiteResearchRequest(url="https://acme.example.com/", max_pages=3)
    )

    # Never actually fetches more than the single requested URL — no
    # automatic mass research, regardless of what max_pages requests.
    assert result.pages_fetched == 1
    assert result.sources_used == ["https://acme.example.com/"]
    assert any("max_pages" in warning for warning in result.warnings)


async def test_research_maps_blocked_host_to_invalid_url_error():
    service = WebsiteResearchService(
        _FakeFetcher(error=BlockedHostError("Host is not allowed."))
    )

    with pytest.raises(InvalidWebsiteURLError):
        await service.research(WebsiteResearchRequest(url="http://169.254.169.254/"))


async def test_research_maps_timeout_to_fetch_failed_error():
    service = WebsiteResearchService(_FakeFetcher(error=FetchTimeoutError("Timed out.")))

    with pytest.raises(WebsiteFetchFailedError):
        await service.research(WebsiteResearchRequest(url="https://slow.example.com/"))
