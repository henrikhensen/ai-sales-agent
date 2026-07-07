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
