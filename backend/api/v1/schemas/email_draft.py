from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EmailDraftRecordResponse(BaseModel):
    """Serialized persisted email draft returned by the API.

    This is a saved draft only: no field on this response ever represents
    that the email was sent — sending remains a separate, manual step.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    lead_id: UUID | None
    workflow_run_id: UUID | None
    subject_lines: list[str]
    email_body: str
    status: str
    created_at: datetime
    updated_at: datetime
