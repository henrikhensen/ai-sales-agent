from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class DoNotContactEntry:
    """An opt-out / do-not-contact record blocking outreach preparation.

    At least one of ``email``, ``domain``, or ``company_name`` must be set
    (enforced by the application service, not here). ``email`` and
    ``domain`` are always stored lowercase. ``company_name`` keeps the
    caller's original, human-readable casing; ``company_name_normalized``
    holds the lowercase/whitespace-collapsed form used for matching.
    Deactivating an entry (``is_active=False``) means it no longer blocks
    anything — it is kept only for audit history.
    """

    reason: str
    email: str | None = None
    domain: str | None = None
    company_name: str | None = None
    company_name_normalized: str | None = None
    source: str = "manual"
    is_active: bool = True
    created_by_user_id: UUID | None = None
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
