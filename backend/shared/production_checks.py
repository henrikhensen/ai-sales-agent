"""Production-readiness config validation.

Centralizes the checks that used to live inline in ``backend/main.py`` so
they can also be surfaced through ``GET /api/v1/system/status`` and tested
directly as a pure function. Every warning message describes *which*
setting is unsafe, never the setting's actual (secret) value.
"""

from __future__ import annotations

from backend.shared.config import Settings

_INSECURE_JWT_SECRET_DEFAULT = "dev-only-insecure-secret-change-me"
_INSECURE_POSTGRES_PASSWORD_DEFAULT = "sales_agent_password"


def get_production_warnings(settings: Settings) -> list[str]:
    """Return clear warnings about unsafe settings for a production run.

    Returns an empty list when ``settings.app_env != "production"`` —
    these checks only apply once a deployment claims to be production.
    """
    if settings.app_env != "production":
        return []

    warnings: list[str] = []

    if settings.jwt_secret_key == _INSECURE_JWT_SECRET_DEFAULT:
        warnings.append(
            "JWT_SECRET_KEY is still the development default — set a real, "
            "random secret before going live."
        )

    origins = settings.cors_allowed_origins_list
    if not origins or "*" in origins:
        warnings.append(
            "CORS_ALLOWED_ORIGINS is '*' or empty — restrict it to the exact "
            "production frontend origin(s)."
        )

    if (
        not settings.database_url_override
        and settings.postgres_password == _INSECURE_POSTGRES_PASSWORD_DEFAULT
    ):
        warnings.append(
            "POSTGRES_PASSWORD is still the example default — set a real, "
            "unique password."
        )

    if settings.debug:
        warnings.append("DEBUG is true in production — set DEBUG=false.")

    return warnings


class ProductionConfigError(RuntimeError):
    """Raised at startup when APP_ENV=production but a critical secret is
    still an insecure default. Deliberately a hard failure, not a warning
    — a missing/default-valued production secret must stop the process
    from starting rather than silently serve traffic with it."""


def validate_production_config(settings: Settings) -> None:
    """Fail startup loudly when critical secrets are missing/insecure in
    production, instead of silently falling back to an unsafe default.

    A no-op outside ``APP_ENV=production`` (development/staging can keep
    using the convenient insecure defaults) — mirrors
    :func:`get_production_warnings`, but raises instead of returning
    strings, and only checks the subset of settings that are actually
    exploitable if left at their default (a shared/known JWT signing key
    or database password, or a wildcard/empty CORS origin list).
    """
    if settings.app_env != "production":
        return

    problems: list[str] = []

    if settings.jwt_secret_key == _INSECURE_JWT_SECRET_DEFAULT:
        problems.append(
            "JWT_SECRET_KEY is missing or still the development default. "
            "Set a real, random secret (e.g. `openssl rand -hex 32`)."
        )

    origins = settings.cors_allowed_origins_list
    if not origins or "*" in origins:
        problems.append(
            "CORS_ALLOWED_ORIGINS is missing, empty, or '*'. Set it to the "
            "exact production frontend origin(s)."
        )

    if (
        not settings.database_url_override
        and settings.postgres_password == _INSECURE_POSTGRES_PASSWORD_DEFAULT
    ):
        problems.append(
            "POSTGRES_PASSWORD is missing or still the example default. Set "
            "a real, unique password (or provide DATABASE_URL)."
        )

    if problems:
        joined = "\n  - ".join(problems)
        raise ProductionConfigError(
            "Refusing to start with APP_ENV=production while critical "
            "settings are missing or insecure:\n  - " + joined
        )
