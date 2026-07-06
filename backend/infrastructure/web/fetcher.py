"""Safe, read-only HTTP(S) fetcher for a single user-supplied public URL.

Deliberately narrow: this is a Server-Side-Request-Forgery (SSRF) guard for
website research, not a general-purpose HTTP client. It only ever performs
a GET request (never submits a form, never persists cookies across calls,
never follows a redirect without re-validating the target), and refuses to
talk to localhost, loopback/private/link-local/reserved/multicast IP
ranges, or any non-http(s) scheme.

Known limitation: hostname -> IP validation happens before the actual
connection, so a DNS record that changes between the check and the real
connection (DNS rebinding) is not defended against here. That would need a
custom transport that resolves once and pins the IP for the socket
connection — out of scope for this phase, which only needs to block
localhost/private/internal targets a caller supplies directly.
"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from backend.infrastructure.web.exceptions import (
    BlockedHostError,
    FetchHTTPError,
    FetchTimeoutError,
    InvalidURLError,
    ResponseTooLargeError,
    TooManyRedirectsError,
    WebFetchError,
)

_ALLOWED_SCHEMES = {"http", "https"}
_BLOCKED_HOSTNAMES = {"localhost", "localhost.localdomain"}


@dataclass(frozen=True)
class FetchedPage:
    """A single successfully fetched page."""

    requested_url: str
    final_url: str
    status_code: int
    content_type: str
    html: str


def validate_public_url(url: str) -> str:
    """Validate ``url`` and return its hostname, or raise if it is unsafe.

    Rejects non-http(s) schemes, missing hostnames, "localhost", and any
    hostname that resolves to a loopback/private/link-local/reserved/
    unspecified/multicast address (RFC 1918 ranges, 127.0.0.0/8,
    169.254.0.0/16 including the cloud metadata address, etc.).
    """
    parsed = urlparse(url)
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise InvalidURLError(
            f"Unsupported URL scheme '{parsed.scheme}'. Only http and https are allowed."
        )
    hostname = parsed.hostname
    if not hostname:
        raise InvalidURLError("URL is missing a hostname.")

    if hostname.lower().strip(".") in _BLOCKED_HOSTNAMES:
        raise BlockedHostError(f"Host '{hostname}' is not allowed.")

    try:
        # AF_UNSPEC resolves both IPv4 and IPv6 records so no address
        # family is left unchecked.
        infos = socket.getaddrinfo(hostname, None, family=socket.AF_UNSPEC)
    except socket.gaierror as exc:
        raise InvalidURLError(f"Could not resolve host '{hostname}'.") from exc
    if not infos:
        raise InvalidURLError(f"Could not resolve host '{hostname}'.")

    for info in infos:
        raw_ip = info[4][0]
        ip = ipaddress.ip_address(raw_ip)
        if (
            ip.is_loopback
            or ip.is_private
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_unspecified
            or ip.is_multicast
        ):
            raise BlockedHostError(
                f"Host '{hostname}' resolves to a non-public address and is not allowed."
            )

    return hostname


class WebFetcher:
    """Fetches a single public URL safely, re-validating every redirect hop."""

    def __init__(
        self,
        *,
        timeout_seconds: float,
        max_bytes: int,
        user_agent: str,
        max_redirects: int = 3,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._max_bytes = max_bytes
        self._user_agent = user_agent
        self._max_redirects = max_redirects

    async def fetch(self, url: str) -> FetchedPage:
        """GET ``url`` and return its final response.

        Never sends cookies across requests (a fresh client is used per
        call), never submits a form (GET only), and never follows a
        redirect without re-validating the target through the same
        scheme/host/IP checks as the original URL.
        """
        current_url = url
        validate_public_url(current_url)

        async with httpx.AsyncClient(
            timeout=self._timeout_seconds,
            follow_redirects=False,
            headers={"User-Agent": self._user_agent},
        ) as client:
            for hop in range(self._max_redirects + 1):
                try:
                    async with client.stream("GET", current_url) as response:
                        if response.is_redirect:
                            if hop >= self._max_redirects:
                                raise TooManyRedirectsError(
                                    f"Exceeded the maximum of {self._max_redirects} redirects."
                                )
                            location = response.headers.get("location")
                            if not location:
                                raise InvalidURLError(
                                    "Redirect response is missing a Location header."
                                )
                            next_url = str(httpx.URL(current_url).join(location))
                            validate_public_url(next_url)
                            current_url = next_url
                            continue

                        if response.status_code >= 400:
                            raise FetchHTTPError(response.status_code, current_url)

                        html = await self._read_capped_body(response)
                        return FetchedPage(
                            requested_url=url,
                            final_url=str(response.url),
                            status_code=response.status_code,
                            content_type=response.headers.get("content-type", ""),
                            html=html,
                        )
                except httpx.TimeoutException as exc:
                    raise FetchTimeoutError(f"Timed out fetching '{current_url}'.") from exc
                except httpx.HTTPError as exc:
                    raise WebFetchError(f"Could not fetch '{current_url}': {exc}") from exc

        raise TooManyRedirectsError(
            f"Exceeded the maximum of {self._max_redirects} redirects."
        )

    async def _read_capped_body(self, response: httpx.Response) -> str:
        content_length = response.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > self._max_bytes:
                    raise ResponseTooLargeError(
                        f"Response declared {content_length} bytes, exceeding the "
                        f"{self._max_bytes}-byte limit."
                    )
            except ValueError:
                pass

        total = 0
        chunks: list[bytes] = []
        async for chunk in response.aiter_bytes():
            total += len(chunk)
            if total > self._max_bytes:
                raise ResponseTooLargeError(
                    f"Response exceeded the {self._max_bytes}-byte limit."
                )
            chunks.append(chunk)

        body = b"".join(chunks)
        encoding = response.encoding or "utf-8"
        return body.decode(encoding, errors="replace")
