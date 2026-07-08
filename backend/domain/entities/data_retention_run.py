from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class DataRetentionRun:
    """One execution (dry-run or real) of a :class:`DataRetentionPolicy`.

    A dry run never changes any data — ``total_processed`` stays 0 and only
    ``total_scanned``/``total_eligible`` are meaningful. A real run requires
    an explicit, authenticated admin action; it is never triggered
    automatically or on a schedule by this system.
    """

    policy_id: UUID
    entity_type: str
    action: str
    dry_run: bool = True
    status: str = "running"
    started_by_user_id: UUID | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    total_scanned: int = 0
    total_eligible: int = 0
    total_processed: int = 0
    total_failed: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
