"""Tests for the SSRF-guarded URL validation in backend/infrastructure/web/fetcher.py.

Uses literal IP addresses wherever possible so these tests never perform a
real DNS lookup or network call — resolving a literal IP is purely local,
offline work for the OS resolver. One test explicitly mocks
``socket.getaddrinfo`` to also cover the hostname-resolution code path
(not just the literal-IP fast path).
"""

import socket

import pytest

from backend.infrastructure.web import fetcher as fetcher_module
from backend.infrastructure.web.exceptions import BlockedHostError, InvalidURLError
from backend.infrastructure.web.fetcher import validate_public_url


def test_valid_https_url_with_public_ip_is_allowed():
    # 8.8.8.8 is a well-known public IP; validate_public_url never connects
    # to it, it only classifies the address.
    hostname = validate_public_url("https://8.8.8.8/some/path")
    assert hostname == "8.8.8.8"


def test_localhost_is_blocked():
    with pytest.raises(BlockedHostError):
        validate_public_url("http://localhost:8000/")


def test_127_0_0_1_is_blocked():
    with pytest.raises(BlockedHostError):
        validate_public_url("http://127.0.0.1/admin")


def test_ipv6_loopback_is_blocked():
    with pytest.raises(BlockedHostError):
        validate_public_url("http://[::1]/")


@pytest.mark.parametrize(
    "ip",
    [
        "10.0.0.5",
        "172.16.0.1",
        "192.168.1.1",
        "169.254.169.254",  # cloud metadata endpoint — link-local
        "0.0.0.0",
    ],
)
def test_private_and_internal_ips_are_blocked(ip):
    with pytest.raises(BlockedHostError):
        validate_public_url(f"http://{ip}/")


@pytest.mark.parametrize("scheme_url", ["ftp://example.com/", "file:///etc/passwd", "javascript:alert(1)"])
def test_invalid_scheme_is_blocked(scheme_url):
    with pytest.raises(InvalidURLError):
        validate_public_url(scheme_url)


def test_url_without_hostname_is_blocked():
    with pytest.raises(InvalidURLError):
        validate_public_url("https:///path-only")


def test_hostname_resolving_to_private_ip_is_blocked(monkeypatch):
    def _fake_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.50.1", 0))]

    monkeypatch.setattr(fetcher_module.socket, "getaddrinfo", _fake_getaddrinfo)

    with pytest.raises(BlockedHostError):
        validate_public_url("http://internal.example.corp/")


def test_hostname_resolving_to_public_ip_is_allowed(monkeypatch):
    def _fake_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]

    monkeypatch.setattr(fetcher_module.socket, "getaddrinfo", _fake_getaddrinfo)

    hostname = validate_public_url("https://example.com/")
    assert hostname == "example.com"


def test_unresolvable_hostname_is_rejected(monkeypatch):
    def _fake_getaddrinfo(*args, **kwargs):
        raise socket.gaierror("name or service not known")

    monkeypatch.setattr(fetcher_module.socket, "getaddrinfo", _fake_getaddrinfo)

    with pytest.raises(InvalidURLError):
        validate_public_url("https://this-domain-does-not-resolve.invalid/")
