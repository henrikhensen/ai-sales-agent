"""Schemas for Data Subject Requests.

Recording a request never performs the requested action automatically and
never sends an email to the subject — export, anonymize-preparation, and
do-not-contact-entry creation are each a separate, explicit, admin-
triggered follow-up step.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.application.compliance.data_export_schemas import DataExportResponse

DataRequestType = Literal["export", "delete", "anonymize", "do_not_contact", "correction"]

DataRequestStatus = Literal["open", "in_progress", "completed", "rejected", "cancelled"]


class DataSubjectRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    request_type: DataRequestType
    subject_email: str | None
    subject_domain: str | None
    subject_name: str | None
    status: DataRequestStatus
    requested_by_user_id: UUID | None
    handled_by_user_id: UUID | None
    notes: str | None
    result_summary: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class DataSubjectRequestListResponse(BaseModel):
    items: list[DataSubjectRequestResponse]
    limit: int
    offset: int


class DataSubjectRequestDetailResponse(BaseModel):
    request: DataSubjectRequestResponse
    export: DataExportResponse | None = None


class CreateDataSubjectRequestRequest(BaseModel):
    request_type: DataRequestType
    subject_email: str | None = Field(default=None, max_length=320)
    subject_domain: str | None = Field(default=None, max_length=255)
    subject_name: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _require_at_least_one_subject_field(self) -> "CreateDataSubjectRequestRequest":
        if not (self.subject_email or self.subject_domain or self.subject_name):
            raise ValueError(
                "At least one of subject_email, subject_domain, or "
                "subject_name is required."
            )
        return self


class UpdateDataSubjectRequestRequest(BaseModel):
    status: DataRequestStatus | None = None
    notes: str | None = Field(default=None, max_length=1000)
    result_summary: str | None = Field(default=None, max_length=1000)


class PrepareAnonymizeDataRequestResponse(BaseModel):
    request: DataSubjectRequestResponse
    message: str
    matched_lead_candidate_ids: list[UUID] = Field(default_factory=list)
    matched_contact_ids: list[UUID] = Field(default_factory=list)


class CompleteDataRequestRequest(BaseModel):
    result_summary: str | None = Field(default=None, max_length=1000)
