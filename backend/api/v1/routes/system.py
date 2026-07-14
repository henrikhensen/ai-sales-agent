"""System status, backup status, and CORS diagnostics reporting.

``/status`` and ``/backups/status`` are admin-only; ``/cors-debug`` is
deliberately public. Never returns a secret, API key, or token — only
which mode each integration is running in, metadata about the most
recent backup file (never a download link), and public CORS
configuration.
"""

from fastapi import APIRouter, Request

from backend.api.dependencies.auth import RequireAdminUserDep
from backend.api.v1.dependencies import SystemStatusServiceDep
from backend.api.v1.schemas.system import (
    BackupStatusResponse,
    CorsDebugResponse,
    SystemStatusResponse,
)
from backend.shared.config import get_settings

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status(
    service: SystemStatusServiceDep,
    _current_user: RequireAdminUserDep,
) -> SystemStatusResponse:
    """Report app/environment/provider/safe-mode status. Admin-only.

    Never returns an API key, OAuth token, JWT secret, or database
    password — only booleans/enums describing which mode is active.
    """
    return await service.get_status()


@router.get("/backups/status", response_model=BackupStatusResponse)
async def get_backup_status(
    service: SystemStatusServiceDep,
    _current_user: RequireAdminUserDep,
) -> BackupStatusResponse:
    """Report backup configuration and the most recent backup file found in
    ``BACKUP_DIR``, if any. Admin-only. There is no download endpoint for
    backup files — only this status metadata.
    """
    return service.get_backup_status()


@router.get("/cors-debug", response_model=CorsDebugResponse)
async def get_cors_debug(request: Request) -> CorsDebugResponse:
    """Report resolved CORS configuration. Deliberately public (no auth,
    no database dependency) — the whole point is to be reachable and
    readable even when the frontend can't get past login because of the
    very CORS misconfiguration it's meant to diagnose. Never returns a
    secret; every field here is already visible in a browser's address
    bar or Network tab.
    """
    settings = get_settings()
    resolved = settings.cors_allowed_origins_list
    origin = request.headers.get("origin")
    return CorsDebugResponse(
        app_env=settings.app_env,
        cors_allowed_origins_raw=settings.cors_allowed_origins,
        cors_allowed_origins_resolved=resolved,
        frontend_public_url=settings.frontend_public_url,
        request_origin=origin,
        request_origin_allowed=(origin in resolved) if origin is not None else None,
    )
