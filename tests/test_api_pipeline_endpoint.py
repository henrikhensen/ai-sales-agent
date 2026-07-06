"""Integration tests for the CRM Pipeline API.

Covers auth/role gating for GET /api/v1/crm/pipeline (admin/sales/reviewer
all allowed to read) and PATCH /api/v1/crm/leads/{lead_id}/pipeline-status
(admin/sales unrestricted, reviewer restricted to in_review/approved/
rejected), plus regression checks for health, the sales workflow, and CRM
endpoints.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.api.v1.dependencies import get_lead_repository, get_user_repository
from backend.domain.entities.lead import Lead
from backend.domain.enums import LeadSource, PipelineStatus
from backend.main import app
from tests.conftest import FakeLeadRepository, FakeUserRepository

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
def _fake_lead_repository():
    fake_repo = FakeLeadRepository()
    app.dependency_overrides[get_lead_repository] = _returning(fake_repo)
    yield fake_repo
    app.dependency_overrides.pop(get_lead_repository, None)


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


# -- GET /crm/pipeline --------------------------------------------------------

def test_pipeline_board_without_token_returns_401():
    response = client.get("/api/v1/crm/pipeline")
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["admin", "sales", "reviewer"])
def test_pipeline_board_allowed_for_every_role(role):
    response = client.get("/api/v1/crm/pipeline", headers=_auth_header(role))
    assert response.status_code == 200


async def test_pipeline_board_groups_leads_by_status(_fake_lead_repository):
    lead_new = await _fake_lead_repository.create(
        Lead(company_id=uuid.uuid4(), source=LeadSource.OUTBOUND)
    )
    lead_draft = await _fake_lead_repository.create(
        Lead(company_id=uuid.uuid4(), source=LeadSource.OUTBOUND)
    )
    await _fake_lead_repository.update_pipeline_status(
        lead_draft.id, PipelineStatus.DRAFT_CREATED
    )

    response = client.get("/api/v1/crm/pipeline", headers=_auth_header("admin"))

    assert response.status_code == 200
    data = response.json()
    columns_by_status = {column["pipeline_status"]: column for column in data["columns"]}
    assert set(columns_by_status) == {
        "new",
        "research_completed",
        "draft_created",
        "in_review",
        "approved",
        "rejected",
        "archived",
    }
    assert [lead["id"] for lead in columns_by_status["new"]["leads"]] == [str(lead_new.id)]
    assert [lead["id"] for lead in columns_by_status["draft_created"]["leads"]] == [
        str(lead_draft.id)
    ]
    assert columns_by_status["archived"]["leads"] == []


# -- PATCH /crm/leads/{lead_id}/pipeline-status -------------------------------

def test_update_pipeline_status_without_token_returns_401():
    response = client.patch(
        f"/api/v1/crm/leads/{uuid.uuid4()}/pipeline-status",
        json={"pipeline_status": "in_review"},
    )
    assert response.status_code == 401


async def test_update_pipeline_status_returns_404_for_unknown_lead():
    response = client.patch(
        f"/api/v1/crm/leads/{uuid.uuid4()}/pipeline-status",
        json={"pipeline_status": "in_review"},
        headers=_auth_header("admin"),
    )
    assert response.status_code == 404


@pytest.mark.parametrize("role", ["admin", "sales"])
async def test_update_pipeline_status_unrestricted_for_admin_and_sales(
    _fake_lead_repository, role
):
    lead = await _fake_lead_repository.create(
        Lead(company_id=uuid.uuid4(), source=LeadSource.OUTBOUND)
    )

    response = client.patch(
        f"/api/v1/crm/leads/{lead.id}/pipeline-status",
        json={"pipeline_status": "archived"},
        headers=_auth_header(role),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["pipeline_status"] == "archived"
    assert data["pipeline_updated_at"] is not None


@pytest.mark.parametrize("allowed_status", ["in_review", "approved", "rejected"])
async def test_reviewer_may_set_review_adjacent_statuses(_fake_lead_repository, allowed_status):
    lead = await _fake_lead_repository.create(
        Lead(company_id=uuid.uuid4(), source=LeadSource.OUTBOUND)
    )

    response = client.patch(
        f"/api/v1/crm/leads/{lead.id}/pipeline-status",
        json={"pipeline_status": allowed_status},
        headers=_auth_header("reviewer"),
    )

    assert response.status_code == 200
    assert response.json()["pipeline_status"] == allowed_status


@pytest.mark.parametrize("blocked_status", ["new", "research_completed", "draft_created", "archived"])
async def test_reviewer_is_blocked_from_other_statuses(_fake_lead_repository, blocked_status):
    lead = await _fake_lead_repository.create(
        Lead(company_id=uuid.uuid4(), source=LeadSource.OUTBOUND)
    )

    response = client.patch(
        f"/api/v1/crm/leads/{lead.id}/pipeline-status",
        json={"pipeline_status": blocked_status},
        headers=_auth_header("reviewer"),
    )

    assert response.status_code == 403


async def test_update_pipeline_status_never_mentions_sending(_fake_lead_repository):
    lead = await _fake_lead_repository.create(
        Lead(company_id=uuid.uuid4(), source=LeadSource.OUTBOUND)
    )

    response = client.patch(
        f"/api/v1/crm/leads/{lead.id}/pipeline-status",
        json={"pipeline_status": "approved"},
        headers=_auth_header("admin"),
    )

    assert response.status_code == 200
    assert "sent" not in response.text
    assert "email" not in response.text.lower()


# -- Regression -----------------------------------------------------------------

def test_health_endpoint_still_works():
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_sales_workflow_and_crm_endpoints_still_registered():
    paths = {route.path for route in app.routes}
    assert "/api/v1/workflows/sales" in paths
    assert "/api/v1/companies" in paths
    assert "/api/v1/leads" in paths
    assert "/api/v1/crm/pipeline" in paths
    assert "/api/v1/crm/leads/{lead_id}/pipeline-status" in paths
