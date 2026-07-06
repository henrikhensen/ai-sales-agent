import uuid

import pytest
from fastapi.testclient import TestClient

from backend.api.v1.dependencies import (
    get_email_draft_repository,
    get_review_event_repository,
    get_user_repository,
    get_workflow_run_repository,
)
from backend.domain.entities.email_draft import EmailDraft
from backend.domain.entities.workflow_run import WorkflowRun
from backend.main import app
from tests.conftest import (
    FakeEmailDraftRepository,
    FakeReviewEventRepository,
    FakeUserRepository,
    FakeWorkflowRunRepository,
)

# No context manager → lifespan (and thus DB init) does not run. Every
# repository dependency used by the reviews router is overridden below with
# an in-memory fake, so persistence is exercised without a real database.
client = TestClient(app)


def _returning(fake):
    # Zero-argument closure: FastAPI inspects an override's own signature as
    # if it were a route dependency, so a lambda with a default-valued
    # parameter (e.g. `lambda fake=fake: fake`) gets misread as an
    # injectable parameter instead of being called as-is.
    def _get():
        return fake

    return _get


@pytest.fixture(autouse=True)
def fakes():
    email_drafts = FakeEmailDraftRepository()
    workflow_runs = FakeWorkflowRunRepository()
    review_events = FakeReviewEventRepository()

    app.dependency_overrides[get_email_draft_repository] = lambda: email_drafts
    app.dependency_overrides[get_workflow_run_repository] = lambda: workflow_runs
    app.dependency_overrides[get_review_event_repository] = lambda: review_events
    yield {
        "email_drafts": email_drafts,
        "workflow_runs": workflow_runs,
        "review_events": review_events,
    }
    app.dependency_overrides.pop(get_email_draft_repository, None)
    app.dependency_overrides.pop(get_workflow_run_repository, None)
    app.dependency_overrides.pop(get_review_event_repository, None)


@pytest.fixture(autouse=True)
def _fake_user_repository():
    fake_repo = FakeUserRepository()
    app.dependency_overrides[get_user_repository] = _returning(fake_repo)
    yield fake_repo
    app.dependency_overrides.pop(get_user_repository, None)


def _login_as(role: str) -> str:
    """Register a fresh user with ``role`` and return a valid access token."""
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


@pytest.fixture(autouse=True)
def _authenticated_as_admin(_fake_user_repository):
    # Admin may set any review status and comment, so defaulting every
    # request in this file to an admin token preserves all prior assertions
    # now that these endpoints require auth. Role-specific behaviour
    # (reviewer/sales) is covered in tests/test_api_rbac.py.
    token = _login_as("admin")
    client.headers["Authorization"] = f"Bearer {token}"
    yield
    del client.headers["Authorization"]


async def _seed_draft(fakes, **overrides) -> EmailDraft:
    defaults = dict(company_id=uuid.uuid4(), email_body="Hallo,\n\nGrüße")
    defaults.update(overrides)
    return await fakes["email_drafts"].create(EmailDraft(**defaults))


async def _seed_workflow_run(fakes) -> WorkflowRun:
    return await fakes["workflow_runs"].create(
        WorkflowRun(
            company_name="Acme GmbH",
            status="completed",
            input_payload={},
            result_payload={},
        )
    )


# -- POST /reviews/email-drafts/{id}/status ----------------------------------

async def test_email_draft_review_status_endpoint_approves(fakes):
    draft = await _seed_draft(fakes)

    response = client.post(
        f"/api/v1/reviews/email-drafts/{draft.id}/status",
        json={
            "review_status": "approved",
            "reviewer_name": "Henrik",
            "comment": "Entwurf geprüft, aber noch nicht senden.",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email_draft_id"] == str(draft.id)
    assert data["review_status"] == "approved"
    assert data["reviewer_name"] == "Henrik"
    assert data["review_comment"] == "Entwurf geprüft, aber noch nicht senden."
    assert data["reviewed_at"] is not None
    assert "keine e-mail gesendet" in data["message"].lower()
    assert "sent" not in data
    assert "contacted" not in data


async def test_email_draft_review_status_endpoint_rejects_invalid_status(fakes):
    draft = await _seed_draft(fakes)

    response = client.post(
        f"/api/v1/reviews/email-drafts/{draft.id}/status",
        json={"review_status": "sent"},
    )
    assert response.status_code == 422


async def test_email_draft_review_status_endpoint_rejects_whitespace_comment(fakes):
    draft = await _seed_draft(fakes)

    response = client.post(
        f"/api/v1/reviews/email-drafts/{draft.id}/status",
        json={"review_status": "approved", "comment": "   "},
    )
    assert response.status_code == 422


def test_email_draft_review_status_endpoint_returns_404_for_unknown_draft(fakes):
    response = client.post(
        "/api/v1/reviews/email-drafts/00000000-0000-0000-0000-000000000000/status",
        json={"review_status": "approved"},
    )
    assert response.status_code == 404


# -- GET /reviews/email-drafts/{id}/events -----------------------------------

async def test_email_draft_events_endpoint_lists_recorded_events(fakes):
    draft = await _seed_draft(fakes)

    client.post(
        f"/api/v1/reviews/email-drafts/{draft.id}/status",
        json={"review_status": "in_review", "reviewer_name": "Henrik"},
    )
    client.post(
        f"/api/v1/reviews/email-drafts/{draft.id}/status",
        json={"review_status": "approved", "reviewer_name": "Henrik"},
    )

    response = client.get(f"/api/v1/reviews/email-drafts/{draft.id}/events")

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 2
    event_types = {item["event_type"] for item in items}
    assert event_types == {"review_started", "approved"}


def test_email_draft_events_endpoint_returns_404_for_unknown_draft(fakes):
    response = client.get(
        "/api/v1/reviews/email-drafts/00000000-0000-0000-0000-000000000000/events"
    )
    assert response.status_code == 404


# -- POST /reviews/workflows/{id}/comment ------------------------------------

async def test_workflow_comment_endpoint_creates_event(fakes):
    run = await _seed_workflow_run(fakes)

    response = client.post(
        f"/api/v1/reviews/workflows/{run.id}/comment",
        json={"reviewer_name": "Henrik", "comment": "Bitte Nutzenargument prüfen."},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["workflow_id"] == str(run.id)
    assert "event_id" in data
    assert "keine e-mail gesendet" in data["message"].lower()
    assert "sent" not in data


async def test_workflow_comment_endpoint_requires_comment(fakes):
    run = await _seed_workflow_run(fakes)

    response = client.post(
        f"/api/v1/reviews/workflows/{run.id}/comment",
        json={"reviewer_name": "Henrik"},
    )
    assert response.status_code == 422


async def test_workflow_comment_endpoint_rejects_whitespace_comment(fakes):
    run = await _seed_workflow_run(fakes)

    response = client.post(
        f"/api/v1/reviews/workflows/{run.id}/comment",
        json={"comment": "   "},
    )
    assert response.status_code == 422


def test_workflow_comment_endpoint_returns_404_for_unknown_workflow(fakes):
    response = client.post(
        "/api/v1/reviews/workflows/00000000-0000-0000-0000-000000000000/comment",
        json={"comment": "Bitte prüfen."},
    )
    assert response.status_code == 404


# -- GET /reviews/workflows/{id}/events --------------------------------------

async def test_workflow_events_endpoint_lists_recorded_comments(fakes):
    run = await _seed_workflow_run(fakes)

    client.post(
        f"/api/v1/reviews/workflows/{run.id}/comment",
        json={"reviewer_name": "Henrik", "comment": "Erster Kommentar."},
    )
    client.post(
        f"/api/v1/reviews/workflows/{run.id}/comment",
        json={"reviewer_name": "Henrik", "comment": "Zweiter Kommentar."},
    )

    response = client.get(f"/api/v1/reviews/workflows/{run.id}/events")

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 2
    assert all(item["event_type"] == "comment_added" for item in items)


def test_workflow_events_endpoint_returns_404_for_unknown_workflow(fakes):
    response = client.get(
        "/api/v1/reviews/workflows/00000000-0000-0000-0000-000000000000/events"
    )
    assert response.status_code == 404


# -- regression: existing routes remain intact -------------------------------

def test_health_endpoint_still_registered():
    paths = {route.path for route in app.routes}
    assert "/api/v1/health" in paths


def test_workflow_history_endpoints_still_registered():
    paths = {route.path for route in app.routes}
    assert "/api/v1/workflows/sales" in paths
    assert "/api/v1/workflows/sales/runs" in paths
    assert "/api/v1/workflows/sales/runs/{workflow_id}" in paths
    assert "/api/v1/workflows/sales/runs/{workflow_id}/review-status" in paths
    assert "/api/v1/workflows/sales/runs/{workflow_id}/crm-links" in paths


def test_crm_endpoints_still_registered():
    paths = {route.path for route in app.routes}
    assert "/api/v1/companies" in paths
    assert "/api/v1/leads" in paths
    assert "/api/v1/contacts" in paths
    assert "/api/v1/interactions" in paths
    assert "/api/v1/email-drafts" in paths


def test_review_endpoints_are_registered():
    paths = {route.path for route in app.routes}
    assert "/api/v1/reviews/email-drafts/{email_draft_id}/status" in paths
    assert "/api/v1/reviews/email-drafts/{email_draft_id}/events" in paths
    assert "/api/v1/reviews/workflows/{workflow_id}/comment" in paths
    assert "/api/v1/reviews/workflows/{workflow_id}/events" in paths


async def test_no_review_endpoint_sends_email_or_offers_a_send_action(fakes):
    # None of the reviews router's response payloads ever carry a field that
    # would represent sending, and no route path contains "send".
    review_paths = {
        route.path for route in app.routes if str(route.path).startswith("/api/v1/reviews")
    }
    assert all("send" not in path for path in review_paths)

    draft = await _seed_draft(fakes)
    run = await _seed_workflow_run(fakes)

    status_response = client.post(
        f"/api/v1/reviews/email-drafts/{draft.id}/status",
        json={"review_status": "approved", "reviewer_name": "Henrik"},
    )
    assert "sent" not in status_response.json()
    assert "contacted" not in status_response.json()

    comment_response = client.post(
        f"/api/v1/reviews/workflows/{run.id}/comment",
        json={"comment": "Bitte prüfen."},
    )
    assert "sent" not in comment_response.json()
    assert "contacted" not in comment_response.json()
