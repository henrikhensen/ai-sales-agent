"""Integration tests for the Legal/Compliance Pack API.

Covers Compliance Documents (all logged-in roles), Data Retention
Policies/Runs, Data Export, and Data Subject Requests (admin-only
throughout), plus the standing regression checks: no secrets ever
returned, no send-capable endpoint anywhere, and unauthenticated access
is rejected.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.api.v1.dependencies import (
    get_audit_log_repository,
    get_company_repository,
    get_contact_repository,
    get_data_retention_policy_repository,
    get_data_retention_run_repository,
    get_data_subject_request_repository,
    get_do_not_contact_repository,
    get_email_draft_repository,
    get_external_email_draft_repository,
    get_lead_candidate_repository,
    get_outreach_dispatch_repository,
    get_outreach_queue_item_repository,
    get_qualification_result_repository,
    get_reply_repository,
    get_user_repository,
    get_workflow_run_repository,
)
from backend.main import app
from tests.conftest import (
    FakeAuditLogRepository,
    FakeCompanyRepository,
    FakeContactRepository,
    FakeDataRetentionPolicyRepository,
    FakeDataRetentionRunRepository,
    FakeDataSubjectRequestRepository,
    FakeDoNotContactRepository,
    FakeEmailDraftRepository,
    FakeExternalEmailDraftRepository,
    FakeLeadCandidateRepository,
    FakeOutreachDispatchRepository,
    FakeOutreachQueueItemRepository,
    FakeQualificationResultRepository,
    FakeReplyRepository,
    FakeUserRepository,
    FakeWorkflowRunRepository,
)

client = TestClient(app)


def _returning(fake):
    def _get():
        return fake

    return _get


@pytest.fixture(autouse=True)
def _fake_repositories():
    overrides = {
        get_user_repository: FakeUserRepository(),
        get_audit_log_repository: FakeAuditLogRepository(),
        get_data_retention_policy_repository: FakeDataRetentionPolicyRepository(),
        get_data_retention_run_repository: FakeDataRetentionRunRepository(),
        get_data_subject_request_repository: FakeDataSubjectRequestRepository(),
        get_contact_repository: FakeContactRepository(),
        get_company_repository: FakeCompanyRepository(),
        get_email_draft_repository: FakeEmailDraftRepository(),
        get_reply_repository: FakeReplyRepository(),
        get_workflow_run_repository: FakeWorkflowRunRepository(),
        get_do_not_contact_repository: FakeDoNotContactRepository(),
        get_external_email_draft_repository: FakeExternalEmailDraftRepository(),
        get_outreach_queue_item_repository: FakeOutreachQueueItemRepository(),
        get_outreach_dispatch_repository: FakeOutreachDispatchRepository(),
        get_qualification_result_repository: FakeQualificationResultRepository(),
        get_lead_candidate_repository: FakeLeadCandidateRepository(),
    }
    for dependency, fake in overrides.items():
        app.dependency_overrides[dependency] = _returning(fake)
    yield overrides
    for dependency in overrides:
        app.dependency_overrides.pop(dependency, None)


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


# -- compliance documents ------------------------------------------------------------


def test_documents_ohne_token_gibt_401():
    response = client.get("/api/v1/compliance/documents")
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["admin", "sales", "reviewer"])
def test_documents_erlaubt_fuer_jede_rolle(role):
    response = client.get("/api/v1/compliance/documents", headers=_auth_header(role))
    assert response.status_code == 200
    body = response.json()
    assert len(body["documents"]) == 8


def test_documents_behaupten_keine_rechtsberatung():
    response = client.get("/api/v1/compliance/documents", headers=_auth_header("admin"))
    assert "not legal advice" in response.text.lower()


# -- data retention: policies ---------------------------------------------------------


@pytest.mark.parametrize("role", ["sales", "reviewer"])
def test_retention_policies_verboten_fuer_nicht_admin(role):
    response = client.get(
        "/api/v1/compliance/data-retention/policies", headers=_auth_header(role)
    )
    assert response.status_code == 403


def test_retention_policy_kann_erstellt_werden():
    response = client.post(
        "/api/v1/compliance/data-retention/policies",
        json={"name": "Old Leads", "entity_type": "lead", "retention_days": 365},
        headers=_auth_header("admin"),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["action"] == "anonymize"


def test_retention_policy_kann_aktualisiert_werden():
    created = client.post(
        "/api/v1/compliance/data-retention/policies",
        json={"name": "Old Leads", "entity_type": "lead", "retention_days": 365},
        headers=_auth_header("admin"),
    ).json()
    response = client.patch(
        f"/api/v1/compliance/data-retention/policies/{created['id']}",
        json={"retention_days": 180},
        headers=_auth_header("admin"),
    )
    assert response.status_code == 200
    assert response.json()["retention_days"] == 180


def test_retention_policy_kann_deaktiviert_werden():
    created = client.post(
        "/api/v1/compliance/data-retention/policies",
        json={"name": "Old Leads", "entity_type": "lead", "retention_days": 365},
        headers=_auth_header("admin"),
    ).json()
    response = client.patch(
        f"/api/v1/compliance/data-retention/policies/{created['id']}/deactivate",
        headers=_auth_header("admin"),
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_retention_dry_run_gibt_200_und_veraendert_nichts():
    created = client.post(
        "/api/v1/compliance/data-retention/policies",
        json={"name": "Old Leads", "entity_type": "lead", "retention_days": 365},
        headers=_auth_header("admin"),
    ).json()
    response = client.post(
        f"/api/v1/compliance/data-retention/policies/{created['id']}/dry-run",
        headers=_auth_header("admin"),
    )
    assert response.status_code == 200
    assert response.json()["dry_run"] is True
    assert response.json()["total_processed"] == 0


def test_retention_run_braucht_admin():
    created = client.post(
        "/api/v1/compliance/data-retention/policies",
        json={"name": "Old Leads", "entity_type": "lead", "retention_days": 365},
        headers=_auth_header("admin"),
    ).json()
    for role in ("sales", "reviewer"):
        response = client.post(
            f"/api/v1/compliance/data-retention/policies/{created['id']}/run",
            json={"confirm": True},
            headers=_auth_header(role),
        )
        assert response.status_code == 403


def test_retention_run_braucht_explizite_bestaetigung():
    created = client.post(
        "/api/v1/compliance/data-retention/policies",
        json={"name": "Old Leads", "entity_type": "lead", "retention_days": 365},
        headers=_auth_header("admin"),
    ).json()
    response = client.post(
        f"/api/v1/compliance/data-retention/policies/{created['id']}/run",
        json={"confirm": False},
        headers=_auth_header("admin"),
    )
    assert response.status_code == 400


def test_retention_runs_koennen_gelistet_werden():
    created = client.post(
        "/api/v1/compliance/data-retention/policies",
        json={"name": "Old Leads", "entity_type": "lead", "retention_days": 365},
        headers=_auth_header("admin"),
    ).json()
    client.post(
        f"/api/v1/compliance/data-retention/policies/{created['id']}/dry-run",
        headers=_auth_header("admin"),
    )
    response = client.get(
        "/api/v1/compliance/data-retention/runs", headers=_auth_header("admin")
    )
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1


# -- data export ------------------------------------------------------------------------


def test_data_export_funktioniert():
    response = client.post(
        "/api/v1/compliance/data-export",
        json={"email": "someone@example.com"},
        headers=_auth_header("admin"),
    )
    assert response.status_code == 200
    body = response.json()
    assert "message" in body


def test_data_export_verboten_fuer_reviewer():
    response = client.post(
        "/api/v1/compliance/data-export",
        json={"email": "someone@example.com"},
        headers=_auth_header("reviewer"),
    )
    assert response.status_code == 403


def test_data_export_enthaelt_keine_secrets():
    response = client.post(
        "/api/v1/compliance/data-export",
        json={"domain": "example.com"},
        headers=_auth_header("admin"),
    )
    body_text = response.text.lower()
    for forbidden in ("token", "secret", "api_key", "client_secret", "password"):
        assert forbidden not in body_text


# -- data subject requests ---------------------------------------------------------------


def test_data_request_kann_erstellt_werden():
    response = client.post(
        "/api/v1/compliance/data-requests",
        json={"request_type": "export", "subject_email": "someone@example.com"},
        headers=_auth_header("admin"),
    )
    assert response.status_code == 201


def test_data_request_verboten_fuer_sales_und_reviewer():
    for role in ("sales", "reviewer"):
        response = client.post(
            "/api/v1/compliance/data-requests",
            json={"request_type": "export", "subject_email": "someone@example.com"},
            headers=_auth_header(role),
        )
        assert response.status_code == 403


def test_data_request_kann_exportieren():
    created = client.post(
        "/api/v1/compliance/data-requests",
        json={"request_type": "export", "subject_email": "someone@example.com"},
        headers=_auth_header("admin"),
    ).json()
    response = client.post(
        f"/api/v1/compliance/data-requests/{created['id']}/export",
        headers=_auth_header("admin"),
    )
    assert response.status_code == 200
    assert response.json()["export"] is not None


def test_data_request_kann_abgeschlossen_werden():
    created = client.post(
        "/api/v1/compliance/data-requests",
        json={"request_type": "correction", "subject_email": "someone@example.com"},
        headers=_auth_header("admin"),
    ).json()
    response = client.post(
        f"/api/v1/compliance/data-requests/{created['id']}/complete",
        json={},
        headers=_auth_header("admin"),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


# -- regression: no send capability, no secrets ------------------------------------------


def test_kein_send_endpoint_unter_compliance():
    for route in app.routes:
        path = getattr(route, "path", "")
        if path.startswith("/api/v1/compliance"):
            assert "send" not in path.lower() or "sending" in path.lower()
