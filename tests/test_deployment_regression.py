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


# -- Phase 35: production deployment finalization ------------------------------------


def test_compose_files_introduce_no_new_automated_dispatch_service():
    """Production Config Finalization must not smuggle in a scheduler,
    worker, or cron service that could send/dispatch anything
    automatically — only backend/frontend/postgres/redis, exactly as
    before this phase. Parsed with a plain top-level-key scan (no PyYAML
    dependency) since compose files are indented consistently (service
    names are the only lines indented exactly two spaces under
    `services:`)."""
    expected_services = {"backend", "frontend", "postgres", "redis"}
    for filename in ("docker-compose.yml", "docker-compose.prod.yml"):
        lines = (REPO_ROOT / filename).read_text(encoding="utf-8").splitlines()
        in_services = False
        found: set[str] = set()
        for line in lines:
            if line.rstrip() == "services:":
                in_services = True
                continue
            if not in_services:
                continue
            if line.startswith("  ") and not line.startswith("   ") and line.strip():
                found.add(line.strip().rstrip(":"))
            elif line and not line.startswith(" "):
                break  # left the `services:` block
        assert found == expected_services, filename


# -- Phase 36: first customer beta package -------------------------------------------


def test_seed_demo_data_script_never_calls_a_send_or_dispatch_endpoint():
    """The Beta demo seed script must only ever call read/create endpoints
    that already exist and are already safety-gated — never anything
    send- or dispatch-shaped."""
    script = (REPO_ROOT / "scripts" / "seed_demo_data.py").read_text(encoding="utf-8")
    lowered = script.lower()
    assert "/send" not in lowered
    assert "dispatch" not in lowered
    assert "outreach/dispatch" not in lowered


def test_beta_onboarding_doc_exists_and_states_no_automatic_sending():
    doc = (REPO_ROOT / "BETA_ONBOARDING.md").read_text(encoding="utf-8")
    assert "no send button" in doc.lower() or "no automatic sending" in doc.lower()


def test_onboarding_step_order_still_ends_in_completion_with_no_send_step():
    from backend.application.onboarding.schemas import ONBOARDING_STEP_ORDER

    assert ONBOARDING_STEP_ORDER[-1] == "completion"
    assert not any("send" in step for step in ONBOARDING_STEP_ORDER)


def test_production_hard_fail_never_bypasses_do_not_contact_or_review():
    """The new validate_production_config() only ever concerns startup
    secrets — it must not reference/gate compliance or review settings,
    which must always remain independently enforced."""
    import inspect

    from backend.shared import production_checks

    source = inspect.getsource(production_checks.validate_production_config)
    assert "do_not_contact" not in source.lower()
    assert "review" not in source.lower()


def test_alembic_present_but_init_database_still_only_creates_tables():
    """Alembic is available for schema changes, but the automatic
    startup path (init_database) must remain additive-only — it must
    never call DROP or ALTER, which could destroy data on a routine
    restart."""
    source = (
        REPO_ROOT / "backend" / "infrastructure" / "database" / "session.py"
    ).read_text(encoding="utf-8")
    assert "create_all" in source
    assert "drop_all" not in source
