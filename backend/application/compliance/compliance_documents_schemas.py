"""Schemas for Compliance Documents.

Every document returned here is a template/informational notice, never
legal advice and never a certification. See ``ComplianceDocumentsService``
for the actual text and ``COMPLIANCE.md`` for the full compliance pack.
"""

from __future__ import annotations

from pydantic import BaseModel


class ComplianceDocument(BaseModel):
    key: str
    title: str
    body: str


class ComplianceDocumentsResponse(BaseModel):
    documents: list[ComplianceDocument]
    disclaimer: str
