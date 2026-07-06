"""Input and output schemas for Website Research.

``WebsiteResearchRequest`` is the validated task input (also used as the
API request body); ``WebsiteResearchResponse`` is the extracted result
(also used as the API response body). Fetches only the exact URL the
caller supplies — no automatic mass research, no LinkedIn scraping, no
LLM call.
"""

from __future__ import annotations

from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

_ALLOWED_SCHEMES = {"http", "https"}


class WebsiteResearchRequest(BaseModel):
    """Input for a single website research request."""

    url: str = Field(
        min_length=1,
        description="Public website URL to research. Must be http or https.",
    )
    max_pages: int | None = Field(
        default=1,
        ge=1,
        le=3,
        description="Reserved for a future same-domain crawl; only 1 page is fetched in this phase.",
    )
    include_same_domain_links: bool = Field(
        default=False,
        description="Reserved for a future same-domain crawl; has no effect in this phase.",
    )

    @field_validator("url")
    @classmethod
    def _validate_url(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("url must not be empty or whitespace only")
        parsed = urlparse(stripped)
        if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
            raise ValueError("url must use http or https")
        if not parsed.hostname:
            raise ValueError("url must include a hostname")
        return stripped


class WebsiteResearchResponse(BaseModel):
    """Extracted, human-reviewable content from a single fetched page."""

    url: str = Field(description="The URL originally requested.")
    final_url: str = Field(description="The URL actually fetched, after any redirects.")
    domain: str = Field(description="Hostname of final_url.")
    title: str | None = Field(description="Extracted <title>, if present.")
    meta_description: str | None = Field(
        description="Extracted <meta name='description'>, if present."
    )
    extracted_text: str = Field(description="Readable body text, truncated if very long.")
    text_length: int = Field(description="Length of extracted_text in characters.")
    pages_fetched: int = Field(description="Number of pages actually fetched.")
    sources_used: list[str] = Field(description="URLs actually fetched to produce this result.")
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal notices, e.g. truncation or unsupported multi-page options.",
    )
