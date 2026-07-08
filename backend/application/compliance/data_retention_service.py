"""Data Retention: admin-declared policies and their dry-run/real execution.

A policy is purely declarative until a run is started against it — creating
one never changes any data by itself. ``anonymize`` is the safe default
action; ``delete`` removes a record outright and is only offered for entity
types whose repository supports deletion; ``archive`` is only supported for
replies (the only entity type with existing archive support). Audit logs
are never deleted or anonymized by any run — they are append-only by
design (see ``AuditLogRepository``); a policy against them is dry-run/count
only, and a real run against one always reports 0 processed with a clear
warning. Do-not-contact entries that are still active are never touched by
any run, regardless of age, so an opt-out can never be silently removed —
only already-inactive entries older than the retention window are eligible.

Only an admin may start a real (non-dry-run) run, and only with an explicit
confirmation flag. A dry run never changes data and is available to the
same admin-only audience. Scanning is page-based and capped
(``_SCAN_SAFETY_CAP``) rather than an unbounded full-table scan — this
mirrors the existing pagination limits used throughout the rest of the
system and is documented as a known limitation in CUSTOMER_READINESS.md.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import Request

from backend.application.audit.audit_log_service import AuditLogService
from backend.application.compliance.data_retention_schemas import (
    CreateDataRetentionPolicyRequest,
    DataRetentionPolicyListResponse,
    DataRetentionPolicyResponse,
    DataRetentionRunListResponse,
    DataRetentionRunResponse,
    RunDataRetentionPolicyRequest,
    UpdateDataRetentionPolicyRequest,
)
from backend.domain.entities.data_retention_policy import DataRetentionPolicy
from backend.domain.entities.data_retention_run import DataRetentionRun
from backend.domain.exceptions import (
    DataRetentionPolicyNotFoundError,
    DataRetentionRunNotFoundError,
    InvalidRetentionPolicyError,
    RetentionRunBlockedError,
)
from backend.domain.repositories.audit_log_repository import AuditLogRepository
from backend.domain.repositories.company_repository import CompanyRepository
from backend.domain.repositories.contact_repository import ContactRepository
from backend.domain.repositories.data_retention_policy_repository import (
    DataRetentionPolicyRepository,
)
from backend.domain.repositories.data_retention_run_repository import (
    DataRetentionRunRepository,
)
from backend.domain.repositories.do_not_contact_repository import (
    DoNotContactRepository,
)
from backend.domain.repositories.email_draft_repository import EmailDraftRepository
from backend.domain.repositories.external_email_draft_repository import (
    ExternalEmailDraftRepository,
)
from backend.domain.repositories.lead_candidate_repository import (
    LeadCandidateRepository,
)
from backend.domain.repositories.outreach_dispatch_repository import (
    OutreachDispatchRepository,
)
from backend.domain.repositories.outreach_queue_item_repository import (
    OutreachQueueItemRepository,
)
from backend.domain.repositories.qualification_result_repository import (
    QualificationResultRepository,
)
from backend.domain.repositories.reply_repository import ReplyRepository
from backend.domain.repositories.workflow_run_repository import WorkflowRunRepository
from backend.shared.config import Settings

logger = logging.getLogger("backend.compliance.data_retention")

# Which actions each entity type's repository can actually carry out.
# "delete" only appears where the repository has a real delete() method;
# "archive" only for replies (the only entity type with archive support).
# audit_log allows "anonymize" only so a policy can exist/dry-run against
# it, but a real run always no-ops (see _process_audit_log).
_SUPPORTED_ACTIONS: dict[str, set[str]] = {
    "lead": {"delete", "anonymize"},
    "company": {"delete", "anonymize"},
    "email_draft": {"delete", "anonymize"},
    "reply": {"delete", "anonymize", "archive"},
    "workflow_run": {"anonymize"},
    "audit_log": {"anonymize"},
    "do_not_contact": {"delete", "anonymize"},
    "external_draft": {"delete", "anonymize"},
    "outreach": {"anonymize"},
    "qualification": {"anonymize"},
    "sourcing_candidate": {"anonymize"},
}

_SCAN_PAGE_SIZE = 200
_SCAN_SAFETY_CAP = 5000


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _entity_created_at(entity: Any) -> datetime | None:
    return getattr(entity, "created_at", None)


class DataRetentionService:
    def __init__(
        self,
        policies: DataRetentionPolicyRepository,
        runs: DataRetentionRunRepository,
        contacts: ContactRepository,
        companies: CompanyRepository,
        email_drafts: EmailDraftRepository,
        replies: ReplyRepository,
        workflow_runs: WorkflowRunRepository,
        do_not_contact: DoNotContactRepository,
        external_email_drafts: ExternalEmailDraftRepository,
        outreach_queue_items: OutreachQueueItemRepository,
        outreach_dispatches: OutreachDispatchRepository,
        qualification_results: QualificationResultRepository,
        lead_candidates: LeadCandidateRepository,
        audit_logs: AuditLogRepository,
        audit: AuditLogService,
        settings: Settings,
    ) -> None:
        self._policies = policies
        self._runs = runs
        self._contacts = contacts
        self._companies = companies
        self._email_drafts = email_drafts
        self._replies = replies
        self._workflow_runs = workflow_runs
        self._do_not_contact = do_not_contact
        self._external_email_drafts = external_email_drafts
        self._outreach_queue_items = outreach_queue_items
        self._outreach_dispatches = outreach_dispatches
        self._qualification_results = qualification_results
        self._lead_candidates = lead_candidates
        self._audit_logs = audit_logs
        self._audit = audit
        self._settings = settings

    # -- policies -----------------------------------------------------------------

    @staticmethod
    def _validate_action(entity_type: str, action: str) -> None:
        supported = _SUPPORTED_ACTIONS.get(entity_type, set())
        if action not in supported:
            raise InvalidRetentionPolicyError(
                f"action '{action}' is not supported for entity_type "
                f"'{entity_type}'. Supported actions: {sorted(supported)}."
            )

    async def list_policies(
        self, limit: int = 100, offset: int = 0, active_only: bool = False
    ) -> DataRetentionPolicyListResponse:
        items = await self._policies.list(
            limit=limit, offset=offset, active_only=active_only
        )
        return DataRetentionPolicyListResponse(
            items=[DataRetentionPolicyResponse.model_validate(p) for p in items],
            limit=limit,
            offset=offset,
        )

    async def _get_policy_or_404(self, policy_id: UUID) -> DataRetentionPolicy:
        policy = await self._policies.get_by_id(policy_id)
        if policy is None:
            raise DataRetentionPolicyNotFoundError(policy_id)
        return policy

    async def create_policy(
        self,
        request: CreateDataRetentionPolicyRequest,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> DataRetentionPolicyResponse:
        self._validate_action(request.entity_type, request.action)
        created = await self._policies.create(
            DataRetentionPolicy(
                name=request.name,
                entity_type=request.entity_type,
                retention_days=request.retention_days,
                action=request.action,
                dry_run_default=request.dry_run_default,
                created_by_user_id=actor_user_id,
            )
        )
        await self._audit.record(
            action="data_retention_policy_created",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="data_retention_policy",
            entity_id=created.id,
            metadata={"entity_type": request.entity_type, "action": request.action},
            request=http_request,
        )
        return DataRetentionPolicyResponse.model_validate(created)

    async def update_policy(
        self,
        policy_id: UUID,
        request: UpdateDataRetentionPolicyRequest,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> DataRetentionPolicyResponse:
        policy = await self._get_policy_or_404(policy_id)
        updates = request.model_dump(exclude_unset=True)
        new_action = updates.get("action", policy.action)
        self._validate_action(policy.entity_type, new_action)
        for field_name, value in updates.items():
            setattr(policy, field_name, value)
        updated = await self._policies.update(policy)
        assert updated is not None
        await self._audit.record(
            action="data_retention_policy_updated",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="data_retention_policy",
            entity_id=updated.id,
            metadata={"fields": list(updates.keys())},
            request=http_request,
        )
        return DataRetentionPolicyResponse.model_validate(updated)

    async def deactivate_policy(
        self,
        policy_id: UUID,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> DataRetentionPolicyResponse:
        policy = await self._get_policy_or_404(policy_id)
        policy.is_active = False
        updated = await self._policies.update(policy)
        assert updated is not None
        await self._audit.record(
            action="data_retention_policy_deactivated",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="data_retention_policy",
            entity_id=updated.id,
            request=http_request,
        )
        return DataRetentionPolicyResponse.model_validate(updated)

    # -- runs ---------------------------------------------------------------------

    async def list_runs(
        self, limit: int = 100, offset: int = 0, policy_id: UUID | None = None
    ) -> DataRetentionRunListResponse:
        items = await self._runs.list(limit=limit, offset=offset, policy_id=policy_id)
        return DataRetentionRunListResponse(
            items=[DataRetentionRunResponse.model_validate(r) for r in items],
            limit=limit,
            offset=offset,
        )

    async def get_run(self, run_id: UUID) -> DataRetentionRunResponse:
        run = await self._runs.get_by_id(run_id)
        if run is None:
            raise DataRetentionRunNotFoundError(run_id)
        return DataRetentionRunResponse.model_validate(run)

    async def dry_run(
        self,
        policy_id: UUID,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> DataRetentionRunResponse:
        """A dry run always executes, regardless of the policy's active
        state — it never changes any data, so there is nothing unsafe about
        running it on an inactive policy to preview what a real run would
        do."""
        policy = await self._get_policy_or_404(policy_id)
        return await self._execute(
            policy,
            dry_run=True,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            http_request=http_request,
        )

    async def run(
        self,
        policy_id: UUID,
        request: RunDataRetentionPolicyRequest,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> DataRetentionRunResponse:
        policy = await self._get_policy_or_404(policy_id)
        if not policy.is_active:
            raise RetentionRunBlockedError(
                "This policy is deactivated. Reactivate it before running it for real."
            )
        if not request.confirm:
            raise RetentionRunBlockedError(
                "Explicit confirmation (confirm=true) is required to run a "
                "real (non-dry-run) data retention action."
            )
        return await self._execute(
            policy,
            dry_run=False,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            http_request=http_request,
        )

    async def _execute(
        self,
        policy: DataRetentionPolicy,
        *,
        dry_run: bool,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None,
    ) -> DataRetentionRunResponse:
        cutoff = _now() - timedelta(days=policy.retention_days)
        run_entity = await self._runs.create(
            DataRetentionRun(
                policy_id=policy.id,
                entity_type=policy.entity_type,
                action=policy.action,
                dry_run=dry_run,
                status="running",
                started_by_user_id=actor_user_id,
                started_at=_now(),
            )
        )
        await self._audit.record(
            action="data_retention_dry_run_executed"
            if dry_run
            else "data_retention_run_started",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="data_retention_run",
            entity_id=run_entity.id,
            metadata={"entity_type": policy.entity_type, "action": policy.action},
            request=http_request,
        )

        handler = self._HANDLERS.get(policy.entity_type)
        try:
            if handler is None:
                scanned, eligible, processed, failed, warnings, errors = (
                    0,
                    0,
                    0,
                    0,
                    [f"No handler implemented for entity_type '{policy.entity_type}'."],
                    [],
                )
            else:
                scanned, eligible, processed, failed, warnings, errors = await handler(
                    self, cutoff, policy.action, dry_run
                )
            run_entity.total_scanned = scanned
            run_entity.total_eligible = eligible
            run_entity.total_processed = processed
            run_entity.total_failed = failed
            run_entity.warnings = warnings
            run_entity.errors = errors
            run_entity.status = "failed" if failed and not processed else "completed"
            run_entity.completed_at = _now()
        except Exception as exc:  # defensive: a run must always resolve to a stored record
            logger.warning("data retention run failed: %s", exc, exc_info=True)
            run_entity.status = "failed"
            run_entity.errors = [*run_entity.errors, "Run failed unexpectedly."]
            run_entity.completed_at = _now()

        updated = await self._runs.update(run_entity)
        assert updated is not None
        await self._audit.record(
            action="data_retention_run_failed"
            if updated.status == "failed"
            else "data_retention_run_completed",
            result="success" if updated.status == "completed" else "failed",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="data_retention_run",
            entity_id=updated.id,
            metadata={
                "total_scanned": updated.total_scanned,
                "total_eligible": updated.total_eligible,
                "total_processed": updated.total_processed,
                "total_failed": updated.total_failed,
                "dry_run": dry_run,
            },
            request=http_request,
        )
        return DataRetentionRunResponse.model_validate(updated)

    # -- per-entity-type handlers ---------------------------------------------------
    # Each returns (scanned, eligible, processed, failed, warnings, errors).

    async def _process_lead(
        self, cutoff: datetime, action: str, dry_run: bool
    ) -> tuple[int, int, int, int, list[str], list[str]]:
        """entity_type="lead" targets Contact records — the CRM Lead entity
        itself carries no personal data (just status/score bookkeeping);
        Contact is where the actual name/email/phone PII lives."""
        return await self._generic_page_scan(
            list_fn=self._contacts.list,
            cutoff=cutoff,
            eligible_fn=lambda e: True,
            process_fn=lambda e: self._anonymize_or_delete_contact(e, action),
            dry_run=dry_run,
        )

    async def _anonymize_or_delete_contact(self, contact: Any, action: str) -> None:
        if action == "delete":
            await self._contacts.delete(contact.id)
            return
        contact.first_name = "Anonymized"
        contact.last_name = "Contact"
        contact.email = None
        contact.phone = None
        await self._contacts.update(contact)

    async def _process_company(
        self, cutoff: datetime, action: str, dry_run: bool
    ) -> tuple[int, int, int, int, list[str], list[str]]:
        return await self._generic_page_scan(
            list_fn=self._companies.list,
            cutoff=cutoff,
            eligible_fn=lambda e: True,
            process_fn=lambda e: self._anonymize_or_delete_company(e, action),
            dry_run=dry_run,
        )

    async def _anonymize_or_delete_company(self, company: Any, action: str) -> None:
        if action == "delete":
            await self._companies.delete(company.id)
            return
        company.domain = None
        await self._companies.update(company)

    async def _process_email_draft(
        self, cutoff: datetime, action: str, dry_run: bool
    ) -> tuple[int, int, int, int, list[str], list[str]]:
        return await self._generic_page_scan(
            list_fn=self._email_drafts.list,
            cutoff=cutoff,
            eligible_fn=lambda e: True,
            process_fn=lambda e: self._anonymize_or_delete_email_draft(e, action),
            dry_run=dry_run,
        )

    async def _anonymize_or_delete_email_draft(self, draft: Any, action: str) -> None:
        if action == "delete":
            await self._email_drafts.delete(draft.id)
            return
        draft.email_body = "[anonymized]"
        draft.subject_lines = ["[anonymized]"]
        await self._email_drafts.update(draft)

    async def _process_reply(
        self, cutoff: datetime, action: str, dry_run: bool
    ) -> tuple[int, int, int, int, list[str], list[str]]:
        return await self._generic_page_scan(
            list_fn=self._replies.list,
            cutoff=cutoff,
            eligible_fn=lambda e: True,
            process_fn=lambda e: self._process_one_reply(e, action),
            dry_run=dry_run,
        )

    async def _process_one_reply(self, reply: Any, action: str) -> None:
        if action == "delete":
            await self._replies.delete(reply.id)
            return
        if action == "archive":
            await self._replies.archive(reply.id, True)
            return
        reply.from_email = "anonymized@example.invalid"
        reply.from_name = None
        reply.to_email = None
        reply.subject = "[anonymized]"
        reply.body_preview = None
        reply.body_text = None
        await self._replies.update(reply)

    async def _process_workflow_run(
        self, cutoff: datetime, action: str, dry_run: bool
    ) -> tuple[int, int, int, int, list[str], list[str]]:
        return await self._generic_page_scan(
            list_fn=self._workflow_runs.list,
            cutoff=cutoff,
            eligible_fn=lambda e: True,
            process_fn=lambda e: self._workflow_runs.anonymize(e.id),
            dry_run=dry_run,
        )

    async def _process_audit_log(
        self, cutoff: datetime, action: str, dry_run: bool
    ) -> tuple[int, int, int, int, list[str], list[str]]:
        entries = await self._audit_logs.list_filtered(
            date_to=cutoff, limit=_SCAN_SAFETY_CAP
        )
        return (
            len(entries),
            len(entries),
            0,
            0,
            [
                "Audit logs are append-only by design and are never deleted "
                "or anonymized by a retention run — this count is "
                "informational only."
            ],
            [],
        )

    async def _process_do_not_contact(
        self, cutoff: datetime, action: str, dry_run: bool
    ) -> tuple[int, int, int, int, list[str], list[str]]:
        # Active entries are never eligible, regardless of age — an opt-out
        # can never be silently removed by a retention run.
        return await self._generic_page_scan(
            list_fn=self._do_not_contact.list,
            cutoff=cutoff,
            eligible_fn=lambda e: not e.is_active,
            process_fn=lambda e: self._anonymize_or_delete_dnc(e, action),
            dry_run=dry_run,
        )

    async def _anonymize_or_delete_dnc(self, entry: Any, action: str) -> None:
        if action == "delete":
            await self._do_not_contact.delete(entry.id)
            return
        entry.email = None
        entry.domain = None
        entry.company_name = None
        entry.company_name_normalized = None
        await self._do_not_contact.update(entry)

    async def _process_external_draft(
        self, cutoff: datetime, action: str, dry_run: bool
    ) -> tuple[int, int, int, int, list[str], list[str]]:
        # ExternalEmailDraftRepository has no system-wide list() beyond the
        # base AbstractRepository.list(), which is safe to use here.
        return await self._generic_page_scan(
            list_fn=self._external_email_drafts.list,
            cutoff=cutoff,
            eligible_fn=lambda e: True,
            process_fn=lambda e: self._anonymize_or_delete_external_draft(e, action),
            dry_run=dry_run,
        )

    async def _anonymize_or_delete_external_draft(
        self, draft: Any, action: str
    ) -> None:
        if action == "delete":
            await self._external_email_drafts.delete(draft.id)
            return
        draft.provider_draft_id = None
        draft.provider_draft_url = None
        await self._external_email_drafts.update(draft)

    async def _process_outreach(
        self, cutoff: datetime, action: str, dry_run: bool
    ) -> tuple[int, int, int, int, list[str], list[str]]:
        queue_result = await self._generic_page_scan(
            list_fn=self._outreach_queue_items.list,
            cutoff=cutoff,
            eligible_fn=lambda e: True,
            process_fn=self._anonymize_queue_item,
            dry_run=dry_run,
        )
        dispatch_result = await self._generic_page_scan(
            list_fn=self._outreach_dispatches.list,
            cutoff=cutoff,
            eligible_fn=lambda e: True,
            process_fn=self._anonymize_dispatch,
            dry_run=dry_run,
        )
        combined = tuple(a + b for a, b in zip(queue_result[:4], dispatch_result[:4]))
        warnings = [*queue_result[4], *dispatch_result[4]]
        errors = [*queue_result[5], *dispatch_result[5]]
        return (*combined, warnings, errors)

    async def _anonymize_queue_item(self, item: Any) -> None:
        item.recommended_outreach_angle = None
        item.personalization_notes = None
        await self._outreach_queue_items.update(item)

    async def _anonymize_dispatch(self, dispatch: Any) -> None:
        dispatch.recipient_email = None
        dispatch.subject_snapshot = None
        dispatch.body_preview_snapshot = None
        await self._outreach_dispatches.update(dispatch)

    async def _process_qualification(
        self, cutoff: datetime, action: str, dry_run: bool
    ) -> tuple[int, int, int, int, list[str], list[str]]:
        return await self._generic_page_scan(
            list_fn=self._qualification_results.list,
            cutoff=cutoff,
            eligible_fn=lambda e: True,
            process_fn=self._anonymize_qualification_result,
            dry_run=dry_run,
        )

    async def _anonymize_qualification_result(self, result: Any) -> None:
        result.fit_summary = None
        result.recommended_outreach_angle = None
        result.disqualification_reason = None
        result.positive_signals = []
        result.negative_signals = []
        result.missing_data = []
        await self._qualification_results.update(result)

    async def _process_sourcing_candidate(
        self, cutoff: datetime, action: str, dry_run: bool
    ) -> tuple[int, int, int, int, list[str], list[str]]:
        return await self._generic_page_scan(
            list_fn=self._lead_candidates.list,
            cutoff=cutoff,
            eligible_fn=lambda e: True,
            process_fn=self._anonymize_lead_candidate,
            dry_run=dry_run,
        )

    async def _anonymize_lead_candidate(self, candidate: Any) -> None:
        candidate.public_contact_email = None
        candidate.notes = []
        await self._lead_candidates.update(candidate)

    # -- shared page-scan helper ----------------------------------------------------

    async def _generic_page_scan(
        self,
        *,
        list_fn: Any,
        cutoff: datetime,
        eligible_fn: Any,
        process_fn: Any,
        dry_run: bool,
    ) -> tuple[int, int, int, int, list[str], list[str]]:
        """Page through ``list_fn`` and process every eligible (older than
        ``cutoff`` and passing ``eligible_fn``) record with ``process_fn``.

        When ``dry_run`` is True, ``process_fn`` is never called — only
        counted — so a dry run is guaranteed to never mutate any data."""
        scanned = eligible = processed = failed = 0
        errors: list[str] = []
        offset = 0
        while scanned < _SCAN_SAFETY_CAP:
            page = await list_fn(limit=_SCAN_PAGE_SIZE, offset=offset)
            if not page:
                break
            for entity in page:
                scanned += 1
                created_at = _entity_created_at(entity)
                if created_at is None or created_at >= cutoff:
                    continue
                if not eligible_fn(entity):
                    continue
                eligible += 1
                if dry_run:
                    continue
                try:
                    await process_fn(entity)
                    processed += 1
                except Exception as exc:  # never let one bad record abort the run
                    failed += 1
                    errors.append(f"Failed to process one record: {type(exc).__name__}")
            offset += _SCAN_PAGE_SIZE
            if len(page) < _SCAN_PAGE_SIZE:
                break
        return scanned, eligible, processed, failed, [], errors

    _HANDLERS: dict[str, Any] = {}


def _register_handlers() -> None:
    DataRetentionService._HANDLERS = {
        "lead": DataRetentionService._process_lead,
        "company": DataRetentionService._process_company,
        "email_draft": DataRetentionService._process_email_draft,
        "reply": DataRetentionService._process_reply,
        "workflow_run": DataRetentionService._process_workflow_run,
        "audit_log": DataRetentionService._process_audit_log,
        "do_not_contact": DataRetentionService._process_do_not_contact,
        "external_draft": DataRetentionService._process_external_draft,
        "outreach": DataRetentionService._process_outreach,
        "qualification": DataRetentionService._process_qualification,
        "sourcing_candidate": DataRetentionService._process_sourcing_candidate,
    }


_register_handlers()
