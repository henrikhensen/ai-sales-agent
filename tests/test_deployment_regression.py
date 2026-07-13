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


# -- CORS_ALLOWED_ORIGINS robust parsing (Railway misconfiguration fix) --------------


def test_cors_allowed_origins_list_parses_single_origin_string():
    """A single origin (no comma at all) must parse to a one-item list, not
    be silently dropped or split into individual characters."""
    settings = Settings(CORS_ALLOWED_ORIGINS="https://frontend-production.up.railway.app")
    assert settings.cors_allowed_origins_list == [
        "https://frontend-production.up.railway.app"
    ]


def test_cors_allowed_origins_list_parses_csv():
    settings = Settings(
        CORS_ALLOWED_ORIGINS="https://a.example.com,https://b.example.com,https://c.example.com"
    )
    assert settings.cors_allowed_origins_list == [
        "https://a.example.com",
        "https://b.example.com",
        "https://c.example.com",
    ]


def test_cors_allowed_origins_list_parses_json_array():
    """A JSON array string (a common copy-paste mistake when the value
    looks like a Python/JS list literal) must parse the same as CSV."""
    settings = Settings(
        CORS_ALLOWED_ORIGINS='["https://a.example.com", "https://b.example.com"]'
    )
    assert settings.cors_allowed_origins_list == [
        "https://a.example.com",
        "https://b.example.com",
    ]


def test_cors_allowed_origins_list_strips_trailing_slash():
    """A browser's Origin header never has a trailing slash — a stray one
    in the configured value must not silently break every real match."""
    settings = Settings(CORS_ALLOWED_ORIGINS="https://frontend.up.railway.app/")
    assert settings.cors_allowed_origins_list == ["https://frontend.up.railway.app"]


def test_cors_allowed_origins_list_strips_whitespace_and_newlines():
    settings = Settings(
        CORS_ALLOWED_ORIGINS="  https://a.example.com \n https://b.example.com  "
    )
    assert settings.cors_allowed_origins_list == [
        "https://a.example.com",
        "https://b.example.com",
    ]


def test_cors_allowed_origins_list_deduplicates():
    settings = Settings(
        CORS_ALLOWED_ORIGINS="https://a.example.com, https://a.example.com"
    )
    assert settings.cors_allowed_origins_list == ["https://a.example.com"]


def test_frontend_public_url_is_folded_into_cors_origins_when_set():
    """FRONTEND_PUBLIC_URL must be usable as the single source of truth for
    the frontend's own origin — it should never need to be duplicated into
    CORS_ALLOWED_ORIGINS by hand once it's set to a real (non-default) URL."""
    settings = Settings(
        CORS_ALLOWED_ORIGINS="https://backend-admin-tool.example.com",
        FRONTEND_PUBLIC_URL="https://frontend-production.up.railway.app/",
    )
    assert settings.cors_allowed_origins_list == [
        "https://backend-admin-tool.example.com",
        "https://frontend-production.up.railway.app",
    ]


def test_frontend_public_url_default_is_not_auto_added():
    """Regression guard: if FRONTEND_PUBLIC_URL is left at its own
    localhost default, it must NOT be folded in — otherwise an entirely
    unconfigured production deploy (CORS_ALLOWED_ORIGINS empty) would
    silently resolve to a non-empty origins list and skip the hard-fail in
    production_checks.validate_production_config."""
    settings = Settings(CORS_ALLOWED_ORIGINS="")
    assert settings.cors_allowed_origins_list == []


def test_cors_preflight_allows_origin_from_json_array_config():
    """End-to-end: a JSON-array-formatted CORS_ALLOWED_ORIGINS must still
    result in FastAPI's CORSMiddleware actually allowing that origin — built
    against a throwaway app (not backend.main) so this doesn't depend on
    reloading the real app/settings module singletons."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    settings = Settings(
        CORS_ALLOWED_ORIGINS='["https://frontend-production.up.railway.app"]'
    )
    probe_app = FastAPI()
    probe_app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @probe_app.get("/probe")
    def _probe():
        return {"ok": True}

    probe_client = TestClient(probe_app)
    response = probe_client.options(
        "/probe",
        headers={
            "Origin": "https://frontend-production.up.railway.app",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert (
        response.headers.get("access-control-allow-origin")
        == "https://frontend-production.up.railway.app"
    )


def test_healthcheck_endpoint_has_no_auth_dependency():
    """GET /api/v1/health must stay publicly reachable (no auth) — a
    protected health check would make every frontend health probe fail
    with 401 regardless of CORS, which would look identical to "backend
    down" from the browser and defeat the whole point of a status check."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] in ("ok", "degraded")


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
