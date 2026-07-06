class WebsiteResearchError(Exception):
    """Base class for website research errors surfaced to the API layer."""


class InvalidWebsiteURLError(WebsiteResearchError):
    """The requested URL failed validation (bad scheme, blocked host, etc.)."""


class WebsiteFetchFailedError(WebsiteResearchError):
    """The URL passed validation but could not be fetched (timeout, HTTP
    error, response too large, or too many redirects)."""
