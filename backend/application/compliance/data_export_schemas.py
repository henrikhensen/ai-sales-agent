"""Schemas for the Data Export (cross-entity search) feature.

Admin-only. Never includes a secret, API key, or token — see
``DataExportService`` for the field-level exclusions applied to every
entity type in the export package.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class DataExportRequest(BaseModel):
    email: str | None = Field(default=None, max_length=320)
    domain: str | None = Field(default=None, max_length=255)
    name: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _require_at_least_one(self) -> "DataExportRequest":
        if not (self.email or self.domain or self.name):
            raise ValueError(
                "At least one of email, domain, or name is required."
            )
        return self


class DataExportResponse(BaseModel):
    query: DataExportRequest
    generated_at: str
    leads: list[dict[str, Any]] = Field(default_factory=list)
    companies: list[dict[str, Any]] = Field(default_factory=list)
    email_drafts: list[dict[str, Any]] = Field(default_factory=list)
    replies: list[dict[str, Any]] = Field(default_factory=list)
    workflow_runs: list[dict[str, Any]] = Field(default_factory=list)
    outreach_queue_items: list[dict[str, Any]] = Field(default_factory=list)
    dispatches: list[dict[str, Any]] = Field(default_factory=list)
    do_not_contact_entries: list[dict[str, Any]] = Field(default_factory=list)
    audit_log_references: list[dict[str, Any]] = Field(default_factory=list)
    message: str
