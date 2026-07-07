"""Admin-only system status and backup status reporting.

Never returns a secret, API key, or token — only which mode each
integration is running in, and metadata about the most recent backup file
(never a download link).
"""

from fastapi import APIRouter

from backend.api.dependencies.auth import RequireAdminUserDep
from backend.api.v1.dependencies import SystemStatusServiceDep
from backend.api.v1.schemas.system import BackupStatusResponse, SystemStatusResponse

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
