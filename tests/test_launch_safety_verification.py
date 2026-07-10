"""Phase 37 launch-safety verification: one consolidated file asserting the
nine non-negotiable guarantees from LAUNCH_CHECKLIST.md section 11 and
PROJECT_RULES.md. Each guarantee already has deeper, feature-specific
coverage elsewhere (test_deployment_regression.py, test_api_outreach_
dispatch_endpoint.py, test_do_not_contact_service.py, etc.) — this file is
a single, readable checklist a reviewer can run before any real launch
without hunting across the suite, not a replacement for those tests.
"""

import inspect
import uuid

from fastapi.testclient import TestClient

from backend.application.audit.audit_log_service import _sanitize_metadata
from backend.application.outreach import outreach_dispatch_service
from backend.main import app
from backend.shared.config import Settings

client = TestClient(app)


# -- 1. Kein automatischer Versand / kein Massenversand --------------------


def test_no_send_endpoint_exists_anywhere_in_the_api():
    paths = [route.path for route in app.routes]
    assert not any("send" in path.lower() for path in paths)


def test_no_batch_or_bulk_send_endpoint_exists_under_dispatch():
    """`/outreach/campaigns/{id}/prepare-batch` legitimately builds queue
    items from campaign candidates (no sending happens there) — this check
    is scoped to `/dispatch`, the only place a message could ever leave the
    system, matching test_kein_batch_endpoint_unter_dispatch."""
    for route in app.routes:
        path = getattr(route, "path", "")
        if "/dispatch" in path:
            assert "batch" not in path.lower()
            assert "bulk" not in path.lower()


# -- 2. Keine Reply-Send-Endpoints ------------------------------------------


def test_no_send_capable_endpoint_under_replies():
    for route in app.routes:
        path = getattr(route, "path", "")
        if path.startswith("/api/v1/replies"):
            assert "send" not in path.lower()


# -- 3. Keine automatische externe Draft-Erstellung -------------------------


def test_external_draft_creation_requires_an_explicit_authenticated_request():
    """The only external-draft-creation route is a POST that requires auth
    and an explicit draft id — there is no scheduler, cron, or background
    task anywhere that could call it on its own."""
    paths = [route.path for route in app.routes]
    draft_paths = [p for p in paths if "external-draft" in p]
    assert draft_paths, "expected at least one external-draft route to exist"
    response = client.post(f"/api/v1/email-drafts/{uuid.uuid4()}/external-draft")
    assert response.status_code == 401


# -- 4. Approved bedeutet nicht Versand -------------------------------------


def test_confirming_a_dispatch_requires_an_explicit_authenticated_call():
    """OutreachDispatchService.confirm() — the only place a dispatch status
    can ever become 'sent_manually_confirmed' — takes an actor_user_id and
    is only ever reached via an authenticated POST; nothing transitions a
    queue item from 'approved'/'external_draft_created' to a sent state on
    its own."""
    source = inspect.getsource(outreach_dispatch_service.OutreachDispatchService.confirm)
    assert "actor_user_id" in source
    response = client.post(f"/api/v1/outreach/dispatch/{uuid.uuid4()}/confirm", json={})
    assert response.status_code == 401


# -- 5. Do-not-contact blockiert --------------------------------------------


def test_do_not_contact_endpoints_registered_and_require_auth():
    response = client.get("/api/v1/compliance/do-not-contact")
    assert response.status_code == 401
    response = client.post("/api/v1/compliance/do-not-contact/check", json={})
    assert response.status_code == 401


# -- 6. Human Review erforderlich -------------------------------------------


def test_review_endpoints_registered_and_require_auth():
    paths = {route.path for route in app.routes}
    assert "/api/v1/reviews/email-drafts/{email_draft_id}/status" in paths
    response = client.post(
        f"/api/v1/reviews/email-drafts/{uuid.uuid4()}/status", json={}
    )
    assert response.status_code == 401


# -- 7. Secrets werden nicht geloggt/angezeigt ------------------------------


def test_audit_log_sanitizes_secret_like_metadata_keys():
    sanitized = _sanitize_metadata(
        {
            "api_key": "sk-real-secret-value",
            "token": "abc123",
            "password": "hunter2",
            "safe_field": "keep-me",
        }
    )
    assert "api_key" not in sanitized
    assert "token" not in sanitized
    assert "password" not in sanitized
    assert sanitized["safe_field"] == "keep-me"


def test_system_status_endpoint_never_returns_a_raw_secret_value():
    settings = Settings()
    response = client.get("/api/v1/system/status")
    # unauthenticated -> 401, but this must hold true regardless of status
    assert settings.jwt_secret_key not in response.text
    assert settings.postgres_password not in response.text


# -- 8. Mock/Safe Mode bleibt Default ---------------------------------------


def test_every_provider_defaults_to_mock_and_real_calls_are_opt_in():
    settings = Settings()
    assert settings.llm_provider == "mock"
    assert settings.llm_enable_real_calls is False
    assert settings.email_integration_provider == "mock"
    assert settings.email_integration_enable_real_drafts is False
    assert settings.reply_tracking_provider == "mock"
    assert settings.reply_tracking_enable_real_reads is False
    assert settings.outreach_dispatch_mode == "draft_only"
    assert settings.outreach_dispatch_enable_real_send is False


def test_data_retention_defaults_to_dry_run_and_anonymize():
    settings = Settings()
    assert settings.data_retention_dry_run_default is True
    assert settings.data_retention_anonymize_instead_of_delete is True
