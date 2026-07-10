"""Tests for backend/shared/production_checks.py and the APP_ENV
validator in backend/shared/config.py.

Pure-function tests: no database, no Redis, no HTTP client needed.
"""

import pytest
from pydantic import ValidationError

from backend.shared.config import Settings
from backend.shared.production_checks import (
    ProductionConfigError,
    get_production_warnings,
    validate_production_config,
)


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


# -- APP_ENV strict validation -----------------------------------------------------


def test_app_env_accepts_the_three_valid_values():
    for value in ("development", "staging", "production"):
        assert Settings(APP_ENV=value).app_env == value


def test_app_env_is_case_insensitive():
    assert Settings(APP_ENV="PRODUCTION").app_env == "production"


def test_app_env_rejects_a_typo():
    with pytest.raises(ValidationError):
        Settings(APP_ENV="prod")


def test_app_env_rejects_an_empty_value():
    with pytest.raises(ValidationError):
        Settings(APP_ENV="")


# -- validate_production_config: hard-fail, not just a warning ----------------------


def test_validate_production_config_does_not_raise_in_development():
    settings = _settings(
        APP_ENV="development",
        JWT_SECRET_KEY="dev-only-insecure-secret-change-me",
        CORS_ALLOWED_ORIGINS="*",
        POSTGRES_PASSWORD="sales_agent_password",
    )
    validate_production_config(settings)  # must not raise


def test_validate_production_config_does_not_raise_for_a_fully_configured_production_settings():
    validate_production_config(_settings())  # must not raise


def test_validate_production_config_raises_on_default_jwt_secret():
    settings = _settings(JWT_SECRET_KEY="dev-only-insecure-secret-change-me")
    with pytest.raises(ProductionConfigError) as exc_info:
        validate_production_config(settings)
    assert "JWT_SECRET_KEY" in str(exc_info.value)


def test_validate_production_config_raises_on_wildcard_cors():
    settings = _settings(CORS_ALLOWED_ORIGINS="*")
    with pytest.raises(ProductionConfigError) as exc_info:
        validate_production_config(settings)
    assert "CORS_ALLOWED_ORIGINS" in str(exc_info.value)


def test_validate_production_config_raises_on_empty_cors():
    settings = _settings(CORS_ALLOWED_ORIGINS="")
    with pytest.raises(ProductionConfigError):
        validate_production_config(settings)


def test_validate_production_config_raises_on_default_postgres_password():
    settings = _settings(POSTGRES_PASSWORD="sales_agent_password")
    with pytest.raises(ProductionConfigError) as exc_info:
        validate_production_config(settings)
    assert "POSTGRES_PASSWORD" in str(exc_info.value)


def test_validate_production_config_does_not_raise_when_database_url_override_is_set():
    settings = _settings(
        POSTGRES_PASSWORD="sales_agent_password",
        DATABASE_URL="postgres://u:p@managed-host:5432/db",
    )
    validate_production_config(settings)  # must not raise


def test_validate_production_config_does_not_raise_for_debug_true_alone():
    """DEBUG=true is a warning (get_production_warnings), not a hard
    startup failure — it's a verbosity setting, not a missing secret."""
    settings = _settings(DEBUG=True)
    validate_production_config(settings)  # must not raise


def test_validate_production_config_reports_every_problem_at_once():
    settings = _settings(
        JWT_SECRET_KEY="dev-only-insecure-secret-change-me",
        CORS_ALLOWED_ORIGINS="*",
        POSTGRES_PASSWORD="sales_agent_password",
    )
    with pytest.raises(ProductionConfigError) as exc_info:
        validate_production_config(settings)
    message = str(exc_info.value)
    assert "JWT_SECRET_KEY" in message
    assert "CORS_ALLOWED_ORIGINS" in message
    assert "POSTGRES_PASSWORD" in message


def test_validate_production_config_error_never_includes_the_actual_secret_value():
    settings = _settings(
        JWT_SECRET_KEY="dev-only-insecure-secret-change-me",
        POSTGRES_PASSWORD="sales_agent_password",
    )
    with pytest.raises(ProductionConfigError) as exc_info:
        validate_production_config(settings)
    message = str(exc_info.value)
    assert "dev-only-insecure-secret-change-me" not in message
    assert "sales_agent_password" not in message
