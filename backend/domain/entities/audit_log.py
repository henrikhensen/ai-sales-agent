from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass
class AuditLog:
    """An immutable, system-wide audit trail entry.

    Deliberately narrow: never stores a secret, API key, token, full email
    body, full LLM prompt, or full reply body — only which action happened,
    to what kind of entity, with what result, and a short human-readable
    reason. ``ip_hash`` is a one-way hash of the caller's IP, never the raw
    address. No ``result`` value here ever represents that an email was
    sent — this system has no send capability.
    """

    action: str
    result: str
    actor_user_id: UUID | None = None
    actor_role: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    reason: str | None = None
    request_id: str | None = None
    ip_hash: str | None = None
    user_agent: str | None = None
    metadata: dict[str, Any] | None = None
    id: UUID | None = None
    created_at: datetime | None = None
