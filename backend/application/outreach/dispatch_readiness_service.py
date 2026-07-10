"""Dispatch Readiness Service: pure gate-checking for Controlled Outreach
Dispatch — never calls a provider's draft/send action itself, only ever
inspects state and reports whether it is safe to proceed.

Do-not-contact, Human Review approval, provider configuration, and the
business-level volume caps are all re-verified fresh on every call —
nothing here trusts a cached status. A provider's real create/send action
is only ever invoked by :class:`~backend.application.outreach.outreach_dispatch_service.OutreachDispatchService`
after this service reports ``is_ready=True`` (and, for execution, after
compliance acknowledgement and final confirmation are also present).
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from uuid import UUID

from backend.application.compliance.do_not_contact_service import DoNotContactService
from backend.application.outreach.dispatch_schemas import (
    DispatchReadinessCheckResponse,
    DispatchReadinessChecks,
)
from backend.domain.entities.outreach_dispatch import OutreachDispatch
from backend.domain.entities.outreach_queue_item import OutreachQueueItem
from backend.domain.enums import EmailDraftReviewStatus
from backend.domain.repositories.company_repository import CompanyRepository
from backend.domain.repositories.contact_repository import ContactRepository
from backend.domain.repositories.email_draft_repository import EmailDraftRepository
from backend.domain.repositories.lead_candidate_repository import (
    LeadCandidateRepository,
)
from backend.domain.repositories.outreach_dispatch_repository import (
    OutreachDispatchRepository,
)
from backend.domain.repositories.quality_score_repository import (
    QualityScoreRepository,
)
from backend.domain.repositories.user_feedback_repository import (
    UserFeedbackRepository,
)
from backend.domain.repositories.workflow_run_repository import WorkflowRunRepository
from backend.infrastructure.dispatch.base import DispatchProvider
from backend.shared.config import Settings

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_ZERO_UUID = UUID(int=0)

_INELIGIBLE_QUEUE_STATUSES = {
    "blocked",
    "rejected",
    "cancelled",
    "archived",
    "failed",
    "replied",
}


def _looks_like_email(value: str | None) -> bool:
    return bool(value) and bool(_EMAIL_RE.match(value))


class DispatchReadinessService:
    def __init__(
        self,
        email_drafts: EmailDraftRepository,
        lead_candidates: LeadCandidateRepository,
        companies: CompanyRepository,
        compliance: DoNotContactService,
        dispatches: OutreachDispatchRepository,
        settings: Settings,
        workflow_runs: WorkflowRunRepository | None = None,
        contacts: ContactRepository | None = None,
        user_feedback: UserFeedbackRepository | None = None,
        quality_scores: QualityScoreRepository | None = None,
    ) -> None:
        self._email_drafts = email_drafts
        self._lead_candidates = lead_candidates
        self._companies = companies
        self._compliance = compliance
        self._dispatches = dispatches
        self._settings = settings
        self._workflow_runs = workflow_runs
        self._contacts = contacts
        self._user_feedback = user_feedback
        self._quality_scores = quality_scores

    async def resolve_recipient_context(
        self, queue_item: OutreachQueueItem
    ) -> tuple[str | None, str | None, str | None]:
        """Return ``(email, domain, company_name)`` resolved from whatever
        context this queue item has — never guesses or fabricates a
        contact; only ever reuses data already on file."""
        email: str | None = None
        domain: str | None = None
        company_name: str | None = None
        if queue_item.company_id is not None:
            company = await self._companies.get(queue_item.company_id)
            if company is not None:
                domain = company.domain
                company_name = company.name
        if queue_item.lead_candidate_id is not None:
            candidate = await self._lead_candidates.get_by_id(queue_item.lead_candidate_id)
            if candidate is not None:
                email = candidate.public_contact_email
                company_name = company_name or candidate.company_name
                domain = domain or candidate.company_domain
        if (
            email is None
            and self._workflow_runs is not None
            and self._contacts is not None
            and queue_item.workflow_run_id is not None
        ):
            run = await self._workflow_runs.get_by_id(queue_item.workflow_run_id)
            if run is not None and run.contact_id is not None:
                contact = await self._contacts.get(run.contact_id)
                if contact is not None:
                    email = contact.email
        return email, domain, company_name

    async def check(
        self,
        queue_item: OutreachQueueItem,
        *,
        dispatch_mode: str,
        provider: DispatchProvider,
        existing_dispatch: OutreachDispatch | None,
        actor_user_id: UUID | None,
    ) -> DispatchReadinessCheckResponse:
        blockers: list[str] = []
        warnings: list[str] = []

        queue_item_allowed = queue_item.queue_status not in _INELIGIBLE_QUEUE_STATUSES
        if not queue_item_allowed:
            blockers.append(
                f"Queue item status '{queue_item.queue_status}' is not eligible for dispatch."
            )

        email_draft = None
        if queue_item.email_draft_id is not None:
            email_draft = await self._email_drafts.get(queue_item.email_draft_id)
        email_draft_exists = email_draft is not None
        if not email_draft_exists:
            blockers.append(
                "No email draft exists yet for this queue item — prepare the "
                "Sales Workflow first."
            )

        human_review_approved = True
        if self._settings.outreach_dispatch_require_approved_review:
            human_review_approved = (
                email_draft_exists
                and email_draft.review_status == EmailDraftReviewStatus.APPROVED
            )
            if email_draft_exists and not human_review_approved:
                blockers.append(
                    "Email draft review status is "
                    f"'{email_draft.review_status.value}', not approved."
                )

        recipient_email, domain, company_name = await self.resolve_recipient_context(
            queue_item
        )
        recipient_valid = _looks_like_email(recipient_email)
        if not recipient_valid:
            blockers.append("No valid recipient email is available for this queue item.")

        do_not_contact_passed = True
        if self._settings.outreach_dispatch_require_do_not_contact_check:
            dnc = await self._compliance.check(
                email=recipient_email, domain=domain, company_name=company_name
            )
            do_not_contact_passed = not dnc.is_blocked
            if dnc.is_blocked:
                blockers.append(
                    f"Blocked by an active do-not-contact entry ({dnc.warning_message})."
                )

        provider_status = await provider.get_provider_status(actor_user_id or _ZERO_UUID)
        provider_config_ok = provider_status.configured
        if not provider_config_ok:
            blockers.append(provider_status.message)
        if dispatch_mode == "manual_send":
            if not self._settings.outreach_dispatch_enable_real_send:
                blockers.append(
                    "Manual send is not enabled (OUTREACH_DISPATCH_ENABLE_REAL_SEND=false)."
                )
            elif not provider_status.supports_manual_send:
                warnings.append(
                    f"Provider '{provider.name}' does not implement real manual "
                    "send — the confirmed action will report a safe-mode result."
                )

        now = datetime.now(timezone.utc)
        count_hour = await self._dispatches.count_since(
            actor_user_id, now - timedelta(hours=1)
        )
        count_day = await self._dispatches.count_since(
            actor_user_id, now - timedelta(days=1)
        )
        rate_limit_ok = (
            count_hour < self._settings.outreach_dispatch_max_per_hour
            and count_day < self._settings.outreach_dispatch_max_per_day
        )
        if not rate_limit_ok:
            blockers.append(
                "The hourly/daily Controlled Outreach Dispatch volume limit "
                "has been reached."
            )

        compliance_ack_present = (
            existing_dispatch is not None
            and existing_dispatch.compliance_acknowledged_at is not None
        )
        if (
            existing_dispatch is not None
            and self._settings.outreach_dispatch_require_compliance_ack
            and not compliance_ack_present
        ):
            blockers.append(
                "Compliance acknowledgement is required before this action."
            )

        quality_ok = await self._check_quality(queue_item, email_draft, blockers, warnings)

        checks = DispatchReadinessChecks(
            do_not_contact_passed=do_not_contact_passed,
            human_review_approved=human_review_approved,
            email_draft_exists=email_draft_exists,
            queue_item_allowed=queue_item_allowed,
            rate_limit_ok=rate_limit_ok,
            provider_config_ok=provider_config_ok,
            recipient_valid=recipient_valid,
            compliance_ack_present=compliance_ack_present,
            quality_ok=quality_ok,
        )

        return DispatchReadinessCheckResponse(
            is_ready=len(blockers) == 0,
            blockers=blockers,
            warnings=warnings,
            checks=checks,
            recommended_mode=dispatch_mode,
            requires_final_confirmation=self._settings.outreach_dispatch_require_final_confirmation,
            requires_compliance_ack=self._settings.outreach_dispatch_require_compliance_ack,
            provider_status=provider_status.message,
        )

    async def _check_quality(
        self,
        queue_item: OutreachQueueItem,
        email_draft: object | None,
        blockers: list[str],
        warnings: list[str],
    ) -> bool:
        """Quality Blocker check (see backend/application/quality/). Only
        open, explicitly-marked ``is_blocking`` feedback or a
        compliance-blocked quality score are hard blockers — a merely low
        score is surfaced as a warning only, since scores are decision
        support, not a pass/fail gate on their own. Returns True (no
        blocker) if the quality repositories were not wired in, keeping
        this fully backward compatible."""
        if self._user_feedback is None and self._quality_scores is None:
            return True

        quality_ok = True
        if self._user_feedback is not None:
            blocking_on_item = await self._user_feedback.count_blocking_for_entity(
                "outreach_queue_item", queue_item.id
            )
            blocking_on_draft = 0
            if queue_item.email_draft_id is not None:
                blocking_on_draft = await self._user_feedback.count_blocking_for_entity(
                    "email_draft", queue_item.email_draft_id
                )
            if blocking_on_item or blocking_on_draft:
                blockers.append(
                    "Open blocking feedback exists for this queue item or its "
                    "email draft — resolve it before dispatching."
                )
                quality_ok = False

        if self._quality_scores is not None and queue_item.email_draft_id is not None:
            latest = await self._quality_scores.find_latest_for_entity(
                "email_draft", queue_item.email_draft_id
            )
            if latest is not None:
                if latest.score_level == "blocked":
                    blockers.append(
                        "The email draft's latest quality score is 'blocked' "
                        "(a compliance flag was raised)."
                    )
                    quality_ok = False
                elif latest.score_total < self._settings.quality_min_draft_score:
                    warnings.append(
                        f"Email draft quality score ({latest.score_total}) is below "
                        f"the configured minimum ({self._settings.quality_min_draft_score})."
                    )
        return quality_ok
