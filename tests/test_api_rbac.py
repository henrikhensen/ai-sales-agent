"""Integration tests for Role-Based Access Control across the API.

Covers the full role matrix from Phase 16A: admin/reviewer/sales access to
Users, Reviews, Workflows, and CRM endpoints. Uses the TestClient directly
against in-memory fakes — no real database, no real email, no external
service of any kind.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.api.v1.dependencies import (
    get_company_repository,
    get_contact_repository,
    get_do_not_contact_repository,
    get_email_draft_repository,
    get_interaction_repository,
    get_lead_repository,
    get_review_event_repository,
    get_user_repository,
    get_workflow_run_repository,
)
from backend.domain.entities.email_draft import EmailDraft
from backend.domain.entities.workflow_run import WorkflowRun
from backend.main import app
from tests.conftest import (
    FakeCompanyRepository,
    FakeContactRepository,
    FakeDoNotContactRepository,
    FakeEmailDraftRepository,
    FakeInteractionRepository,
    FakeLeadRepository,
    FakeReviewEventRepository,
    FakeUserRepository,
    FakeWorkflowRunRepository,
)

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
    repos = {
        get_user_repository: FakeUserRepository(),
        get_workflow_run_repository: FakeWorkflowRunRepository(),
        get_email_draft_repository: FakeEmailDraftRepository(),
        get_review_event_repository: FakeReviewEventRepository(),
        get_company_repository: FakeCompanyRepository(),
        get_lead_repository: FakeLeadRepository(),
        get_contact_repository: FakeContactRepository(),
        get_interaction_repository: FakeInteractionRepository(),
        get_do_not_contact_repository: FakeDoNotContactRepository(),
    }
    for dependency, fake in repos.items():
        app.dependency_overrides[dependency] = _returning(fake)
    yield repos
    for dependency in repos:
        app.dependency_overrides.pop(dependency, None)


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


def _auth_header(role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {_login_as(role)}"}


async def _seed_draft(fakes) -> EmailDraft:
    return await fakes[get_email_draft_repository].create(
        EmailDraft(company_id=uuid.uuid4(), email_body="Hallo,\n\nGrüße")
    )


async def _seed_workflow_run(fakes) -> WorkflowRun:
    return await fakes[get_workflow_run_repository].create(
        WorkflowRun(
            company_name="Acme GmbH",
            status="completed",
            input_payload={},
            result_payload={},
        )
    )


# -- GET /api/v1/users --------------------------------------------------------

def test_list_users_without_token_returns_401():
    response = client.get("/api/v1/users")
    assert response.status_code == 401


def test_list_users_as_sales_returns_403():
    response = client.get("/api/v1/users", headers=_auth_header("sales"))
    assert response.status_code == 403


def test_list_users_as_reviewer_returns_403():
    response = client.get("/api/v1/users", headers=_auth_header("reviewer"))
    assert response.status_code == 403


def test_list_users_as_admin_returns_200():
    response = client.get("/api/v1/users", headers=_auth_header("admin"))
    assert response.status_code == 200


# -- Review status change: admin/reviewer allowed, sales blocked ------------

async def test_email_draft_review_approve_as_reviewer_is_allowed(fakes):
    draft = await _seed_draft(fakes)

    response = client.post(
        f"/api/v1/reviews/email-drafts/{draft.id}/status",
        json={"review_status": "approved"},
        headers=_auth_header("reviewer"),
    )

    assert response.status_code == 200
    assert response.json()["review_status"] == "approved"


async def test_email_draft_review_approve_as_admin_is_allowed(fakes):
    draft = await _seed_draft(fakes)

    response = client.post(
        f"/api/v1/reviews/email-drafts/{draft.id}/status",
        json={"review_status": "approved"},
        headers=_auth_header("admin"),
    )

    assert response.status_code == 200


async def test_email_draft_review_approve_as_sales_returns_403(fakes):
    draft = await _seed_draft(fakes)

    response = client.post(
        f"/api/v1/reviews/email-drafts/{draft.id}/status",
        json={"review_status": "approved"},
        headers=_auth_header("sales"),
    )

    assert response.status_code == 403


async def test_email_draft_review_status_without_token_returns_401(fakes):
    draft = await _seed_draft(fakes)

    response = client.post(
        f"/api/v1/reviews/email-drafts/{draft.id}/status",
        json={"review_status": "approved"},
    )

    assert response.status_code == 401


async def test_email_draft_review_status_defaults_reviewer_name_from_current_user(fakes):
    draft = await _seed_draft(fakes)
    token = _login_as("reviewer")

    response = client.post(
        f"/api/v1/reviews/email-drafts/{draft.id}/status",
        json={"review_status": "in_review"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["reviewer_name"]  # defaulted from the logged-in user


# -- Workflow comments: every role allowed -----------------------------------

@pytest.mark.parametrize("role", ["admin", "reviewer", "sales"])
async def test_workflow_comment_allowed_for_every_role(fakes, role):
    run = await _seed_workflow_run(fakes)

    response = client.post(
        f"/api/v1/reviews/workflows/{run.id}/comment",
        json={"comment": "Bitte pruefen."},
        headers=_auth_header(role),
    )

    assert response.status_code == 200


def test_workflow_comment_without_token_returns_401():
    response = client.post(
        f"/api/v1/reviews/workflows/{uuid.uuid4()}/comment",
        json={"comment": "Bitte pruefen."},
    )
    assert response.status_code == 401


# -- Workflow: starting allowed for admin/sales(/reviewer) -------------------

def test_start_sales_workflow_as_sales_is_allowed():
    response = client.post(
        "/api/v1/workflows/sales",
        json={"company_name": "Acme GmbH", "product_or_service_offered": "Freight API"},
        headers=_auth_header("sales"),
    )
    assert response.status_code == 200


def test_start_sales_workflow_as_admin_is_allowed():
    response = client.post(
        "/api/v1/workflows/sales",
        json={"company_name": "Acme GmbH", "product_or_service_offered": "Freight API"},
        headers=_auth_header("admin"),
    )
    assert response.status_code == 200


def test_start_sales_workflow_without_token_returns_401():
    response = client.post(
        "/api/v1/workflows/sales",
        json={"company_name": "Acme GmbH", "product_or_service_offered": "Freight API"},
    )
    assert response.status_code == 401


# -- Workflow History: every role allowed to read ----------------------------

@pytest.mark.parametrize("role", ["admin", "reviewer", "sales"])
def test_list_workflow_history_allowed_for_every_role(role):
    response = client.get(
        "/api/v1/workflows/sales/runs", headers=_auth_header(role)
    )
    assert response.status_code == 200


@pytest.mark.parametrize("role", ["admin", "reviewer", "sales"])
async def test_get_workflow_run_detail_allowed_for_every_role(fakes, role):
    run = await _seed_workflow_run(fakes)

    response = client.get(
        f"/api/v1/workflows/sales/runs/{run.id}", headers=_auth_header(role)
    )
    assert response.status_code == 200


# -- WorkflowRun review-status: sales blocked from approved/rejected only ---

async def test_workflow_run_review_status_sales_blocked_from_approved(fakes):
    run = await _seed_workflow_run(fakes)

    response = client.patch(
        f"/api/v1/workflows/sales/runs/{run.id}/review-status",
        json={"review_status": "approved"},
        headers=_auth_header("sales"),
    )

    assert response.status_code == 403


async def test_workflow_run_review_status_sales_blocked_from_rejected(fakes):
    run = await _seed_workflow_run(fakes)

    response = client.patch(
        f"/api/v1/workflows/sales/runs/{run.id}/review-status",
        json={"review_status": "rejected"},
        headers=_auth_header("sales"),
    )

    assert response.status_code == 403


async def test_workflow_run_review_status_sales_allowed_for_reviewed(fakes):
    run = await _seed_workflow_run(fakes)

    response = client.patch(
        f"/api/v1/workflows/sales/runs/{run.id}/review-status",
        json={"review_status": "reviewed"},
        headers=_auth_header("sales"),
    )

    assert response.status_code == 200


async def test_workflow_run_review_status_reviewer_allowed_for_approved(fakes):
    run = await _seed_workflow_run(fakes)

    response = client.patch(
        f"/api/v1/workflows/sales/runs/{run.id}/review-status",
        json={"review_status": "approved"},
        headers=_auth_header("reviewer"),
    )

    assert response.status_code == 200


async def test_workflow_run_review_status_admin_allowed_for_rejected(fakes):
    run = await _seed_workflow_run(fakes)

    response = client.patch(
        f"/api/v1/workflows/sales/runs/{run.id}/review-status",
        json={"review_status": "rejected"},
        headers=_auth_header("admin"),
    )

    assert response.status_code == 200


# -- CRM read endpoints: every role allowed ----------------------------------

@pytest.mark.parametrize(
    "path",
    ["/api/v1/companies", "/api/v1/leads", "/api/v1/contacts", "/api/v1/interactions",
     "/api/v1/email-drafts"],
)
@pytest.mark.parametrize("role", ["admin", "reviewer", "sales"])
def test_crm_read_endpoints_allowed_for_every_role(path, role):
    response = client.get(path, headers=_auth_header(role))
    assert response.status_code == 200


@pytest.mark.parametrize(
    "path",
    ["/api/v1/companies", "/api/v1/leads", "/api/v1/contacts", "/api/v1/interactions",
     "/api/v1/email-drafts"],
)
def test_crm_read_endpoints_without_token_return_401(path):
    response = client.get(path)
    assert response.status_code == 401


# -- CRM write endpoints: admin/sales allowed, reviewer blocked --------------

def test_create_company_as_reviewer_returns_403():
    response = client.post(
        "/api/v1/companies",
        json={"name": "Acme GmbH"},
        headers=_auth_header("reviewer"),
    )
    assert response.status_code == 403


def test_create_company_as_sales_is_allowed():
    response = client.post(
        "/api/v1/companies",
        json={"name": "Acme GmbH"},
        headers=_auth_header("sales"),
    )
    assert response.status_code == 201


def test_create_company_as_admin_is_allowed():
    response = client.post(
        "/api/v1/companies",
        json={"name": "Acme GmbH"},
        headers=_auth_header("admin"),
    )
    assert response.status_code == 201


# -- Regression: unrelated public endpoints keep working ---------------------

def test_health_endpoint_still_works_without_auth():
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_register_endpoint_still_works():
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "regression@example.com", "password": "testpassword123"},
    )
    assert response.status_code == 201


def test_login_endpoint_still_works():
    client.post(
        "/api/v1/auth/register",
        json={"email": "regression-login@example.com", "password": "testpassword123"},
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "regression-login@example.com", "password": "testpassword123"},
    )
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


def test_agent_endpoint_still_public_without_auth():
    # Agents endpoints are deliberately left unauthenticated this phase so
    # the still-public /agents/* frontend pages keep working.
    response = client.post(
        "/api/v1/agents/lead-research", json={"company_name": "Acme GmbH"}
    )
    assert response.status_code == 200
