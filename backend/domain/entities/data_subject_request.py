from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class DataSubjectRequest:
    """A tracked request from or about a data subject (export, delete,
    anonymize, do-not-contact, or correction).

    Recording a request never performs the requested action by itself and
    never sends an email to the subject — every follow-up action (export,
    anonymize-preparation, do-not-contact entry creation) is a separate,
    explicit, admin-triggered step. ``subject_email`` is always stored
    lowercase for consistent matching; at least one of ``subject_email``,
    ``subject_domain``, or ``subject_name`` is required (enforced by the
    service layer, not this dataclass).
    """

    request_type: str
    subject_email: str | None = None
    subject_domain: str | None = None
    subject_name: str | None = None
    status: str = "open"
    requested_by_user_id: UUID | None = None
    handled_by_user_id: UUID | None = None
    notes: str | None = None
    result_summary: str | None = None
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    completed_at: datetime | None = None
