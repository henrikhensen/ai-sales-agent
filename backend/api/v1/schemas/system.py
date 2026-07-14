from typing import Literal

from pydantic import BaseModel


class SystemStatusResponse(BaseModel):
    """Admin-only system status snapshot.

    Never includes a secret, API key, or token — only booleans/enums
    describing which mode each integration is running in.
    """

    app_name: str
    app_version: str
    app_env: str
    database_status: Literal["up", "down"]
    redis_status: Literal["up", "down"]
    llm_provider: str
    llm_real_calls_enabled: bool
    email_integration_provider: str
    email_real_drafts_enabled: bool
    reply_tracking_provider: str
    reply_real_reads_enabled: bool
    metrics_enabled: bool
    backups_enabled: bool
    request_logging_enabled: bool
    production_warnings: list[str]


class MetricsResponse(BaseModel):
    """Simple JSON metrics — no personal data, email/reply content, or
    secrets. Gated by ENABLE_METRICS; admin-only."""

    request_count: int
    request_error_count: int
    average_response_time_ms: float
    workflow_run_count: int
    email_draft_count: int
    reply_count: int
    do_not_contact_block_count: int
    external_draft_created_count: int
    llm_test_count: int


class BackupStatusResponse(BaseModel):
    """Admin-only backup status. Never exposes a download link — only
    whether backups are enabled and metadata about the most recent one."""

    backups_enabled: bool
    backup_dir: str
    retention_days: int
    latest_backup_time: str | None
    latest_backup_file_name: str | None


class CorsDebugResponse(BaseModel):
    """Public CORS diagnostics — deliberately minimal, exactly five fields,
    never a secret, API key, token, or environment dump. Intended to be
    opened directly in a browser (bypassing CORS entirely, since CORS only
    applies to cross-origin fetch/XHR, not top-level navigation) so an
    operator can see exactly what the backend resolved
    CORS_ALLOWED_ORIGINS/FRONTEND_PUBLIC_URL/BACKEND_PUBLIC_URL to, without
    guessing from the Railway Variables tab."""

    request_origin: str | None
    allowed_origins: list[str]
    cors_allowed: bool | None
    frontend_public_url: str
    backend_public_url: str
