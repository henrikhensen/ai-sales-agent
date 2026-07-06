class WebFetchError(Exception):
    """Base class for website-fetching errors."""


class InvalidURLError(WebFetchError):
    """Raised when a URL fails scheme/hostname validation."""


class BlockedHostError(WebFetchError):
    """Raised when a host resolves to a disallowed network.

    Covers localhost, loopback, private, link-local, reserved, unspecified,
    and multicast addresses — i.e. anything that isn't a plain public host.
    """


class FetchTimeoutError(WebFetchError):
    """Raised when a fetch exceeds the configured timeout."""


class TooManyRedirectsError(WebFetchError):
    """Raised when a fetch exceeds the configured redirect limit."""


class ResponseTooLargeError(WebFetchError):
    """Raised when a response body exceeds the configured maximum size."""


class FetchHTTPError(WebFetchError):
    """Raised when the server returns a non-2xx status code."""

    def __init__(self, status_code: int, url: str) -> None:
        self.status_code = status_code
        self.url = url
        super().__init__(f"Received HTTP {status_code} fetching '{url}'.")
