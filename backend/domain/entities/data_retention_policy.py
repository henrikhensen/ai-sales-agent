from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class DataRetentionPolicy:
    """An admin-declared retention rule for one kind of stored data.

    Purely declarative until a run is actually started against it — a
    policy existing does not, by itself, delete or change anything.
    ``entity_type`` and ``action`` are validated against a fixed set (see
    ``backend.application.compliance.data_retention_schemas``); not every
    action is supported for every entity type (e.g. ``archive`` only
    applies to replies, and several entity types only support ``anonymize``
    because their repositories have no delete capability by design — audit
    logs are append-only and are never deleted or anonymized by any run).
    """

    name: str
    entity_type: str
    retention_days: int
    action: str = "anonymize"
    is_active: bool = True
    dry_run_default: bool = True
    created_by_user_id: UUID | None = None
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
