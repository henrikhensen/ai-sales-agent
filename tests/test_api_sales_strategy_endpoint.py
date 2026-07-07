"""Integration tests for the ICP/Offer strategy profile API.

Covers auth/role gating (GET/check-fit/preview: admin/sales/reviewer;
POST create/PATCH update: admin/sales; PATCH deactivate: admin only), CRUD
correctness, and the exact hard requirements from the ICP/offer strategy
spec: fit scoring reacts to positive/negative signals and warns on missing
data, and offer previews surface forbidden_claims/missing proof points.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.api.v1.dependencies import (
    get_icp_profile_repository,
    get_offer_profile_repository,
    get_user_repository,
)
from backend.main import app
from tests.conftest import (
    FakeICPProfileRepository,
    FakeOfferProfileRepository,
    FakeUserRepository,
)

client = TestClient(app)


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
def _fake_icp_profile_repository():
    fake_repo = FakeICPProfileRepository()
    app.dependency_overrides[get_icp_profile_repository] = _returning(fake_repo)
    yield fake_repo
    app.dependency_overrides.pop(get_icp_profile_repository, None)


@pytest.fixture(autouse=True)
def _fake_offer_profile_repository():
    fake_repo = FakeOfferProfileRepository()
    app.dependency_overrides[get_offer_profile_repository] = _returning(fake_repo)
    yield fake_repo
    app.dependency_overrides.pop(get_offer_profile_repository, None)


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


def _create_icp(role: str = "admin", **overrides) -> dict:
    payload = {
        "name": "Mittelstand Logistik",
        "description": "B2B Logistikdienstleister im deutschsprachigen Raum",
        "target_industries": ["Logistics", "Transport"],
        "excluded_industries": ["Gambling"],
        "target_keywords": ["fleet", "supply chain"],
        "negative_keywords": ["student project"],
        "target_pain_points": ["manual dispatch", "no visibility"],
        "buying_triggers": ["recently expanded", "new funding"],
        "required_signals": ["uses SAP"],
        "minimum_fit_score": 70,
        **overrides,
    }
    response = client.post(
        "/api/v1/sales-strategy/icp", json=payload, headers=_auth_header(role)
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_offer(role: str = "admin", **overrides) -> dict:
    payload = {
        "name": "Fleet Visibility Suite",
        "main_value_proposition": "Real-time fleet visibility for logistics teams.",
        "key_benefits": ["Fewer missed deliveries", "Lower fuel costs"],
        "differentiators": ["Works with existing telematics"],
        "proof_points": [],
        "call_to_action": "Book a 15-minute demo",
        "forbidden_claims": ["guaranteed 50% cost reduction"],
        **overrides,
    }
    response = client.post(
        "/api/v1/sales-strategy/offers", json=payload, headers=_auth_header(role)
    )
    assert response.status_code == 201, response.text
    return response.json()


# -- ICP: auth/role gating -----------------------------------------------------


def test_list_icp_without_token_returns_401():
    response = client.get("/api/v1/sales-strategy/icp")
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["admin", "sales", "reviewer"])
def test_list_icp_allowed_for_every_role(role):
    response = client.get("/api/v1/sales-strategy/icp", headers=_auth_header(role))
    assert response.status_code == 200


def test_create_icp_forbidden_for_reviewer():
    response = client.post(
        "/api/v1/sales-strategy/icp",
        json={"name": "x"},
        headers=_auth_header("reviewer"),
    )
    assert response.status_code == 403


def test_deactivate_icp_forbidden_for_sales():
    created = _create_icp()
    response = client.patch(
        f"/api/v1/sales-strategy/icp/{created['id']}/deactivate",
        headers=_auth_header("sales"),
    )
    assert response.status_code == 403


# -- ICP: CRUD ------------------------------------------------------------------


def test_icp_kann_erstellt_werden():
    created = _create_icp()
    assert created["name"] == "Mittelstand Logistik"
    assert created["is_active"] is True
    assert created["minimum_fit_score"] == 70


def test_icp_default_minimum_fit_score_is_70_when_omitted():
    response = client.post(
        "/api/v1/sales-strategy/icp",
        json={"name": "Minimal ICP"},
        headers=_auth_header("admin"),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["minimum_fit_score"] == 70
    assert body["is_active"] is True


def test_icp_kann_aktualisiert_werden():
    created = _create_icp()
    response = client.patch(
        f"/api/v1/sales-strategy/icp/{created['id']}",
        json={"name": "Updated Name", "minimum_fit_score": 80},
        headers=_auth_header("sales"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Updated Name"
    assert body["minimum_fit_score"] == 80
    # Fields not included in the PATCH body are left untouched.
    assert body["target_industries"] == ["Logistics", "Transport"]


def test_icp_kann_deaktiviert_werden():
    created = _create_icp()
    response = client.patch(
        f"/api/v1/sales-strategy/icp/{created['id']}/deactivate",
        headers=_auth_header("admin"),
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_get_missing_icp_returns_404():
    response = client.get(
        f"/api/v1/sales-strategy/icp/{uuid.uuid4()}", headers=_auth_header("admin")
    )
    assert response.status_code == 404


# -- ICP: fit check ---------------------------------------------------------------


def test_icp_fit_check_funktioniert():
    created = _create_icp()
    response = client.post(
        "/api/v1/sales-strategy/icp/check-fit",
        json={
            "icp_profile_id": created["id"],
            "company_name": "Acme Logistics",
            "industry": "Logistics",
        },
        headers=_auth_header("sales"),
    )
    assert response.status_code == 200
    body = response.json()
    assert "fit_score" in body
    assert body["fit_level"] in ("excellent", "good", "medium", "weak", "not_fit")


def test_icp_fit_score_erkennt_positive_signale():
    created = _create_icp()
    response = client.post(
        "/api/v1/sales-strategy/icp/check-fit",
        json={
            "icp_profile_id": created["id"],
            "industry": "Logistics",
            "website_text": (
                "We run a modern fleet and struggle with manual dispatch, "
                "recently expanded and use SAP for supply chain."
            ),
        },
        headers=_auth_header("sales"),
    )
    body = response.json()
    assert body["fit_score"] > 50
    assert len(body["matched_signals"]) > 0
    assert body["fit_level"] in ("excellent", "good")


def test_icp_fit_score_erkennt_negative_signale():
    created = _create_icp()
    response = client.post(
        "/api/v1/sales-strategy/icp/check-fit",
        json={
            "icp_profile_id": created["id"],
            "industry": "Gambling",
            "website_text": "This is a student project, not a real business.",
        },
        headers=_auth_header("sales"),
    )
    body = response.json()
    assert body["fit_score"] < 50
    assert len(body["negative_signals"]) > 0
    assert body["fit_level"] in ("weak", "not_fit")


def test_icp_fit_score_gibt_warnings_bei_fehlenden_daten():
    created = _create_icp()
    response = client.post(
        "/api/v1/sales-strategy/icp/check-fit",
        json={"icp_profile_id": created["id"]},
        headers=_auth_header("sales"),
    )
    body = response.json()
    assert len(body["warnings"]) > 0


def test_icp_fit_check_for_missing_icp_returns_404():
    response = client.post(
        "/api/v1/sales-strategy/icp/check-fit",
        json={"icp_profile_id": str(uuid.uuid4())},
        headers=_auth_header("sales"),
    )
    assert response.status_code == 404


# -- Offer: auth/role gating -----------------------------------------------------


def test_list_offers_without_token_returns_401():
    response = client.get("/api/v1/sales-strategy/offers")
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["admin", "sales", "reviewer"])
def test_list_offers_allowed_for_every_role(role):
    response = client.get(
        "/api/v1/sales-strategy/offers", headers=_auth_header(role)
    )
    assert response.status_code == 200


def test_create_offer_forbidden_for_reviewer():
    response = client.post(
        "/api/v1/sales-strategy/offers",
        json={"name": "x", "main_value_proposition": "y"},
        headers=_auth_header("reviewer"),
    )
    assert response.status_code == 403


def test_deactivate_offer_forbidden_for_sales():
    created = _create_offer()
    response = client.patch(
        f"/api/v1/sales-strategy/offers/{created['id']}/deactivate",
        headers=_auth_header("sales"),
    )
    assert response.status_code == 403


# -- Offer: CRUD ------------------------------------------------------------------


def test_offer_kann_erstellt_werden():
    created = _create_offer()
    assert created["name"] == "Fleet Visibility Suite"
    assert created["tone"] == "professional"
    assert created["language"] == "de"
    assert created["is_active"] is True


def test_offer_kann_aktualisiert_werden():
    created = _create_offer()
    response = client.patch(
        f"/api/v1/sales-strategy/offers/{created['id']}",
        json={"call_to_action": "Reply to this email"},
        headers=_auth_header("sales"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["call_to_action"] == "Reply to this email"
    assert body["main_value_proposition"] == created["main_value_proposition"]


def test_offer_kann_deaktiviert_werden():
    created = _create_offer()
    response = client.patch(
        f"/api/v1/sales-strategy/offers/{created['id']}/deactivate",
        headers=_auth_header("admin"),
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False


# -- Offer: preview -----------------------------------------------------------------


def test_offer_preview_funktioniert():
    created = _create_offer()
    response = client.post(
        "/api/v1/sales-strategy/offers/preview",
        json={"offer_profile_id": created["id"]},
        headers=_auth_header("sales"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]
    assert body["positioning"]
    assert body["suggested_cta"] == "Book a 15-minute demo"


def test_forbidden_claims_werden_berücksichtigt():
    created = _create_offer()
    response = client.post(
        "/api/v1/sales-strategy/offers/preview",
        json={"offer_profile_id": created["id"]},
        headers=_auth_header("sales"),
    )
    body = response.json()
    assert any("forbidden_claims" in w for w in body["warnings"])
    # No proof_points were provided either — that must be flagged too.
    assert any("proof_points" in w for w in body["warnings"])


def test_offer_preview_for_missing_offer_returns_404():
    response = client.post(
        "/api/v1/sales-strategy/offers/preview",
        json={"offer_profile_id": str(uuid.uuid4())},
        headers=_auth_header("sales"),
    )
    assert response.status_code == 404


# -- regression: no send capability ----------------------------------------------


def test_kein_send_endpoint_unter_sales_strategy():
    for route in app.routes:
        path = getattr(route, "path", "")
        if path.startswith("/api/v1/sales-strategy"):
            assert "send" not in path.lower()
