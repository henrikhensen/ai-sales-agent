"""Data Export: cross-entity search by email / domain / name.

Admin-only. Builds a JSON export package from an explicit allow-list of
fields per entity type — never the entity's full ``__dict__`` — so a
newly-added field can never accidentally leak into an export without a
deliberate decision to include it. Never includes a secret, API key,
token, or full LLM prompt. This is a read-only search: nothing is changed,
deleted, or sent anywhere.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import Request

from backend.application.audit.audit_log_service import AuditLogService
from backend.application.compliance.data_export_schemas import (
    DataExportRequest,
    DataExportResponse,
)
from backend.domain.repositories.audit_log_repository import AuditLogRepository
from backend.domain.repositories.company_repository import CompanyRepository
from backend.domain.repositories.contact_repository import ContactRepository
from backend.domain.repositories.do_not_contact_repository import (
    DoNotContactRepository,
)
from backend.domain.repositories.email_draft_repository import EmailDraftRepository
from backend.domain.repositories.outreach_dispatch_repository import (
    OutreachDispatchRepository,
)
from backend.domain.repositories.outreach_queue_item_repository import (
    OutreachQueueItemRepository,
)
from backend.domain.repositories.reply_repository import ReplyRepository
from backend.domain.repositories.workflow_run_repository import WorkflowRunRepository

logger = logging.getLogger("backend.compliance.data_export")

_SCAN_PAGE_SIZE = 200
_SCAN_SAFETY_CAP = 2000


def _matches_text(value: str | None, needle: str | None) -> bool:
    if not value or not needle:
        return False
    return needle.lower() in value.lower()


class DataExportService:
    def __init__(
        self,
        companies: CompanyRepository,
        contacts: ContactRepository,
        email_drafts: EmailDraftRepository,
        replies: ReplyRepository,
        workflow_runs: WorkflowRunRepository,
        outreach_queue_items: OutreachQueueItemRepository,
        outreach_dispatches: OutreachDispatchRepository,
        do_not_contact: DoNotContactRepository,
        audit_logs: AuditLogRepository,
        audit: AuditLogService,
    ) -> None:
        self._companies = companies
        self._contacts = contacts
        self._email_drafts = email_drafts
        self._replies = replies
        self._workflow_runs = workflow_runs
        self._outreach_queue_items = outreach_queue_items
        self._outreach_dispatches = outreach_dispatches
        self._do_not_contact = do_not_contact
        self._audit_logs = audit_logs
        self._audit = audit

    async def export(
        self,
        request: DataExportRequest,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> DataExportResponse:
        email = request.email.lower() if request.email else None
        domain = request.domain.lower() if request.domain else None
        name = request.name

        matched_company_ids: set[UUID] = set()
        companies: list[dict[str, Any]] = []
        if domain:
            found = await self._companies.find_by_domain(domain)
            if found is not None:
                matched_company_ids.add(found.id)
                companies.append(self._company_dict(found))
        if name:
            found = await self._companies.find_by_name(name)
            if found is not None and found.id not in matched_company_ids:
                matched_company_ids.add(found.id)
                companies.append(self._company_dict(found))

        contacts: list[dict[str, Any]] = []
        for company_id in matched_company_ids:
            for contact in await self._contacts.list_by_company(company_id, limit=500):
                if email and contact.email and contact.email.lower() != email:
                    continue
                contacts.append(self._contact_dict(contact))

        email_drafts: list[dict[str, Any]] = []
        for company_id in matched_company_ids:
            for draft in await self._email_drafts.list_by_company(company_id, limit=500):
                email_drafts.append(self._email_draft_dict(draft))
        matched_email_draft_ids = {d["id"] for d in email_drafts}

        workflow_runs: list[dict[str, Any]] = []
        if name:
            for run in await self._workflow_runs.list(limit=500, company_name=name):
                workflow_runs.append(self._workflow_run_dict(run))

        replies = await self._scan_replies(email, matched_email_draft_ids)
        outreach_queue_items = await self._scan_outreach_queue_items(matched_company_ids)
        dispatches = await self._scan_dispatches(matched_company_ids)
        do_not_contact_entries = await self._scan_do_not_contact(email, domain, name)

        audit_log_references = await self._collect_audit_references(matched_company_ids)

        response = DataExportResponse(
            query=request,
            generated_at=datetime.now(timezone.utc).isoformat(),
            leads=contacts,
            companies=companies,
            email_drafts=email_drafts,
            replies=replies,
            workflow_runs=workflow_runs,
            outreach_queue_items=outreach_queue_items,
            dispatches=dispatches,
            do_not_contact_entries=do_not_contact_entries,
            audit_log_references=audit_log_references,
            message=(
                "This export may contain personal data. Handle it only for "
                "an authorized, legitimate purpose (e.g. responding to a "
                "data subject request) and never share it more widely than "
                "necessary."
            ),
        )
        await self._audit.record(
            action="data_export_executed",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="data_export",
            metadata={
                "has_email": bool(email),
                "has_domain": bool(domain),
                "has_name": bool(name),
                "result_counts": {
                    "leads": len(contacts),
                    "companies": len(companies),
                    "email_drafts": len(email_drafts),
                    "replies": len(replies),
                    "workflow_runs": len(workflow_runs),
                    "outreach_queue_items": len(outreach_queue_items),
                    "dispatches": len(dispatches),
                    "do_not_contact_entries": len(do_not_contact_entries),
                },
            },
            request=http_request,
        )
        return response

    # -- scans (repositories without a direct search method) ------------------------

    async def _scan_replies(
        self, email: str | None, email_draft_ids: set[Any]
    ) -> list[dict[str, Any]]:
        if not email and not email_draft_ids:
            return []
        results: list[dict[str, Any]] = []
        offset = 0
        scanned = 0
        while scanned < _SCAN_SAFETY_CAP:
            page = await self._replies.list(limit=_SCAN_PAGE_SIZE, offset=offset)
            if not page:
                break
            for reply in page:
                scanned += 1
                if (email and reply.from_email and reply.from_email.lower() == email) or (
                    reply.email_draft_id in email_draft_ids
                ):
                    results.append(self._reply_dict(reply))
            offset += _SCAN_PAGE_SIZE
            if len(page) < _SCAN_PAGE_SIZE:
                break
        return results

    async def _scan_outreach_queue_items(
        self, company_ids: set[UUID]
    ) -> list[dict[str, Any]]:
        if not company_ids:
            return []
        results: list[dict[str, Any]] = []
        offset = 0
        scanned = 0
        while scanned < _SCAN_SAFETY_CAP:
            page = await self._outreach_queue_items.list(
                limit=_SCAN_PAGE_SIZE, offset=offset
            )
            if not page:
                break
            for item in page:
                scanned += 1
                if item.company_id in company_ids:
                    results.append(self._queue_item_dict(item))
            offset += _SCAN_PAGE_SIZE
            if len(page) < _SCAN_PAGE_SIZE:
                break
        return results

    async def _scan_dispatches(self, company_ids: set[UUID]) -> list[dict[str, Any]]:
        if not company_ids:
            return []
        results: list[dict[str, Any]] = []
        offset = 0
        scanned = 0
        while scanned < _SCAN_SAFETY_CAP:
            page = await self._outreach_dispatches.list(
                limit=_SCAN_PAGE_SIZE, offset=offset
            )
            if not page:
                break
            for dispatch in page:
                scanned += 1
                if dispatch.company_id in company_ids:
                    results.append(self._dispatch_dict(dispatch))
            offset += _SCAN_PAGE_SIZE
            if len(page) < _SCAN_PAGE_SIZE:
                break
        return results

    async def _scan_do_not_contact(
        self, email: str | None, domain: str | None, name: str | None
    ) -> list[dict[str, Any]]:
        if not (email or domain or name):
            return []
        results: list[dict[str, Any]] = []
        offset = 0
        scanned = 0
        while scanned < _SCAN_SAFETY_CAP:
            page = await self._do_not_contact.list(limit=_SCAN_PAGE_SIZE, offset=offset)
            if not page:
                break
            for entry in page:
                scanned += 1
                if (
                    (email and entry.email and entry.email.lower() == email)
                    or (domain and entry.domain and entry.domain.lower() == domain)
                    or (name and _matches_text(entry.company_name, name))
                ):
                    results.append(self._dnc_dict(entry))
            offset += _SCAN_PAGE_SIZE
            if len(page) < _SCAN_PAGE_SIZE:
                break
        return results

    async def _collect_audit_references(
        self, company_ids: set[UUID]
    ) -> list[dict[str, Any]]:
        references: list[dict[str, Any]] = []
        for company_id in list(company_ids)[:20]:
            entries = await self._audit_logs.list_filtered(
                entity_id=str(company_id), limit=20
            )
            for entry in entries:
                references.append(
                    {
                        "action": entry.action,
                        "result": entry.result,
                        "entity_type": entry.entity_type,
                        "entity_id": entry.entity_id,
                        "created_at": entry.created_at.isoformat()
                        if entry.created_at
                        else None,
                    }
                )
        return references

    # -- field allow-lists per entity type -------------------------------------------

    @staticmethod
    def _company_dict(company: Any) -> dict[str, Any]:
        return {
            "id": company.id,
            "name": company.name,
            "domain": company.domain,
            "industry": company.industry,
            "created_at": company.created_at.isoformat() if company.created_at else None,
        }

    @staticmethod
    def _contact_dict(contact: Any) -> dict[str, Any]:
        return {
            "id": contact.id,
            "company_id": contact.company_id,
            "first_name": contact.first_name,
            "last_name": contact.last_name,
            "email": contact.email,
            "phone": contact.phone,
            "created_at": contact.created_at.isoformat() if contact.created_at else None,
        }

    @staticmethod
    def _email_draft_dict(draft: Any) -> dict[str, Any]:
        return {
            "id": draft.id,
            "company_id": draft.company_id,
            "subject_lines": draft.subject_lines,
            "status": draft.status,
            "review_status": draft.review_status.value
            if hasattr(draft.review_status, "value")
            else draft.review_status,
            "created_at": draft.created_at.isoformat() if draft.created_at else None,
        }

    @staticmethod
    def _reply_dict(reply: Any) -> dict[str, Any]:
        return {
            "id": reply.id,
            "from_email": reply.from_email,
            "from_name": reply.from_name,
            "subject": reply.subject,
            "body_preview": reply.body_preview,
            "detected_intent": reply.detected_intent.value
            if hasattr(reply.detected_intent, "value")
            else reply.detected_intent,
            "received_at": reply.received_at.isoformat() if reply.received_at else None,
        }

    @staticmethod
    def _workflow_run_dict(run: Any) -> dict[str, Any]:
        return {
            "id": run.id,
            "company_name": run.company_name,
            "status": run.status,
            "review_status": run.review_status.value
            if hasattr(run.review_status, "value")
            else run.review_status,
            "created_at": run.created_at.isoformat() if run.created_at else None,
        }

    @staticmethod
    def _queue_item_dict(item: Any) -> dict[str, Any]:
        return {
            "id": item.id,
            "campaign_id": item.campaign_id,
            "queue_status": item.queue_status,
            "compliance_status": item.compliance_status,
            "do_not_contact_status": item.do_not_contact_status,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }

    @staticmethod
    def _dispatch_dict(dispatch: Any) -> dict[str, Any]:
        return {
            "id": dispatch.id,
            "dispatch_status": dispatch.dispatch_status,
            "dispatch_mode": dispatch.dispatch_mode,
            "recipient_email": dispatch.recipient_email,
            "created_at": dispatch.created_at.isoformat() if dispatch.created_at else None,
        }

    @staticmethod
    def _dnc_dict(entry: Any) -> dict[str, Any]:
        return {
            "id": entry.id,
            "email": entry.email,
            "domain": entry.domain,
            "company_name": entry.company_name,
            "reason": entry.reason,
            "is_active": entry.is_active,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
        }
