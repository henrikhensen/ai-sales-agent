"""Reply Inbox / Reply Tracking service.

Reads replies from Gmail/Outlook/Mock (via
:class:`~backend.infrastructure.reply_tracking.base.ReplyTrackingProvider`),
classifies each new one with the existing Reply Analysis Agent, checks for
do-not-contact (unsubscribe/opt-out) signals, and stores the result. Never
sends an email, never sends a reply, and never creates an external draft —
this only ever reads and stores what already arrived in a connected
mailbox. Do-not-contact and Human Review both continue to apply exactly as
before: creating an opt-out entry here only ever blocks *future* drafts and
approvals through the existing mechanisms, never anything automatic.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from backend.agents.reply_analysis.schemas import ReplyAnalysisRequest
from backend.agents.reply_analysis.service import ReplyAnalysisService
from backend.application.compliance.do_not_contact_service import DoNotContactService
from backend.application.compliance.schemas import CreateDoNotContactRequest
from backend.application.integrations.reply_schemas import (
    ReplyIntegrationStatusResponse,
    ReplyListResponse,
    ReplyResponse,
    SyncRepliesResponse,
)
from backend.domain.entities.interaction import Interaction
from backend.domain.entities.reply import Reply
from backend.domain.enums import (
    EmailProviderType,
    InteractionType,
    PipelineStatus,
    ReplyCategory,
    ReplyIntent,
    ReplySentiment,
    ReplySyncStatus,
)
from backend.domain.exceptions import (
    EmailDraftNotFoundError,
    LeadNotFoundError,
    ReplyNotFoundError,
)
from backend.domain.repositories.company_repository import CompanyRepository
from backend.domain.repositories.contact_repository import ContactRepository
from backend.domain.repositories.email_draft_repository import EmailDraftRepository
from backend.domain.repositories.email_provider_connection_repository import (
    EmailProviderConnectionRepository,
)
from backend.domain.repositories.external_email_draft_repository import (
    ExternalEmailDraftRepository,
)
from backend.domain.repositories.interaction_repository import InteractionRepository
from backend.domain.repositories.lead_repository import LeadRepository
from backend.domain.repositories.reply_repository import ReplyRepository
from backend.domain.repositories.workflow_run_repository import WorkflowRunRepository
from backend.infrastructure.reply_tracking.base import (
    ReplySyncRequest,
    ReplyTrackingError,
    SyncedReplyMessage,
)
from backend.infrastructure.reply_tracking.factory import (
    create_reply_tracking_provider,
)
from backend.shared.config import Settings

logger = logging.getLogger("backend.reply_tracking")

# Deterministic — not left to the LLM's classification, so a false-negative
# from the model can never suppress an opt-out signal, and a test can rely
# on this behaving the same way every time.
_UNSUBSCRIBE_KEYWORDS = (
    "unsubscribe",
    "do not contact",
    "please stop",
    "remove me",
    "opt out",
    "opt-out",
)

_INTENT_TO_CATEGORY: dict[ReplyIntent, ReplyCategory] = {
    ReplyIntent.INTERESTED: ReplyCategory.INTERESTED,
    ReplyIntent.MEETING_REQUEST: ReplyCategory.MEETING_REQUEST,
    ReplyIntent.QUESTION: ReplyCategory.NEEDS_MORE_INFO,
    ReplyIntent.OBJECTION: ReplyCategory.NEEDS_MORE_INFO,
    ReplyIntent.NOT_INTERESTED: ReplyCategory.NOT_INTERESTED,
    ReplyIntent.OUT_OF_OFFICE: ReplyCategory.OUT_OF_OFFICE,
    ReplyIntent.UNCLEAR: ReplyCategory.UNKNOWN,
}

# Pure recommendation only — never applied automatically. A human changes
# the lead's actual pipeline_status via the existing
# PATCH /crm/leads/{lead_id}/pipeline-status endpoint.
_CATEGORY_TO_RECOMMENDED_PIPELINE_STATUS: dict[ReplyCategory, PipelineStatus] = {
    ReplyCategory.INTERESTED: PipelineStatus.IN_REVIEW,
    ReplyCategory.MEETING_REQUEST: PipelineStatus.IN_REVIEW,
    ReplyCategory.NEEDS_MORE_INFO: PipelineStatus.IN_REVIEW,
    ReplyCategory.NOT_INTERESTED: PipelineStatus.REJECTED,
    ReplyCategory.UNSUBSCRIBE: PipelineStatus.ARCHIVED,
    ReplyCategory.OUT_OF_OFFICE: PipelineStatus.RESEARCH_COMPLETED,
    ReplyCategory.UNKNOWN: PipelineStatus.RESEARCH_COMPLETED,
}


def _detect_unsubscribe_keyword(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in _UNSUBSCRIBE_KEYWORDS)


def _determine_reply_category(intent: ReplyIntent, reply_text: str) -> ReplyCategory:
    if _detect_unsubscribe_keyword(reply_text):
        return ReplyCategory.UNSUBSCRIBE
    return _INTENT_TO_CATEGORY.get(intent, ReplyCategory.UNKNOWN)


def _compliance_warning(category: str | None) -> str | None:
    if category == ReplyCategory.UNSUBSCRIBE.value:
        return (
            "Do-not-contact Signal erkannt: diese Antwort enthält eine "
            "Unsubscribe/Opt-out-Formulierung. Ein Do-not-contact-Eintrag "
            "wurde automatisch vorgeschlagen bzw. erstellt."
        )
    return None


def _recommended_pipeline_status(category: str | None) -> str | None:
    if category is None:
        return None
    try:
        return _CATEGORY_TO_RECOMMENDED_PIPELINE_STATUS[ReplyCategory(category)].value
    except ValueError:
        return None


class ReplyTrackingService:
    """Reads, classifies, and stores replies. Never sends anything."""

    def __init__(
        self,
        replies: ReplyRepository,
        connections: EmailProviderConnectionRepository,
        leads: LeadRepository,
        companies: CompanyRepository,
        contacts: ContactRepository,
        email_drafts: EmailDraftRepository,
        external_drafts: ExternalEmailDraftRepository,
        workflow_runs: WorkflowRunRepository,
        interactions: InteractionRepository,
        compliance: DoNotContactService,
        reply_analysis: ReplyAnalysisService,
        settings: Settings,
    ) -> None:
        self._replies = replies
        self._connections = connections
        self._leads = leads
        self._companies = companies
        self._contacts = contacts
        self._email_drafts = email_drafts
        self._external_drafts = external_drafts
        self._workflow_runs = workflow_runs
        self._interactions = interactions
        self._compliance = compliance
        self._reply_analysis = reply_analysis
        self._settings = settings

    def _build_provider(self):
        return create_reply_tracking_provider(self._connections, self._settings)

    def _sync_request(self, known_emails: list[str]) -> ReplySyncRequest:
        since = datetime.now(UTC) - timedelta(
            days=self._settings.reply_tracking_lookback_days
        )
        return ReplySyncRequest(
            known_emails=known_emails,
            since=since,
            max_messages=self._settings.reply_tracking_max_messages_per_sync,
        )

    # -- status -----------------------------------------------------------------

    async def get_status(self, user_id: UUID) -> ReplyIntegrationStatusResponse:
        active = self._settings.reply_tracking_provider.strip().lower()
        real_enabled = self._settings.reply_tracking_enable_real_reads

        if active in ("gmail", "outlook") and real_enabled:
            configured = self._is_configured(active)
            if not configured:
                return ReplyIntegrationStatusResponse(
                    active_provider=active,
                    real_reads_enabled=real_enabled,
                    safe_mode=True,
                    connected=False,
                    message=(
                        f"REPLY_TRACKING_PROVIDER={active} and "
                        "REPLY_TRACKING_ENABLE_REAL_READS=true, but the "
                        "required OAuth configuration is missing, so the "
                        "mock provider is used instead. No real mailbox is "
                        "read."
                    ),
                )

        provider = self._build_provider()
        status = await provider.get_provider_status(user_id)
        if active == "mock":
            message = "Mock provider is active. No real mailbox is ever read."
        elif not real_enabled:
            message = (
                f"REPLY_TRACKING_PROVIDER={active} but "
                "REPLY_TRACKING_ENABLE_REAL_READS is not true, so the mock "
                "provider is used instead. No real mailbox is read."
            )
        else:
            message = status.message
        return ReplyIntegrationStatusResponse(
            active_provider=provider.name,
            real_reads_enabled=real_enabled,
            safe_mode=provider.name == "mock",
            connected=status.connected,
            external_account_email=status.external_account_email,
            message=message,
        )

    def _is_configured(self, provider: str) -> bool:
        if provider == "gmail":
            return bool(
                self._settings.google_client_id
                and self._settings.google_client_secret
                and self._settings.email_token_encryption_key
            )
        if provider == "outlook":
            return bool(
                self._settings.microsoft_client_id
                and self._settings.microsoft_client_secret
                and self._settings.email_token_encryption_key
            )
        return True

    # -- reading / managing stored replies ---------------------------------------

    async def list_replies(
        self,
        *,
        category: ReplyCategory | None = None,
        sentiment: ReplySentiment | None = None,
        is_read: bool | None = None,
        is_archived: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> ReplyListResponse:
        replies = await self._replies.list_filtered(
            category=category,
            sentiment=sentiment,
            is_read=is_read,
            is_archived=is_archived,
            limit=limit,
            offset=offset,
        )
        return ReplyListResponse(
            items=[self._to_response(reply) for reply in replies],
            limit=limit,
            offset=offset,
        )

    async def list_lead_replies(
        self, lead_id: UUID, limit: int = 100, offset: int = 0
    ) -> ReplyListResponse:
        replies = await self._replies.list_by_lead(lead_id, limit=limit, offset=offset)
        return ReplyListResponse(
            items=[self._to_response(reply) for reply in replies],
            limit=limit,
            offset=offset,
        )

    async def get_reply(self, reply_id: UUID) -> ReplyResponse:
        reply = await self._replies.get(reply_id)
        if reply is None:
            raise ReplyNotFoundError(reply_id)
        return self._to_response(reply)

    async def mark_read(self, reply_id: UUID, is_read: bool = True) -> ReplyResponse:
        updated = await self._replies.mark_read(reply_id, is_read)
        if updated is None:
            raise ReplyNotFoundError(reply_id)
        return self._to_response(updated)

    async def archive_reply(
        self, reply_id: UUID, is_archived: bool = True
    ) -> ReplyResponse:
        updated = await self._replies.archive(reply_id, is_archived)
        if updated is None:
            raise ReplyNotFoundError(reply_id)
        return self._to_response(updated)

    @staticmethod
    def _to_response(reply: Reply) -> ReplyResponse:
        response = ReplyResponse.model_validate(reply)
        return response.model_copy(
            update={
                "recommended_pipeline_status": _recommended_pipeline_status(
                    response.reply_category
                ),
                "compliance_warning": _compliance_warning(response.reply_category),
            }
        )

    # -- syncing ------------------------------------------------------------------

    async def sync_replies_for_lead(
        self, user_id: UUID, lead_id: UUID
    ) -> SyncRepliesResponse:
        lead = await self._leads.get(lead_id)
        if lead is None:
            raise LeadNotFoundError(lead_id)

        contacts = await self._contacts.list_by_company(lead.company_id, limit=100)
        known_emails = sorted({c.email for c in contacts if c.email})

        try:
            provider = self._build_provider()
            messages = await provider.sync_replies_for_lead(
                user_id, self._sync_request(known_emails)
            )
        except ReplyTrackingError as exc:
            return self._sync_error_response(exc)

        return await self._store_synced_messages(
            provider.name,
            messages,
            lead_id=lead.id,
            company_id=lead.company_id,
        )

    async def sync_replies_for_draft(
        self, user_id: UUID, email_draft_id: UUID
    ) -> SyncRepliesResponse:
        draft = await self._email_drafts.get(email_draft_id)
        if draft is None:
            raise EmailDraftNotFoundError(email_draft_id)

        known_emails: list[str] = []
        if draft.workflow_run_id is not None:
            run = await self._workflow_runs.get_by_id(draft.workflow_run_id)
            if run is not None and run.contact_id is not None:
                contact = await self._contacts.get(run.contact_id)
                if contact and contact.email:
                    known_emails.append(contact.email)

        external_draft = await self._external_drafts.get_by_email_draft_id(
            email_draft_id
        )

        try:
            provider = self._build_provider()
            messages = await provider.sync_replies_for_draft(
                user_id, self._sync_request(known_emails)
            )
        except ReplyTrackingError as exc:
            return self._sync_error_response(exc)

        return await self._store_synced_messages(
            provider.name,
            messages,
            lead_id=draft.lead_id,
            company_id=draft.company_id,
            email_draft_id=draft.id,
            external_draft_id=external_draft.id if external_draft else None,
        )

    async def sync_recent_replies(self, user_id: UUID) -> SyncRepliesResponse:
        leads = await self._leads.list(limit=100)
        email_to_lead: dict[str, tuple[UUID, UUID]] = {}
        for lead in leads:
            contacts = await self._contacts.list_by_company(lead.company_id, limit=100)
            for contact in contacts:
                if contact.email:
                    email_to_lead[contact.email.strip().lower()] = (
                        lead.id,
                        lead.company_id,
                    )

        known_emails = sorted(email_to_lead.keys())

        try:
            provider = self._build_provider()
            messages = await provider.sync_recent_replies(
                user_id, self._sync_request(known_emails)
            )
        except ReplyTrackingError as exc:
            return self._sync_error_response(exc)

        new_count = 0
        duplicate_count = 0
        dnc_signals = 0
        saved: list[Reply] = []
        per_lead_new: dict[UUID, int] = {}

        for message in messages:
            lookup = email_to_lead.get(message.from_email.strip().lower())
            lead_id, company_id = lookup if lookup else (None, None)
            result = await self._store_one_message(
                provider.name,
                message,
                lead_id=lead_id,
                company_id=company_id,
                email_draft_id=None,
                external_draft_id=None,
            )
            if result is None:
                duplicate_count += 1
                continue
            reply, is_dnc_signal = result
            new_count += 1
            saved.append(reply)
            if is_dnc_signal:
                dnc_signals += 1
            if lead_id is not None:
                per_lead_new[lead_id] = per_lead_new.get(lead_id, 0) + 1

        for lead_id, count in per_lead_new.items():
            await self._record_sync_interaction(
                lead_id, provider.name, new_count=count, duplicate_count=0
            )

        return SyncRepliesResponse(
            status=(
                ReplySyncStatus.MOCK_SYNCED.value
                if provider.name == "mock"
                else ReplySyncStatus.SYNCED.value
            ),
            provider=provider.name,
            synced_count=len(messages),
            new_count=new_count,
            duplicate_count=duplicate_count,
            do_not_contact_signals=dnc_signals,
            message=f"Synced {len(messages)} message(s): {new_count} new, "
            f"{duplicate_count} duplicate(s).",
            replies=[self._to_response(reply) for reply in saved],
        )

    def _sync_error_response(self, exc: ReplyTrackingError) -> SyncRepliesResponse:
        logger.warning("reply sync failed: %s", type(exc).__name__)
        return SyncRepliesResponse(
            status=ReplySyncStatus.FAILED.value,
            provider=self._settings.reply_tracking_provider.strip().lower(),
            synced_count=0,
            new_count=0,
            duplicate_count=0,
            do_not_contact_signals=0,
            message=str(exc),
            error=str(exc),
        )

    async def _store_synced_messages(
        self,
        provider_name: str,
        messages: list[SyncedReplyMessage],
        *,
        lead_id: UUID | None,
        company_id: UUID | None,
        email_draft_id: UUID | None = None,
        external_draft_id: UUID | None = None,
    ) -> SyncRepliesResponse:
        new_count = 0
        duplicate_count = 0
        dnc_signals = 0
        saved: list[Reply] = []

        for message in messages:
            result = await self._store_one_message(
                provider_name,
                message,
                lead_id=lead_id,
                company_id=company_id,
                email_draft_id=email_draft_id,
                external_draft_id=external_draft_id,
            )
            if result is None:
                duplicate_count += 1
                continue
            reply, is_dnc_signal = result
            new_count += 1
            saved.append(reply)
            if is_dnc_signal:
                dnc_signals += 1

        if lead_id is not None:
            await self._record_sync_interaction(
                lead_id, provider_name, new_count=new_count, duplicate_count=duplicate_count
            )

        return SyncRepliesResponse(
            status=(
                ReplySyncStatus.MOCK_SYNCED.value
                if provider_name == "mock"
                else ReplySyncStatus.SYNCED.value
            ),
            provider=provider_name,
            synced_count=len(messages),
            new_count=new_count,
            duplicate_count=duplicate_count,
            do_not_contact_signals=dnc_signals,
            message=f"Synced {len(messages)} message(s): {new_count} new, "
            f"{duplicate_count} duplicate(s).",
            replies=[self._to_response(reply) for reply in saved],
        )

    async def _store_one_message(
        self,
        provider_name: str,
        message: SyncedReplyMessage,
        *,
        lead_id: UUID | None,
        company_id: UUID | None,
        email_draft_id: UUID | None,
        external_draft_id: UUID | None,
    ) -> tuple[Reply, bool] | None:
        """Store one synced message as a Reply, unless it already exists.

        Returns ``None`` for a duplicate, otherwise ``(reply, is_dnc_signal)``.
        """
        provider = EmailProviderType(provider_name)
        existing = await self._replies.get_by_provider_message_id(
            provider, message.provider_message_id
        )
        if existing is not None:
            return None

        company = await self._companies.get(company_id) if company_id else None

        try:
            analysis = await self._reply_analysis.analyze(
                ReplyAnalysisRequest(
                    company_name=company.name if company else "Unknown",
                    original_email_subject=message.subject,
                    reply_text=message.body_text or "(no content)",
                )
            )
            detected_intent = ReplyIntent(analysis.classification)
            sentiment = ReplySentiment(analysis.sentiment)
            confidence_score = analysis.confidence_score
        except Exception:
            logger.warning("reply analysis failed for a synced message", exc_info=True)
            detected_intent = None
            sentiment = None
            confidence_score = None

        reply_category = (
            _determine_reply_category(detected_intent, message.body_text or "")
            if detected_intent is not None
            else (
                ReplyCategory.UNSUBSCRIBE
                if _detect_unsubscribe_keyword(message.body_text or "")
                else ReplyCategory.UNKNOWN
            )
        )

        store_preview_only = self._settings.reply_tracking_store_body_preview_only
        body_preview = (message.body_text or "")[:500]
        body_text = None if store_preview_only else (message.body_text or None)

        reply = await self._replies.create(
            Reply(
                provider=provider,
                provider_message_id=message.provider_message_id,
                from_email=message.from_email,
                received_at=message.received_at,
                lead_id=lead_id,
                company_id=company_id,
                email_draft_id=email_draft_id,
                external_draft_id=external_draft_id,
                provider_thread_id=message.provider_thread_id,
                provider_message_url=message.provider_message_url,
                from_name=message.from_name,
                to_email=message.to_email,
                subject=message.subject,
                body_preview=body_preview,
                body_text=body_text,
                detected_intent=detected_intent,
                sentiment=sentiment,
                reply_category=reply_category,
                confidence_score=confidence_score,
            )
        )

        is_dnc_signal = reply_category == ReplyCategory.UNSUBSCRIBE
        if is_dnc_signal:
            await self._handle_unsubscribe_signal(reply, lead_id)

        return reply, is_dnc_signal

    async def _handle_unsubscribe_signal(
        self, reply: Reply, lead_id: UUID | None
    ) -> None:
        """Create a do-not-contact entry for this sender if none exists yet.

        Never sends anything, and never removes or overrides an existing
        do-not-contact entry — this only ever adds one, defensively, so a
        detected opt-out can never be silently dropped.
        """
        existing_block = await self._compliance.check(email=reply.from_email)
        if not existing_block.is_blocked:
            await self._compliance.create_entry(
                CreateDoNotContactRequest(
                    email=reply.from_email,
                    reason=(
                        "Automatically detected unsubscribe/opt-out signal "
                        f"in a reply (provider_message_id={reply.provider_message_id})."
                    ),
                    source="reply_auto_detected",
                ),
                created_by_user_id=None,
            )

        if lead_id is not None:
            await self._interactions.create(
                Interaction(
                    lead_id=lead_id,
                    type=InteractionType.NOTE,
                    status="do_not_contact_signal_detected",
                    notes=(
                        f"Reply from {reply.from_email} matched an "
                        "unsubscribe/opt-out signal. Do-not-contact entry "
                        "checked/created. No further outreach is prepared "
                        "for this lead."
                    ),
                )
            )

    async def _record_sync_interaction(
        self, lead_id: UUID, provider_name: str, *, new_count: int, duplicate_count: int
    ) -> None:
        await self._interactions.create(
            Interaction(
                lead_id=lead_id,
                type=InteractionType.EMAIL,
                status="replies_synced",
                notes=(
                    f"Reply sync via {provider_name}: {new_count} new, "
                    f"{duplicate_count} duplicate(s). No email was sent."
                ),
            )
        )
