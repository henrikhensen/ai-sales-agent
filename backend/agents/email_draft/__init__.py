"""Email Draft Agent package.

Turns company, lead and personalization context into a human-reviewable email
draft. Produces a draft only — no sending, no automated contact, no spam, and
no fabrication of facts. Human approval remains mandatory before any send.
"""

from backend.agents.email_draft.exceptions import (
    EmailDraftError,
    InvalidEmailDraftOutputError,
)
from backend.agents.email_draft.prompt import (
    EMAIL_DRAFT_SYSTEM_PROMPT,
    build_email_draft_prompt,
)
from backend.agents.email_draft.schemas import EmailDraftRequest, EmailDraftResponse
from backend.agents.email_draft.service import EmailDraftAgent, EmailDraftService

__all__ = [
    "EMAIL_DRAFT_SYSTEM_PROMPT",
    "EmailDraftAgent",
    "EmailDraftError",
    "EmailDraftRequest",
    "EmailDraftResponse",
    "EmailDraftService",
    "InvalidEmailDraftOutputError",
    "build_email_draft_prompt",
]
