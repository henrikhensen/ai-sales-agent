"""Tests for the Brave Search Lead Sourcing Provider.

Covers: config loading (BRAVE_SEARCH_API_KEY), provider selection via the
factory (brave only used when both LEAD_SOURCING_PROVIDER=brave and
LEAD_SOURCING_ENABLE_REAL_SEARCH=true; a missing key blocks rather than
silently falling back to mock), the Brave adapter mapping a mocked API
response onto RawLeadCandidate (including excluded-keyword filtering and
the truncated raw_snapshot), HTTP error/timeout handling, and the
standing guarantee that Brave real-mode candidates never contain the
mock provider's ``*.example`` data.
"""

import httpx
import pytest

from backend.domain.exceptions import (
    InvalidLeadSourcingProviderError,
    LeadSourcingProviderNotConfiguredError,
)
from backend.infrastructure.lead_sourcing.base import LeadSourcingSearchQuery
from backend.infrastructure.lead_sourcing.brave_provider import (
    BraveLeadSourcingProvider,
)
from backend.infrastructure.lead_sourcing.factory import get_lead_sourcing_provider
from backend.infrastructure.lead_sourcing.mock_provider import (
    _MOCK_COMPANIES,
    MockLeadSourcingProvider,
)
from backend.shared.config import get_settings


def _settings(**overrides):
    settings = get_settings()
    original = {}
    for key, value in overrides.items():
        original[key] = getattr(settings, key)
        setattr(settings, key, value)
    return settings, original


def _restore(settings, original):
    for key, value in original.items():
        setattr(settings, key, value)


class _FakeResponse:
    def __init__(self, status_code: int, json_data: dict | None = None):
        self.status_code = status_code
        self._json_data = json_data or {}

    def json(self) -> dict:
        return self._json_data


class _FakeAsyncClient:
    """Stand-in for ``httpx.AsyncClient``, mirroring
    tests/test_email_integration_providers.py's convention."""

    def __init__(self, responses: list):
        self._responses = list(responses)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, **kwargs):
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _patch_client(monkeypatch, responses: list):
    monkeypatch.setattr(
        "backend.infrastructure.lead_sourcing.brave_provider.httpx.AsyncClient",
        lambda **kwargs: _FakeAsyncClient(responses),
    )


_BRAVE_PAYLOAD = {
    "web": {
        "results": [
            {
                "title": "Nordlicht Fertigungstechnik GmbH",
                "url": "https://nordlicht-fertigungstechnik.de",
                "description": "Praezisionsfertigung fuer den Mittelstand.",
            },
            {
                "title": "Lucky Casino Online",
                "url": "https://lucky-casino-online.de",
                "description": "Online Gambling und Casino Spiele.",
            },
        ]
    }
}


# -- config loading -----------------------------------------------------------------


def test_brave_search_api_key_defaults_to_none():
    settings = get_settings()
    assert settings.brave_search_api_key is None


def test_brave_search_api_key_loaded_from_env(monkeypatch):
    from backend.shared.config import Settings

    settings = Settings(BRAVE_SEARCH_API_KEY="a-real-key-value")
    assert settings.brave_search_api_key == "a-real-key-value"


# -- provider selection ---------------------------------------------------------------


def test_invalid_provider_message_mentions_brave():
    settings, original = _settings(lead_sourcing_provider="not-a-real-provider")
    try:
        with pytest.raises(InvalidLeadSourcingProviderError) as exc_info:
            get_lead_sourcing_provider(settings)
        assert "brave" in str(exc_info.value)
    finally:
        _restore(settings, original)


def test_brave_falls_back_to_mock_when_real_search_disabled():
    settings, original = _settings(
        lead_sourcing_provider="brave", lead_sourcing_enable_real_search=False
    )
    try:
        provider = get_lead_sourcing_provider(settings)
        assert isinstance(provider, MockLeadSourcingProvider)
    finally:
        _restore(settings, original)


def test_brave_used_when_real_search_enabled_and_key_present():
    settings, original = _settings(
        lead_sourcing_provider="brave",
        lead_sourcing_enable_real_search=True,
        brave_search_api_key="a-real-key-value",
    )
    try:
        provider = get_lead_sourcing_provider(settings)
        assert isinstance(provider, BraveLeadSourcingProvider)
    finally:
        _restore(settings, original)


async def test_brave_selected_but_missing_key_blocks_instead_of_falling_back_to_mock():
    """The factory must still hand back a BraveLeadSourcingProvider (never
    silently swap in Mock) when the key is missing — the block happens
    inside search_companies(), loudly."""
    settings, original = _settings(
        lead_sourcing_provider="brave",
        lead_sourcing_enable_real_search=True,
        brave_search_api_key=None,
    )
    try:
        provider = get_lead_sourcing_provider(settings)
        assert isinstance(provider, BraveLeadSourcingProvider)
        with pytest.raises(LeadSourcingProviderNotConfiguredError):
            await provider.search_companies(
                LeadSourcingSearchQuery(target_industry="Manufacturing", max_results=10)
            )
    finally:
        _restore(settings, original)


async def test_brave_provider_status_reflects_missing_key():
    settings, original = _settings(brave_search_api_key=None)
    try:
        provider = BraveLeadSourcingProvider(settings)
        status = await provider.get_provider_status()
        assert status.status == "not_configured"
        assert status.warnings
    finally:
        _restore(settings, original)


async def test_brave_provider_status_ready_when_key_present():
    settings, original = _settings(brave_search_api_key="a-real-key-value")
    try:
        provider = BraveLeadSourcingProvider(settings)
        status = await provider.get_provider_status()
        assert status.status == "ready"
        assert status.warnings == []
    finally:
        _restore(settings, original)


# -- Brave adapter: mapping a real API response ----------------------------------------


async def test_brave_search_companies_maps_response_to_raw_candidates(monkeypatch):
    settings, original = _settings(brave_search_api_key="a-real-key-value")
    try:
        provider = BraveLeadSourcingProvider(settings)
        _patch_client(monkeypatch, [_FakeResponse(200, _BRAVE_PAYLOAD)])

        candidates = await provider.search_companies(
            LeadSourcingSearchQuery(
                target_industry="Manufacturing", target_location="Germany", max_results=10
            )
        )

        assert len(candidates) == 2
        first = candidates[0]
        assert first.company_name == "Nordlicht Fertigungstechnik GmbH"
        assert first.company_website_url == "https://nordlicht-fertigungstechnik.de"
        assert first.description == "Praezisionsfertigung fuer den Mittelstand."
        assert first.source_name == "brave"
        assert first.source_url == "https://nordlicht-fertigungstechnik.de"
        assert first.raw_snapshot is not None
        assert len(first.raw_snapshot) <= 500
    finally:
        _restore(settings, original)


async def test_brave_applies_excluded_keywords_after_the_response_comes_back(monkeypatch):
    settings, original = _settings(brave_search_api_key="a-real-key-value")
    try:
        provider = BraveLeadSourcingProvider(settings)
        _patch_client(monkeypatch, [_FakeResponse(200, _BRAVE_PAYLOAD)])

        candidates = await provider.search_companies(
            LeadSourcingSearchQuery(
                target_industry="Manufacturing",
                excluded_keywords=["Casino", "Gambling"],
                max_results=10,
            )
        )

        names = [c.company_name for c in candidates]
        assert "Lucky Casino Online" not in names
        assert "Nordlicht Fertigungstechnik GmbH" in names
    finally:
        _restore(settings, original)


async def test_brave_no_query_terms_returns_empty_without_a_call(monkeypatch):
    settings, original = _settings(brave_search_api_key="a-real-key-value")
    try:
        provider = BraveLeadSourcingProvider(settings)

        def _fail(**kwargs):
            raise AssertionError("must not call the Brave API with an empty query")

        monkeypatch.setattr(
            "backend.infrastructure.lead_sourcing.brave_provider.httpx.AsyncClient", _fail
        )
        candidates = await provider.search_companies(LeadSourcingSearchQuery(max_results=10))
        assert candidates == []
    finally:
        _restore(settings, original)


@pytest.mark.parametrize("status_code", [401, 403, 429, 500])
async def test_brave_maps_error_status_codes_to_a_clear_blocking_error(
    monkeypatch, status_code
):
    settings, original = _settings(brave_search_api_key="a-real-key-value")
    try:
        provider = BraveLeadSourcingProvider(settings)
        _patch_client(monkeypatch, [_FakeResponse(status_code, {})])
        with pytest.raises(LeadSourcingProviderNotConfiguredError):
            await provider.search_companies(
                LeadSourcingSearchQuery(target_industry="Manufacturing", max_results=10)
            )
    finally:
        _restore(settings, original)


async def test_brave_maps_timeout_and_connection_errors(monkeypatch):
    settings, original = _settings(brave_search_api_key="a-real-key-value")
    try:
        provider = BraveLeadSourcingProvider(settings)
        _patch_client(monkeypatch, [httpx.TimeoutException("timed out")])
        with pytest.raises(LeadSourcingProviderNotConfiguredError):
            await provider.search_companies(
                LeadSourcingSearchQuery(target_industry="Manufacturing", max_results=10)
            )
    finally:
        _restore(settings, original)

    settings, original = _settings(brave_search_api_key="a-real-key-value")
    try:
        provider = BraveLeadSourcingProvider(settings)
        _patch_client(monkeypatch, [httpx.ConnectError("no route to host")])
        with pytest.raises(LeadSourcingProviderNotConfiguredError):
            await provider.search_companies(
                LeadSourcingSearchQuery(target_industry="Manufacturing", max_results=10)
            )
    finally:
        _restore(settings, original)


# -- standing guarantee: never the mock provider's data --------------------------------


async def test_brave_real_mode_never_returns_mockprovider_example_domains(monkeypatch):
    settings, original = _settings(brave_search_api_key="a-real-key-value")
    try:
        provider = BraveLeadSourcingProvider(settings)
        _patch_client(monkeypatch, [_FakeResponse(200, _BRAVE_PAYLOAD)])

        candidates = await provider.search_companies(
            LeadSourcingSearchQuery(target_industry="Manufacturing", max_results=10)
        )

        mock_names = {c.company_name for c in _MOCK_COMPANIES}
        mock_domains = {c.company_domain for c in _MOCK_COMPANIES}
        assert len(candidates) >= 1
        for candidate in candidates:
            assert candidate.company_website_url is not None
            assert not candidate.company_website_url.rstrip("/").endswith(".example")
            assert candidate.company_name not in mock_names
            assert candidate.company_domain not in mock_domains
    finally:
        _restore(settings, original)
