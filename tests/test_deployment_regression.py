"""Deployment-readiness regression checks.

Most individual features already have their own dedicated test files
(auth, sales workflow, do-not-contact, email integration, reply tracking);
this file covers the specific checklist items from the deployment/
monitoring/backup phase that don't already live elsewhere: CORS parsing,
backup/restore script existence, and .gitignore coverage. It also smoke-
tests that the core features these deployment changes must not break are
still registered and reachable.
"""

import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from backend.shared.config import Settings

client = TestClient(app)

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_cors_allowed_origins_list_parses_multiple_origins():
    settings = Settings(
        CORS_ALLOWED_ORIGINS="https://a.example.com, https://b.example.com"
    )
    assert settings.cors_allowed_origins_list == [
        "https://a.example.com",
        "https://b.example.com",
    ]


def test_cors_preflight_allows_configured_origin():
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_backup_and_restore_scripts_exist_for_both_shells():
    scripts_dir = REPO_ROOT / "scripts"
    for name in (
        "backup_db.ps1",
        "backup_db.sh",
        "restore_db.ps1",
        "restore_db.sh",
    ):
        assert (scripts_dir / name).is_file(), name


def _git_check_ignore(path: str) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "-q", path],
        cwd=REPO_ROOT,
        check=False,
    )
    return result.returncode == 0


def test_env_file_is_gitignored():
    assert _git_check_ignore(".env")


def test_backup_directory_and_sql_dumps_are_gitignored():
    assert _git_check_ignore("backups/example_dump.sql")
    assert _git_check_ignore("some_dump.sql")


def test_log_files_are_gitignored():
    assert _git_check_ignore("backend.log")


# -- regression: existing features remain registered and reachable --------------


def test_health_endpoint_still_works():
    assert client.get("/api/v1/health").status_code == 200


def test_auth_endpoints_still_registered():
    paths = {route.path for route in app.routes}
    assert "/api/v1/auth/register" in paths
    assert "/api/v1/auth/login" in paths


def test_sales_workflow_endpoint_still_registered():
    paths = {route.path for route in app.routes}
    assert "/api/v1/workflows/sales" in paths


def test_do_not_contact_endpoints_still_registered():
    paths = {route.path for route in app.routes}
    assert "/api/v1/compliance/do-not-contact" in paths
    assert "/api/v1/compliance/do-not-contact/check" in paths


def test_external_draft_integration_still_mock_by_default():
    settings = Settings()
    assert settings.email_integration_provider == "mock"
    assert settings.email_integration_enable_real_drafts is False


def test_reply_tracking_still_mock_by_default():
    settings = Settings()
    assert settings.reply_tracking_provider == "mock"
    assert settings.reply_tracking_enable_real_reads is False


def test_llm_still_mock_by_default():
    settings = Settings()
    assert settings.llm_provider == "mock"
    assert settings.llm_enable_real_calls is False


def test_no_send_endpoint_exists_anywhere():
    paths = [route.path for route in app.routes]
    assert not any("send" in path.lower() for path in paths)
