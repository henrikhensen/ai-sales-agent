"""Admin-only system status and backup status reporting.

Never returns a secret, API key, or token — only which mode each
integration is running in (mock/safe vs. real), and whether the
DB/Redis dependencies are currently reachable.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from backend.api.v1.schemas.system import BackupStatusResponse, SystemStatusResponse
from backend.infrastructure.database.session import check_database_connection
from backend.infrastructure.redis.client import check_redis_connection
from backend.shared.config import Settings
from backend.shared.production_checks import get_production_warnings

# Recognized backup file extensions produced by scripts/backup_db.*
_BACKUP_FILE_SUFFIXES = (".sql", ".sql.gz", ".dump")


class SystemStatusService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def get_status(self) -> SystemStatusResponse:
        database_up = await self._safe_check(check_database_connection)
        redis_up = await self._safe_check(check_redis_connection)
        settings = self._settings
        return SystemStatusResponse(
            app_name=settings.app_name,
            app_version=settings.app_version,
            app_env=settings.app_env,
            database_status="up" if database_up else "down",
            redis_status="up" if redis_up else "down",
            llm_provider=settings.llm_provider,
            llm_real_calls_enabled=settings.llm_enable_real_calls,
            email_integration_provider=settings.email_integration_provider,
            email_real_drafts_enabled=settings.email_integration_enable_real_drafts,
            reply_tracking_provider=settings.reply_tracking_provider,
            reply_real_reads_enabled=settings.reply_tracking_enable_real_reads,
            metrics_enabled=settings.enable_metrics,
            backups_enabled=settings.enable_backups,
            request_logging_enabled=settings.enable_request_logging,
            production_warnings=get_production_warnings(settings),
        )

    def get_backup_status(self) -> BackupStatusResponse:
        settings = self._settings
        latest_time: str | None = None
        latest_name: str | None = None

        backup_dir = Path(settings.backup_dir)
        if backup_dir.is_dir():
            candidates = [
                entry
                for entry in backup_dir.iterdir()
                if entry.is_file() and entry.name.endswith(_BACKUP_FILE_SUFFIXES)
            ]
            if candidates:
                latest = max(candidates, key=lambda entry: entry.stat().st_mtime)
                latest_name = latest.name
                latest_time = datetime.fromtimestamp(
                    latest.stat().st_mtime, tz=UTC
                ).isoformat()

        return BackupStatusResponse(
            backups_enabled=settings.enable_backups,
            backup_dir=settings.backup_dir,
            retention_days=settings.backup_retention_days,
            latest_backup_time=latest_time,
            latest_backup_file_name=latest_name,
        )

    @staticmethod
    async def _safe_check(check) -> bool:
        try:
            await check()
            return True
        except Exception:
            return False
