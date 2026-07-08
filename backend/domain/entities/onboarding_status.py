from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class OnboardingStatus:
    """One user's progress through the guided product setup checklist.

    Purely a progress tracker — never gates or grants access to any
    feature, never stores sensitive data, and never enables a real
    provider or automatic contact by itself.
    """

    user_id: UUID
    current_step: str = "welcome"
    completed_steps: list[str] = field(default_factory=list)
    skipped_steps: list[str] = field(default_factory=list)
    is_completed: bool = False
    completed_at: datetime | None = None
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
