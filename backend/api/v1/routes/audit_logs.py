"""System-wide audit log: read-only, admin-only.

Every entry here already had its sensitive fields stripped/truncated at
write time (see backend/application/audit/audit_log_service.py) — never a
secret, API key, token, full email body, full LLM prompt, or full reply
body. Sales and reviewer accounts do not get access to the global audit
trail; they already see the narrower, domain-specific audit trails (Review
Events on workflow runs/email drafts, Reply Inbox, do-not-contact entries)
through their own existing endpoints.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from backend.api.dependencies.auth import RequireAdminUserDep
from backend.api.v1.dependencies import AuditLogServiceDep
from backend.application.audit.schemas import AuditLogListResponse, AuditLogResponse
from backend.domain.exceptions import AuditLogNotFoundError

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    service: AuditLogServiceDep,
    _current_user: RequireAdminUserDep,
    actor_user_id: UUID | None = Query(default=None),
    action: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    result: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> AuditLogListResponse:
    """List audit log entries, newest first, with optional filters.

    Admin-only. Never returns a secret, API key, or token.
    """
    return await service.list_filtered(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        result=result,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


@router.get("/{audit_log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    audit_log_id: UUID,
    service: AuditLogServiceDep,
    _current_user: RequireAdminUserDep,
) -> AuditLogResponse:
    """Return a single audit log entry. Admin-only."""
    try:
        return await service.get(audit_log_id)
    except AuditLogNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
