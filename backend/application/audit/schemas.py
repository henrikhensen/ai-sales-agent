from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    """A single audit log entry. Never includes a secret, API key, token,
    full email body, full LLM prompt, or full reply body."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_user_id: UUID | None
    actor_role: str | None
    action: str
    entity_type: str | None
    entity_id: str | None
    result: str
    reason: str | None
    request_id: str | None
    ip_hash: str | None
    user_agent: str | None
    metadata: dict[str, Any] | None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    limit: int
    offset: int
