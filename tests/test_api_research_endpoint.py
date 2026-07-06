"""Integration tests for POST /api/v1/research/website.

Overrides the WebFetcher dependency with a fake — no real network call is
ever made in these tests. Covers auth/role gating (admin/reviewer/sales
allowed, no token -> 401) and a health-endpoint regression check.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.api.v1.dependencies import get_user_repository, get_web_fetcher
from backend.infrastructure.web.exceptions import BlockedHostError
from backend.infrastructure.web.fetcher import FetchedPage
from backend.main import app
from tests.conftest import FakeUserRepository

client = TestClient(app)

_SAMPLE_HTML = """
<html>
  <head>
    <title>Acme GmbH</title>
    <meta name="description" content="Logistics software.">
  </head>
  <body><p>Acme builds freight visibility software.</p></body>
</html>
"""


class _FakeFetcher:
    def __init__(self, page: FetchedPage | None = None, error: Exception | None = None):
        self._page = page
        self._error = error

    async def fetch(self, url: str) -> FetchedPage:
        if self._error is not None:
            raise self._error
        assert self._page is not None
        return self._page


def _returning(fake):
    def _get():
        return fake

    return _get


@pytest.fixture(autouse=True)
def _fake_user_repository():
    fake_repo = FakeUserRepository()
    app.dependency_overrides[get_user_repository] = _returning(fake_repo)
    yield fake_repo
    app.dependency_overrides.pop(get_user_repository, None)


@pytest.fixture(autouse=True)
def _fake_web_fetcher():
    page = FetchedPage(
        requested_url="https://acme.example.com/",
        final_url="https://acme.example.com/",
        status_code=200,
        content_type="text/html",
        html=_SAMPLE_HTML,
    )
    app.dependency_overrides[get_web_fetcher] = _returning(_FakeFetcher(page=page))
    yield
    app.dependency_overrides.pop(get_web_fetcher, None)


def _login_as(role: str) -> str:
    email = f"{role}-{uuid.uuid4().hex[:8]}@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpassword123", "role": role},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "testpassword123"},
    )
    return login.json()["access_token"]


def _auth_header(role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {_login_as(role)}"}


def test_research_website_without_token_returns_401():
    response = client.post(
        "/api/v1/research/website", json={"url": "https://acme.example.com/"}
    )
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["admin", "reviewer", "sales"])
def test_research_website_allowed_for_every_role(role):
    response = client.post(
        "/api/v1/research/website",
        json={"url": "https://acme.example.com/"},
        headers=_auth_header(role),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["url"] == "https://acme.example.com/"
    assert data["final_url"] == "https://acme.example.com/"
    assert data["domain"] == "acme.example.com"
    assert data["title"] == "Acme GmbH"
    assert data["meta_description"] == "Logistics software."
    assert "Acme builds freight visibility software." in data["extracted_text"]
    assert data["pages_fetched"] == 1
    assert data["sources_used"] == ["https://acme.example.com/"]


def test_research_website_rejects_invalid_scheme():
    response = client.post(
        "/api/v1/research/website",
        json={"url": "ftp://acme.example.com/"},
        headers=_auth_header("admin"),
    )
    assert response.status_code == 422


def test_research_website_rejects_max_pages_above_three():
    response = client.post(
        "/api/v1/research/website",
        json={"url": "https://acme.example.com/", "max_pages": 4},
        headers=_auth_header("admin"),
    )
    assert response.status_code == 422


def test_research_website_maps_blocked_host_to_422():
    app.dependency_overrides[get_web_fetcher] = _returning(
        _FakeFetcher(error=BlockedHostError("Host is not allowed."))
    )
    try:
        response = client.post(
            "/api/v1/research/website",
            json={"url": "http://169.254.169.254/"},
            headers=_auth_header("admin"),
        )
    finally:
        app.dependency_overrides.pop(get_web_fetcher, None)

    assert response.status_code == 422


def test_research_endpoint_registered_under_research_tag():
    matching = [
        route for route in app.routes if getattr(route, "path", "") == "/api/v1/research/website"
    ]
    assert len(matching) == 1
    assert "research" in getattr(matching[0], "tags", [])


# -- Regression -----------------------------------------------------------------

def test_health_endpoint_still_works():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] in ("ok", "degraded")
