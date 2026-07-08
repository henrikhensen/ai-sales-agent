from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class WorkspaceSettings:
    """A single workspace's declared setup preferences and safety-related
    toggles.

    Single-tenant in this phase — there is exactly one row, acting as a
    workspace-wide settings singleton rather than enforcing multi-tenancy.
    These fields never substitute for environment configuration: they
    record admin *intent* (surfaced throughout onboarding/admin controls),
    validated against the real ``*_ENABLE_REAL_*`` environment flags at
    write time, but the environment flags remain the sole runtime
    authority over whether a real provider call can ever happen.
    """

    workspace_name: str
    company_name: str | None = None
    company_website: str | None = None
    default_language: str = "de"
    default_tone: str = "professional"
    default_icp_profile_id: UUID | None = None
    default_offer_profile_id: UUID | None = None
    require_human_review: bool = True
    require_do_not_contact_check: bool = True
    allow_real_llm_calls: bool = False
    allow_real_email_drafts: bool = False
    allow_real_reply_reads: bool = False
    allow_real_dispatch: bool = False
    dispatch_mode: str = "draft_only"
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
