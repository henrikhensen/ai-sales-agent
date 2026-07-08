"""System-wide audit logging.

Deliberately narrow: records what happened, to what kind of entity, with
what result, and a short human-readable reason — never a secret, API key,
token, full email body, full LLM prompt, or full reply body. Gated by
``AUDIT_LOGS_ENABLED``; when disabled, both :meth:`AuditLogService.record`
and :meth:`AuditLogService.record_independent` are no-ops. Recording an
event never raises back to the caller — a logging failure must never break
the action it's observing.

Use :meth:`AuditLogService.record` for ordinary events, which persist
atomically with the rest of the request. Use
:meth:`AuditLogService.record_independent` for security-relevant events
that must survive even when the request that describes them is itself
rejected and its own transaction rolled back — e.g. an unsafe admin
control change or a blocked dispatch confirmation.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import Request

from backend.application.audit.schemas import AuditLogListResponse, AuditLogResponse
from backend.domain.entities.audit_log import AuditLog
from backend.domain.exceptions import AuditLogNotFoundError
from backend.domain.repositories.audit_log_repository import AuditLogRepository
from backend.shared.config import Settings

logger = logging.getLogger("backend.audit")

# Metadata keys containing any of these words are dropped entirely rather
# than risk leaking a secret or large content blob into the audit trail.
_SENSITIVE_METADATA_KEYWORDS = (
    "api_key",
    "apikey",
    "password",
    "secret",
    "token",
    "authorization",
    "body",
    "prompt",
    "content",
)
_MAX_METADATA_VALUE_LENGTH = 300
_MAX_REASON_LENGTH = 500
_MAX_USER_AGENT_LENGTH = 300


def hash_ip(ip_address: str) -> str:
    """One-way hash of a client IP — never store the raw address."""
    return hashlib.sha256(ip_address.encode("utf-8")).hexdigest()[:32]


def _sanitize_metadata(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    if not metadata:
        return None
    cleaned: dict[str, Any] = {}
    for key, value in metadata.items():
        if any(word in key.lower() for word in _SENSITIVE_METADATA_KEYWORDS):
            continue
        if isinstance(value, str) and len(value) > _MAX_METADATA_VALUE_LENGTH:
            value = value[:_MAX_METADATA_VALUE_LENGTH] + "…(truncated)"
        cleaned[key] = value
    return cleaned or None


def _build_entry(
    *,
    action: str,
    result: str,
    actor_user_id: UUID | None,
    actor_role: str | None,
    entity_type: str | None,
    entity_id: str | UUID | None,
    reason: str | None,
    request: Request | None,
    metadata: dict[str, Any] | None,
) -> AuditLog:
    request_id: str | None = None
    ip_hash: str | None = None
    user_agent: str | None = None
    if request is not None:
        request_id = getattr(request.state, "request_id", None) or request.headers.get(
            "x-request-id"
        )
        client_host = request.client.host if request.client else None
        ip_hash = hash_ip(client_host) if client_host else None
        raw_user_agent = request.headers.get("user-agent")
        user_agent = raw_user_agent[:_MAX_USER_AGENT_LENGTH] if raw_user_agent else None

    return AuditLog(
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        result=result,
        reason=reason[:_MAX_REASON_LENGTH] if reason else None,
        request_id=request_id,
        ip_hash=ip_hash,
        user_agent=user_agent,
        metadata=_sanitize_metadata(metadata),
    )


class AuditLogService:
    def __init__(self, audit_logs: AuditLogRepository, settings: Settings) -> None:
        self._audit_logs = audit_logs
        self._settings = settings

    async def record(
        self,
        *,
        action: str,
        result: str,
        actor_user_id: UUID | None = None,
        actor_role: str | None = None,
        entity_type: str | None = None,
        entity_id: str | UUID | None = None,
        reason: str | None = None,
        request: Request | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record one audit event. Never raises — a failure here must
        never break the action it's observing.

        Rides on whatever ambient request transaction the caller is part
        of: if the caller's own request later raises and its session rolls
        back, this entry rolls back with it. Use :meth:`record_independent`
        instead for events that must survive that rollback."""
        if not self._settings.audit_logs_enabled:
            return

        entry = _build_entry(
            action=action,
            result=result,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type=entity_type,
            entity_id=entity_id,
            reason=reason,
            request=request,
            metadata=metadata,
        )
        try:
            await self._audit_logs.create(entry)
        except Exception:
            logger.warning(
                "failed to record audit log entry: action=%s", action, exc_info=True
            )

    async def record_independent(
        self,
        *,
        action: str,
        result: str,
        actor_user_id: UUID | None = None,
        actor_role: str | None = None,
        entity_type: str | None = None,
        entity_id: str | UUID | None = None,
        reason: str | None = None,
        request: Request | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record one audit event durably, independent of the caller's
        ambient request transaction. Never raises.

        Use this specifically for security-relevant events that must
        persist even when the action they describe is itself rejected —
        e.g. an unsafe admin control change or a blocked dispatch
        confirmation, where the caller records this and then immediately
        raises a domain exception that would otherwise roll back the entry
        along with everything else in the request (see
        ``backend.infrastructure.database.session.get_session``). Applies
        the same sanitization as :meth:`record` — no secrets, API keys,
        tokens, full bodies, or full prompts are ever stored.
        """
        if not self._settings.audit_logs_enabled:
            return

        entry = _build_entry(
            action=action,
            result=result,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type=entity_type,
            entity_id=entity_id,
            reason=reason,
            request=request,
            metadata=metadata,
        )
        try:
            await self._audit_logs.create_independent(entry)
        except Exception:
            logger.warning(
                "failed to record independent audit log entry: action=%s",
                action,
                exc_info=True,
            )

    async def get(self, audit_log_id: UUID) -> AuditLogResponse:
        entry = await self._audit_logs.get(audit_log_id)
        if entry is None:
            raise AuditLogNotFoundError(audit_log_id)
        return AuditLogResponse.model_validate(entry)

    async def list_filtered(
        self,
        *,
        actor_user_id: UUID | None = None,
        action: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        result: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> AuditLogListResponse:
        entries = await self._audit_logs.list_filtered(
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
        return AuditLogListResponse(
            items=[AuditLogResponse.model_validate(entry) for entry in entries],
            limit=limit,
            offset=offset,
        )
