"""Tests for backend/shared/production_checks.py.

Pure-function tests: no database, no Redis, no HTTP client needed.
"""

from backend.shared.config import Settings
from backend.shared.production_checks import get_production_warnings


def _settings(**overrides) -> Settings:
    defaults: dict = dict(
        APP_ENV="production",
        JWT_SECRET_KEY="a-real-random-secret-value",
        CORS_ALLOWED_ORIGINS="https://app.example.com",
        POSTGRES_PASSWORD="a-real-random-password",
        DEBUG=False,
    )
    defaults.update(overrides)
    return Settings(**defaults)


def test_no_warnings_in_development_regardless_of_settings():
    settings = _settings(
        APP_ENV="development",
        JWT_SECRET_KEY="dev-only-insecure-secret-change-me",
        CORS_ALLOWED_ORIGINS="*",
    )
    assert get_production_warnings(settings) == []


def test_no_warnings_for_a_fully_configured_production_settings():
    assert get_production_warnings(_settings()) == []


def test_warns_on_default_jwt_secret_in_production():
    settings = _settings(JWT_SECRET_KEY="dev-only-insecure-secret-change-me")
    warnings = get_production_warnings(settings)
    assert any("JWT_SECRET_KEY" in w for w in warnings)


def test_warns_on_wildcard_cors_in_production():
    settings = _settings(CORS_ALLOWED_ORIGINS="*")
    warnings = get_production_warnings(settings)
    assert any("CORS_ALLOWED_ORIGINS" in w for w in warnings)


def test_warns_on_empty_cors_in_production():
    settings = _settings(CORS_ALLOWED_ORIGINS="")
    warnings = get_production_warnings(settings)
    assert any("CORS_ALLOWED_ORIGINS" in w for w in warnings)


def test_warns_on_default_postgres_password_in_production():
    settings = _settings(POSTGRES_PASSWORD="sales_agent_password")
    warnings = get_production_warnings(settings)
    assert any("POSTGRES_PASSWORD" in w for w in warnings)


def test_no_postgres_password_warning_when_database_url_override_is_set():
    settings = _settings(
        POSTGRES_PASSWORD="sales_agent_password",
        DATABASE_URL="postgres://u:p@managed-host:5432/db",
    )
    warnings = get_production_warnings(settings)
    assert not any("POSTGRES_PASSWORD" in w for w in warnings)


def test_warns_on_debug_true_in_production():
    settings = _settings(DEBUG=True)
    warnings = get_production_warnings(settings)
    assert any("DEBUG" in w for w in warnings)


def test_warnings_never_include_the_actual_secret_value():
    settings = _settings(
        JWT_SECRET_KEY="dev-only-insecure-secret-change-me",
        POSTGRES_PASSWORD="sales_agent_password",
    )
    warnings = get_production_warnings(settings)
    joined = " ".join(warnings)
    assert "dev-only-insecure-secret-change-me" not in joined
    assert "sales_agent_password" not in joined
