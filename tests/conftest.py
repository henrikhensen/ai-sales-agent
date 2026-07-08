"""Shared pytest fixtures and test doubles.

``FakeWorkflowRunRepository`` and its CRM counterparts are in-memory
stand-ins for the domain repository ports (mirroring how ``MockLLMProvider``
stands in for a real LLM provider elsewhere in this test suite). This
project's DB-backed repositories (companies, leads, ...) are exercised
end-to-end via Docker Compose against real PostgreSQL rather than through
pytest, since none of the Postgres-specific column types (JSONB, native UUID)
have a lightweight in-process equivalent to test against. Using a fake at the
repository port boundary keeps service- and API-level tests fast and
dependency-free while still exercising real business logic.
"""

from __future__ import annotations

import datetime
import uuid

import pytest

from backend.domain.entities.audit_log import AuditLog
from backend.domain.entities.company import Company
from backend.domain.entities.contact import Contact
from backend.domain.entities.do_not_contact_entry import DoNotContactEntry
from backend.domain.entities.email_draft import EmailDraft
from backend.domain.entities.email_provider_connection import EmailProviderConnection
from backend.domain.entities.external_email_draft import ExternalEmailDraft
from backend.domain.entities.icp_profile import ICPProfile
from backend.domain.entities.interaction import Interaction
from backend.domain.entities.lead import Lead
from backend.domain.entities.lead_candidate import LeadCandidate
from backend.domain.entities.lead_sourcing_campaign import LeadSourcingCampaign
from backend.domain.entities.lead_sourcing_run import LeadSourcingRun
from backend.domain.entities.offer_profile import OfferProfile
from backend.domain.entities.outreach_campaign import OutreachCampaign
from backend.domain.entities.outreach_queue_item import OutreachQueueItem
from backend.domain.entities.qualification_result import QualificationResult
from backend.domain.entities.qualification_run import QualificationRun
from backend.domain.entities.reply import Reply
from backend.domain.entities.review_event import ReviewEvent
from backend.domain.entities.user import User
from backend.domain.entities.workflow_run import WorkflowRun
from backend.domain.enums import (
    EmailDraftReviewStatus,
    EmailProviderType,
    PipelineStatus,
    WorkflowReviewStatus,
)
from backend.domain.repositories.audit_log_repository import AuditLogRepository
from backend.domain.repositories.company_repository import CompanyRepository
from backend.domain.repositories.contact_repository import ContactRepository
from backend.domain.repositories.do_not_contact_repository import (
    DoNotContactRepository,
)
from backend.domain.repositories.email_draft_repository import EmailDraftRepository
from backend.domain.repositories.email_provider_connection_repository import (
    EmailProviderConnectionRepository,
)
from backend.domain.repositories.external_email_draft_repository import (
    ExternalEmailDraftRepository,
)
from backend.domain.repositories.icp_profile_repository import ICPProfileRepository
from backend.domain.repositories.interaction_repository import InteractionRepository
from backend.domain.repositories.lead_candidate_repository import (
    LeadCandidateRepository,
)
from backend.domain.repositories.lead_repository import LeadRepository
from backend.domain.repositories.lead_sourcing_campaign_repository import (
    LeadSourcingCampaignRepository,
)
from backend.domain.repositories.lead_sourcing_run_repository import (
    LeadSourcingRunRepository,
)
from backend.domain.repositories.offer_profile_repository import OfferProfileRepository
from backend.domain.repositories.outreach_campaign_repository import (
    OutreachCampaignRepository,
)
from backend.domain.repositories.outreach_queue_item_repository import (
    OutreachQueueItemRepository,
)
from backend.domain.repositories.qualification_result_repository import (
    QualificationResultRepository,
)
from backend.domain.repositories.qualification_run_repository import (
    QualificationRunRepository,
)
from backend.domain.repositories.reply_repository import ReplyRepository
from backend.domain.repositories.review_event_repository import ReviewEventRepository
from backend.domain.repositories.user_repository import UserRepository
from backend.domain.repositories.workflow_run_repository import WorkflowRunRepository


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class FakeWorkflowRunRepository(WorkflowRunRepository):
    """In-memory ``WorkflowRunRepository`` test double. No database involved."""

    def __init__(self) -> None:
        self._runs: dict[uuid.UUID, WorkflowRun] = {}

    async def create(self, run: WorkflowRun) -> WorkflowRun:
        now = _now()
        stored = WorkflowRun(
            id=uuid.uuid4(),
            company_name=run.company_name,
            workflow_type=run.workflow_type,
            status=run.status,
            review_status=run.review_status,
            input_payload=run.input_payload,
            result_payload=run.result_payload,
            confidence_score=run.confidence_score,
            missing_information=run.missing_information,
            compliance_notes=run.compliance_notes,
            company_id=run.company_id,
            lead_id=run.lead_id,
            contact_id=run.contact_id,
            email_draft_id=run.email_draft_id,
            created_at=now,
            updated_at=now,
        )
        self._runs[stored.id] = stored
        return stored

    async def get_by_id(self, run_id: uuid.UUID) -> WorkflowRun | None:
        return self._runs.get(run_id)

    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        company_name: str | None = None,
        review_status: WorkflowReviewStatus | None = None,
    ) -> list[WorkflowRun]:
        items = sorted(self._runs.values(), key=lambda run: run.created_at, reverse=True)
        if company_name:
            needle = company_name.lower()
            items = [run for run in items if needle in run.company_name.lower()]
        if review_status is not None:
            items = [run for run in items if run.review_status == review_status]
        return items[offset : offset + limit]

    async def update_review_status(
        self, run_id: uuid.UUID, review_status: WorkflowReviewStatus
    ) -> WorkflowRun | None:
        run = self._runs.get(run_id)
        if run is None:
            return None
        run.review_status = review_status
        run.updated_at = _now()
        return run

    async def update_crm_links(
        self,
        run_id: uuid.UUID,
        company_id: uuid.UUID | None = None,
        lead_id: uuid.UUID | None = None,
        contact_id: uuid.UUID | None = None,
        email_draft_id: uuid.UUID | None = None,
    ) -> WorkflowRun | None:
        run = self._runs.get(run_id)
        if run is None:
            return None
        if company_id is not None:
            run.company_id = company_id
        if lead_id is not None:
            run.lead_id = lead_id
        if contact_id is not None:
            run.contact_id = contact_id
        if email_draft_id is not None:
            run.email_draft_id = email_draft_id
        run.updated_at = _now()
        return run


class FakeCompanyRepository(CompanyRepository):
    """In-memory ``CompanyRepository`` test double. No database involved."""

    def __init__(self) -> None:
        self._companies: dict[uuid.UUID, Company] = {}

    async def create(self, entity: Company) -> Company:
        now = _now()
        stored = Company(
            id=uuid.uuid4(),
            name=entity.name,
            domain=entity.domain,
            industry=entity.industry,
            created_at=now,
            updated_at=now,
        )
        self._companies[stored.id] = stored
        return stored

    async def get(self, entity_id: uuid.UUID) -> Company | None:
        return self._companies.get(entity_id)

    async def list(self, limit: int = 100, offset: int = 0) -> list[Company]:
        items = sorted(
            self._companies.values(), key=lambda company: company.created_at, reverse=True
        )
        return items[offset : offset + limit]

    async def update(self, entity: Company) -> Company | None:
        if entity.id not in self._companies:
            return None
        entity.updated_at = _now()
        self._companies[entity.id] = entity
        return entity

    async def delete(self, entity_id: uuid.UUID) -> bool:
        return self._companies.pop(entity_id, None) is not None

    async def find_by_name(self, name: str) -> Company | None:
        needle = name.strip().lower()
        for company in self._companies.values():
            if company.name.strip().lower() == needle:
                return company
        return None

    async def find_by_domain(self, domain: str) -> Company | None:
        needle = domain.strip().lower()
        for company in self._companies.values():
            if company.domain and company.domain.strip().lower() == needle:
                return company
        return None


class FakeLeadRepository(LeadRepository):
    """In-memory ``LeadRepository`` test double. No database involved."""

    def __init__(self) -> None:
        self._leads: dict[uuid.UUID, Lead] = {}

    async def create(self, entity: Lead) -> Lead:
        now = _now()
        stored = Lead(
            id=uuid.uuid4(),
            company_id=entity.company_id,
            source=entity.source,
            status=entity.status,
            score=entity.score,
            pipeline_status=entity.pipeline_status,
            pipeline_updated_at=entity.pipeline_updated_at,
            created_at=now,
            updated_at=now,
        )
        self._leads[stored.id] = stored
        return stored

    async def get(self, entity_id: uuid.UUID) -> Lead | None:
        return self._leads.get(entity_id)

    async def list(self, limit: int = 100, offset: int = 0) -> list[Lead]:
        items = sorted(self._leads.values(), key=lambda lead: lead.created_at, reverse=True)
        return items[offset : offset + limit]

    async def update(self, entity: Lead) -> Lead | None:
        if entity.id not in self._leads:
            return None
        entity.updated_at = _now()
        self._leads[entity.id] = entity
        return entity

    async def delete(self, entity_id: uuid.UUID) -> bool:
        return self._leads.pop(entity_id, None) is not None

    async def list_by_company(
        self, company_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> list[Lead]:
        items = [lead for lead in self._leads.values() if lead.company_id == company_id]
        items.sort(key=lambda lead: lead.created_at, reverse=True)
        return items[offset : offset + limit]

    async def list_by_pipeline_status(
        self, pipeline_status: PipelineStatus, limit: int = 100, offset: int = 0
    ) -> list[Lead]:
        items = [
            lead for lead in self._leads.values() if lead.pipeline_status == pipeline_status
        ]
        items.sort(key=lambda lead: lead.created_at, reverse=True)
        return items[offset : offset + limit]

    async def update_pipeline_status(
        self, lead_id: uuid.UUID, pipeline_status: PipelineStatus
    ) -> Lead | None:
        lead = self._leads.get(lead_id)
        if lead is None:
            return None
        lead.pipeline_status = pipeline_status
        lead.pipeline_updated_at = _now()
        lead.updated_at = _now()
        return lead

    async def list_pipeline_board(self) -> list[Lead]:
        return sorted(self._leads.values(), key=lambda lead: lead.created_at, reverse=True)


class FakeContactRepository(ContactRepository):
    """In-memory ``ContactRepository`` test double. No database involved."""

    def __init__(self) -> None:
        self._contacts: dict[uuid.UUID, Contact] = {}

    async def create(self, entity: Contact) -> Contact:
        now = _now()
        stored = Contact(
            id=uuid.uuid4(),
            company_id=entity.company_id,
            first_name=entity.first_name,
            last_name=entity.last_name,
            email=entity.email,
            phone=entity.phone,
            created_at=now,
            updated_at=now,
        )
        self._contacts[stored.id] = stored
        return stored

    async def get(self, entity_id: uuid.UUID) -> Contact | None:
        return self._contacts.get(entity_id)

    async def list(self, limit: int = 100, offset: int = 0) -> list[Contact]:
        items = sorted(
            self._contacts.values(), key=lambda contact: contact.created_at, reverse=True
        )
        return items[offset : offset + limit]

    async def update(self, entity: Contact) -> Contact | None:
        if entity.id not in self._contacts:
            return None
        entity.updated_at = _now()
        self._contacts[entity.id] = entity
        return entity

    async def delete(self, entity_id: uuid.UUID) -> bool:
        return self._contacts.pop(entity_id, None) is not None

    async def find_by_company_and_name(
        self, company_id: uuid.UUID, first_name: str, last_name: str
    ) -> Contact | None:
        for contact in self._contacts.values():
            if (
                contact.company_id == company_id
                and contact.first_name.strip().lower() == first_name.strip().lower()
                and contact.last_name.strip().lower() == last_name.strip().lower()
            ):
                return contact
        return None

    async def list_by_company(
        self, company_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> list[Contact]:
        items = [c for c in self._contacts.values() if c.company_id == company_id]
        items.sort(key=lambda contact: contact.created_at, reverse=True)
        return items[offset : offset + limit]


class FakeInteractionRepository(InteractionRepository):
    """In-memory ``InteractionRepository`` test double. No database involved."""

    def __init__(self) -> None:
        self._interactions: dict[uuid.UUID, Interaction] = {}

    async def create(self, entity: Interaction) -> Interaction:
        now = _now()
        stored = Interaction(
            id=uuid.uuid4(),
            lead_id=entity.lead_id,
            type=entity.type,
            notes=entity.notes,
            status=entity.status,
            occurred_at=entity.occurred_at or now,
            created_at=now,
            updated_at=now,
        )
        self._interactions[stored.id] = stored
        return stored

    async def get(self, entity_id: uuid.UUID) -> Interaction | None:
        return self._interactions.get(entity_id)

    async def list(self, limit: int = 100, offset: int = 0) -> list[Interaction]:
        items = sorted(
            self._interactions.values(), key=lambda item: item.created_at, reverse=True
        )
        return items[offset : offset + limit]

    async def update(self, entity: Interaction) -> Interaction | None:
        if entity.id not in self._interactions:
            return None
        entity.updated_at = _now()
        self._interactions[entity.id] = entity
        return entity

    async def delete(self, entity_id: uuid.UUID) -> bool:
        return self._interactions.pop(entity_id, None) is not None

    async def list_by_lead(
        self, lead_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> list[Interaction]:
        items = [item for item in self._interactions.values() if item.lead_id == lead_id]
        items.sort(key=lambda item: item.created_at, reverse=True)
        return items[offset : offset + limit]


class FakeEmailDraftRepository(EmailDraftRepository):
    """In-memory ``EmailDraftRepository`` test double. No database involved."""

    def __init__(self) -> None:
        self._drafts: dict[uuid.UUID, EmailDraft] = {}

    async def create(self, entity: EmailDraft) -> EmailDraft:
        now = _now()
        stored = EmailDraft(
            id=uuid.uuid4(),
            company_id=entity.company_id,
            lead_id=entity.lead_id,
            workflow_run_id=entity.workflow_run_id,
            subject_lines=entity.subject_lines,
            email_body=entity.email_body,
            status=entity.status,
            review_status=entity.review_status,
            reviewer_name=entity.reviewer_name,
            review_comment=entity.review_comment,
            reviewed_at=entity.reviewed_at,
            created_at=now,
            updated_at=now,
        )
        self._drafts[stored.id] = stored
        return stored

    async def get(self, entity_id: uuid.UUID) -> EmailDraft | None:
        return self._drafts.get(entity_id)

    async def list(self, limit: int = 100, offset: int = 0) -> list[EmailDraft]:
        items = sorted(
            self._drafts.values(), key=lambda draft: draft.created_at, reverse=True
        )
        return items[offset : offset + limit]

    async def update(self, entity: EmailDraft) -> EmailDraft | None:
        if entity.id not in self._drafts:
            return None
        entity.updated_at = _now()
        self._drafts[entity.id] = entity
        return entity

    async def delete(self, entity_id: uuid.UUID) -> bool:
        return self._drafts.pop(entity_id, None) is not None

    async def list_by_company(
        self, company_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> list[EmailDraft]:
        items = [draft for draft in self._drafts.values() if draft.company_id == company_id]
        items.sort(key=lambda draft: draft.created_at, reverse=True)
        return items[offset : offset + limit]

    async def update_review_status(
        self,
        email_draft_id: uuid.UUID,
        review_status: EmailDraftReviewStatus,
        reviewer_name: str | None = None,
        comment: str | None = None,
    ) -> EmailDraft | None:
        draft = self._drafts.get(email_draft_id)
        if draft is None:
            return None
        draft.review_status = review_status
        draft.reviewer_name = reviewer_name
        draft.review_comment = comment
        draft.reviewed_at = _now()
        draft.updated_at = _now()
        return draft


class FakeReviewEventRepository(ReviewEventRepository):
    """In-memory ``ReviewEventRepository`` test double. No database involved."""

    def __init__(self) -> None:
        self._events: dict[uuid.UUID, ReviewEvent] = {}

    async def create(self, event: ReviewEvent) -> ReviewEvent:
        stored = ReviewEvent(
            id=uuid.uuid4(),
            workflow_run_id=event.workflow_run_id,
            email_draft_id=event.email_draft_id,
            event_type=event.event_type,
            previous_status=event.previous_status,
            new_status=event.new_status,
            comment=event.comment,
            reviewer_name=event.reviewer_name,
            metadata=event.metadata,
            created_at=_now(),
        )
        self._events[stored.id] = stored
        return stored

    async def list_by_workflow_run(
        self, workflow_run_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> list[ReviewEvent]:
        items = [
            event for event in self._events.values() if event.workflow_run_id == workflow_run_id
        ]
        items.sort(key=lambda event: event.created_at, reverse=True)
        return items[offset : offset + limit]

    async def list_by_email_draft(
        self, email_draft_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> list[ReviewEvent]:
        items = [
            event for event in self._events.values() if event.email_draft_id == email_draft_id
        ]
        items.sort(key=lambda event: event.created_at, reverse=True)
        return items[offset : offset + limit]


class FakeUserRepository(UserRepository):
    """In-memory ``UserRepository`` test double. No database involved."""

    def __init__(self) -> None:
        self._users: dict[uuid.UUID, User] = {}

    async def create(self, user: User) -> User:
        now = _now()
        stored = User(
            id=uuid.uuid4(),
            email=user.email,
            full_name=user.full_name,
            hashed_password=user.hashed_password,
            role=user.role,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            created_at=now,
            updated_at=now,
        )
        self._users[stored.id] = stored
        return stored

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self._users.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        for user in self._users.values():
            if user.email == email:
                return user
        return None

    async def list(self, limit: int = 100, offset: int = 0) -> list[User]:
        items = sorted(self._users.values(), key=lambda user: user.created_at, reverse=True)
        return items[offset : offset + limit]

    async def update(self, user: User) -> User | None:
        if user.id not in self._users:
            return None
        user.updated_at = _now()
        self._users[user.id] = user
        return user

    async def deactivate(self, user_id: uuid.UUID) -> User | None:
        user = self._users.get(user_id)
        if user is None:
            return None
        user.is_active = False
        user.updated_at = _now()
        return user


class FakeDoNotContactRepository(DoNotContactRepository):
    """In-memory ``DoNotContactRepository`` test double. No database involved."""

    def __init__(self) -> None:
        self._entries: dict[uuid.UUID, DoNotContactEntry] = {}

    async def create(self, entity: DoNotContactEntry) -> DoNotContactEntry:
        now = _now()
        stored = DoNotContactEntry(
            id=uuid.uuid4(),
            email=entity.email,
            domain=entity.domain,
            company_name=entity.company_name,
            company_name_normalized=entity.company_name_normalized,
            reason=entity.reason,
            source=entity.source,
            is_active=entity.is_active,
            created_by_user_id=entity.created_by_user_id,
            created_at=now,
            updated_at=now,
        )
        self._entries[stored.id] = stored
        return stored

    async def get(self, entity_id: uuid.UUID) -> DoNotContactEntry | None:
        return self._entries.get(entity_id)

    async def list(self, limit: int = 100, offset: int = 0) -> list[DoNotContactEntry]:
        items = sorted(
            self._entries.values(), key=lambda entry: entry.created_at, reverse=True
        )
        return items[offset : offset + limit]

    async def update(self, entity: DoNotContactEntry) -> DoNotContactEntry | None:
        if entity.id not in self._entries:
            return None
        entity.updated_at = _now()
        self._entries[entity.id] = entity
        return entity

    async def delete(self, entity_id: uuid.UUID) -> bool:
        return self._entries.pop(entity_id, None) is not None

    async def deactivate(self, entry_id: uuid.UUID) -> DoNotContactEntry | None:
        entry = self._entries.get(entry_id)
        if entry is None:
            return None
        entry.is_active = False
        entry.updated_at = _now()
        return entry

    async def find_active_by_email(self, email: str) -> DoNotContactEntry | None:
        for entry in self._entries.values():
            if entry.is_active and entry.email == email:
                return entry
        return None

    async def find_active_by_domain(self, domain: str) -> DoNotContactEntry | None:
        for entry in self._entries.values():
            if entry.is_active and entry.domain == domain:
                return entry
        return None

    async def find_active_by_company_name(
        self, company_name_normalized: str
    ) -> DoNotContactEntry | None:
        for entry in self._entries.values():
            if (
                entry.is_active
                and entry.company_name_normalized == company_name_normalized
            ):
                return entry
        return None


class FakeExternalEmailDraftRepository(ExternalEmailDraftRepository):
    """In-memory ``ExternalEmailDraftRepository`` test double."""

    def __init__(self) -> None:
        self._drafts: dict[uuid.UUID, ExternalEmailDraft] = {}

    async def create(self, entity: ExternalEmailDraft) -> ExternalEmailDraft:
        now = _now()
        stored = ExternalEmailDraft(
            id=uuid.uuid4(),
            email_draft_id=entity.email_draft_id,
            provider=entity.provider,
            provider_status=entity.provider_status,
            provider_draft_id=entity.provider_draft_id,
            provider_draft_url=entity.provider_draft_url,
            created_by_user_id=entity.created_by_user_id,
            last_error=entity.last_error,
            is_active=entity.is_active,
            created_at=now,
            updated_at=now,
        )
        self._drafts[stored.id] = stored
        return stored

    async def get(self, entity_id: uuid.UUID) -> ExternalEmailDraft | None:
        return self._drafts.get(entity_id)

    async def list(
        self, limit: int = 100, offset: int = 0
    ) -> list[ExternalEmailDraft]:
        items = sorted(
            self._drafts.values(), key=lambda draft: draft.created_at, reverse=True
        )
        return items[offset : offset + limit]

    async def update(self, entity: ExternalEmailDraft) -> ExternalEmailDraft | None:
        if entity.id not in self._drafts:
            return None
        entity.updated_at = _now()
        self._drafts[entity.id] = entity
        return entity

    async def delete(self, entity_id: uuid.UUID) -> bool:
        return self._drafts.pop(entity_id, None) is not None

    async def get_by_email_draft_id(
        self, email_draft_id: uuid.UUID
    ) -> ExternalEmailDraft | None:
        for draft in self._drafts.values():
            if draft.email_draft_id == email_draft_id:
                return draft
        return None


class FakeEmailProviderConnectionRepository(EmailProviderConnectionRepository):
    """In-memory ``EmailProviderConnectionRepository`` test double."""

    def __init__(self) -> None:
        self._connections: dict[uuid.UUID, EmailProviderConnection] = {}

    async def create(self, entity: EmailProviderConnection) -> EmailProviderConnection:
        now = _now()
        stored = EmailProviderConnection(
            id=uuid.uuid4(),
            user_id=entity.user_id,
            provider=entity.provider,
            encrypted_access_token=entity.encrypted_access_token,
            encrypted_refresh_token=entity.encrypted_refresh_token,
            token_expires_at=entity.token_expires_at,
            scope=entity.scope,
            external_account_email=entity.external_account_email,
            is_active=entity.is_active,
            created_at=now,
            updated_at=now,
        )
        self._connections[stored.id] = stored
        return stored

    async def get(self, entity_id: uuid.UUID) -> EmailProviderConnection | None:
        return self._connections.get(entity_id)

    async def list(
        self, limit: int = 100, offset: int = 0
    ) -> list[EmailProviderConnection]:
        items = sorted(
            self._connections.values(),
            key=lambda connection: connection.created_at,
            reverse=True,
        )
        return items[offset : offset + limit]

    async def update(
        self, entity: EmailProviderConnection
    ) -> EmailProviderConnection | None:
        if entity.id not in self._connections:
            return None
        entity.updated_at = _now()
        self._connections[entity.id] = entity
        return entity

    async def delete(self, entity_id: uuid.UUID) -> bool:
        return self._connections.pop(entity_id, None) is not None

    async def get_active_for_user(
        self, user_id: uuid.UUID, provider: EmailProviderType
    ) -> EmailProviderConnection | None:
        for connection in self._connections.values():
            if (
                connection.user_id == user_id
                and connection.provider == provider
                and connection.is_active
            ):
                return connection
        return None

    async def deactivate_for_user(
        self, user_id: uuid.UUID, provider: EmailProviderType
    ) -> EmailProviderConnection | None:
        connection = await self.get_active_for_user(user_id, provider)
        if connection is None:
            return None
        connection.is_active = False
        connection.updated_at = _now()
        return connection


def build_fake_crm_sync_service():
    """Build a ``WorkflowCrmSyncService`` wired entirely to in-memory fakes."""
    from backend.application.crm.workflow_sync_service import WorkflowCrmSyncService

    return WorkflowCrmSyncService(
        companies=FakeCompanyRepository(),
        leads=FakeLeadRepository(),
        contacts=FakeContactRepository(),
        interactions=FakeInteractionRepository(),
        email_drafts=FakeEmailDraftRepository(),
    )


def build_fake_compliance_service():
    """Build a ``DoNotContactService`` wired to a fresh in-memory fake.

    A fresh, empty repository every call — never blocks anything unless the
    caller first creates an entry via ``service.create_entry(...)``.
    """
    from backend.application.compliance.do_not_contact_service import (
        DoNotContactService,
    )

    return DoNotContactService(FakeDoNotContactRepository())


def build_fake_email_draft_integration_service(
    *,
    email_drafts=None,
    companies=None,
    workflow_runs=None,
    contacts=None,
    compliance=None,
    connections=None,
    external_drafts=None,
    settings=None,
):
    """Build an ``EmailDraftIntegrationService`` wired entirely to in-memory
    fakes, with the mock email draft provider active by default (no real
    OAuth credentials needed).
    """
    from backend.application.integrations.email_draft_integration_service import (
        EmailDraftIntegrationService,
    )
    from backend.shared.config import Settings

    return EmailDraftIntegrationService(
        connections=connections or FakeEmailProviderConnectionRepository(),
        external_drafts=external_drafts or FakeExternalEmailDraftRepository(),
        email_drafts=email_drafts or FakeEmailDraftRepository(),
        companies=companies or FakeCompanyRepository(),
        workflow_runs=workflow_runs or FakeWorkflowRunRepository(),
        contacts=contacts or FakeContactRepository(),
        compliance=compliance or build_fake_compliance_service(),
        settings=settings
        or Settings(
            EMAIL_INTEGRATION_PROVIDER="mock",
            EMAIL_INTEGRATION_ENABLE_REAL_DRAFTS=False,
        ),
    )


class FakeReplyRepository(ReplyRepository):
    """In-memory ``ReplyRepository`` test double. No database involved."""

    def __init__(self) -> None:
        self._replies: dict[uuid.UUID, Reply] = {}

    async def create(self, entity: Reply) -> Reply:
        now = _now()
        stored = Reply(
            id=uuid.uuid4(),
            lead_id=entity.lead_id,
            company_id=entity.company_id,
            email_draft_id=entity.email_draft_id,
            external_draft_id=entity.external_draft_id,
            provider=entity.provider,
            provider_message_id=entity.provider_message_id,
            provider_thread_id=entity.provider_thread_id,
            provider_message_url=entity.provider_message_url,
            from_email=entity.from_email,
            from_name=entity.from_name,
            to_email=entity.to_email,
            subject=entity.subject,
            body_preview=entity.body_preview,
            body_text=entity.body_text,
            received_at=entity.received_at,
            detected_intent=entity.detected_intent,
            sentiment=entity.sentiment,
            reply_category=entity.reply_category,
            confidence_score=entity.confidence_score,
            is_read=entity.is_read,
            is_archived=entity.is_archived,
            last_error=entity.last_error,
            created_at=now,
            updated_at=now,
        )
        self._replies[stored.id] = stored
        return stored

    async def get(self, entity_id: uuid.UUID) -> Reply | None:
        return self._replies.get(entity_id)

    async def list(self, limit: int = 100, offset: int = 0) -> list[Reply]:
        items = sorted(
            self._replies.values(), key=lambda reply: reply.received_at, reverse=True
        )
        return items[offset : offset + limit]

    async def update(self, entity: Reply) -> Reply | None:
        if entity.id not in self._replies:
            return None
        entity.updated_at = _now()
        self._replies[entity.id] = entity
        return entity

    async def delete(self, entity_id: uuid.UUID) -> bool:
        return self._replies.pop(entity_id, None) is not None

    async def get_by_provider_message_id(
        self, provider, provider_message_id: str
    ) -> Reply | None:
        for reply in self._replies.values():
            if (
                reply.provider == provider
                and reply.provider_message_id == provider_message_id
            ):
                return reply
        return None

    async def list_by_lead(
        self, lead_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> list[Reply]:
        items = [r for r in self._replies.values() if r.lead_id == lead_id]
        items.sort(key=lambda reply: reply.received_at, reverse=True)
        return items[offset : offset + limit]

    async def list_by_email_draft(
        self, email_draft_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> list[Reply]:
        items = [
            r for r in self._replies.values() if r.email_draft_id == email_draft_id
        ]
        items.sort(key=lambda reply: reply.received_at, reverse=True)
        return items[offset : offset + limit]

    async def list_filtered(
        self,
        *,
        category=None,
        sentiment=None,
        is_read: bool | None = None,
        is_archived: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Reply]:
        items = list(self._replies.values())
        if category is not None:
            items = [r for r in items if r.reply_category == category]
        if sentiment is not None:
            items = [r for r in items if r.sentiment == sentiment]
        if is_read is not None:
            items = [r for r in items if r.is_read == is_read]
        if is_archived is not None:
            items = [r for r in items if r.is_archived == is_archived]
        items.sort(key=lambda reply: reply.received_at, reverse=True)
        return items[offset : offset + limit]

    async def mark_read(self, reply_id: uuid.UUID, is_read: bool = True) -> Reply | None:
        reply = self._replies.get(reply_id)
        if reply is None:
            return None
        reply.is_read = is_read
        reply.updated_at = _now()
        return reply

    async def archive(
        self, reply_id: uuid.UUID, is_archived: bool = True
    ) -> Reply | None:
        reply = self._replies.get(reply_id)
        if reply is None:
            return None
        reply.is_archived = is_archived
        reply.updated_at = _now()
        return reply


def build_fake_reply_tracking_service(
    *,
    replies=None,
    connections=None,
    leads=None,
    companies=None,
    contacts=None,
    email_drafts=None,
    external_drafts=None,
    workflow_runs=None,
    interactions=None,
    compliance=None,
    reply_analysis=None,
    settings=None,
):
    """Build a ``ReplyTrackingService`` wired entirely to in-memory fakes,
    with the mock reply tracking provider and mock LLM provider active by
    default (no real OAuth credentials or LLM API key needed).
    """
    from backend.agents.reply_analysis.service import ReplyAnalysisService
    from backend.application.integrations.reply_tracking_service import (
        ReplyTrackingService,
    )
    from backend.infrastructure.llm.mock_provider import MockLLMProvider
    from backend.shared.config import Settings

    return ReplyTrackingService(
        replies=replies or FakeReplyRepository(),
        connections=connections or FakeEmailProviderConnectionRepository(),
        leads=leads or FakeLeadRepository(),
        companies=companies or FakeCompanyRepository(),
        contacts=contacts or FakeContactRepository(),
        email_drafts=email_drafts or FakeEmailDraftRepository(),
        external_drafts=external_drafts or FakeExternalEmailDraftRepository(),
        workflow_runs=workflow_runs or FakeWorkflowRunRepository(),
        interactions=interactions or FakeInteractionRepository(),
        compliance=compliance or build_fake_compliance_service(),
        reply_analysis=reply_analysis or ReplyAnalysisService(MockLLMProvider()),
        settings=settings
        or Settings(
            REPLY_TRACKING_PROVIDER="mock",
            REPLY_TRACKING_ENABLE_REAL_READS=False,
        ),
    )


class FakeAuditLogRepository(AuditLogRepository):
    """In-memory ``AuditLogRepository`` test double. No database involved."""

    def __init__(self) -> None:
        self._entries: dict[uuid.UUID, AuditLog] = {}

    async def create(self, entry: AuditLog) -> AuditLog:
        now = _now()
        stored = AuditLog(
            id=uuid.uuid4(),
            actor_user_id=entry.actor_user_id,
            actor_role=entry.actor_role,
            action=entry.action,
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            result=entry.result,
            reason=entry.reason,
            request_id=entry.request_id,
            ip_hash=entry.ip_hash,
            user_agent=entry.user_agent,
            metadata=entry.metadata,
            created_at=now,
        )
        self._entries[stored.id] = stored
        return stored

    async def get(self, entry_id: uuid.UUID) -> AuditLog | None:
        return self._entries.get(entry_id)

    async def list_filtered(
        self,
        *,
        actor_user_id: uuid.UUID | None = None,
        action: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        result: str | None = None,
        date_from: datetime.datetime | None = None,
        date_to: datetime.datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        items = list(self._entries.values())
        if actor_user_id is not None:
            items = [e for e in items if e.actor_user_id == actor_user_id]
        if action is not None:
            items = [e for e in items if e.action == action]
        if entity_type is not None:
            items = [e for e in items if e.entity_type == entity_type]
        if entity_id is not None:
            items = [e for e in items if e.entity_id == entity_id]
        if result is not None:
            items = [e for e in items if e.result == result]
        if date_from is not None:
            items = [e for e in items if e.created_at and e.created_at >= date_from]
        if date_to is not None:
            items = [e for e in items if e.created_at and e.created_at <= date_to]
        items.sort(key=lambda e: e.created_at or _now(), reverse=True)
        return items[offset : offset + limit]


def build_fake_audit_log_service(audit_logs=None, settings=None):
    """Build an ``AuditLogService`` wired to an in-memory fake, with audit
    logging enabled by default (unlike the global test-suite default,
    which disables it — see the ``_test_safety_defaults`` fixture below)."""
    from backend.application.audit.audit_log_service import AuditLogService
    from backend.shared.config import Settings

    return AuditLogService(
        audit_logs or FakeAuditLogRepository(),
        settings or Settings(AUDIT_LOGS_ENABLED=True),
    )


@pytest.fixture(autouse=True)
def _test_safety_defaults():
    """Keep the test suite fast and isolated from two process-global
    features that default to "on" in production:

    - Rate limiting uses an in-process counter shared by every request in
      this test session; without resetting it, unrelated tests would trip
      each other's limits (most tests log in/register at least once).
      Raised to a very high ceiling here so ordinary test traffic never
      hits it — dedicated rate-limit tests lower a specific limit back
      down for just that test via ``monkeypatch``.
    - Audit logging is disabled by default here because it would otherwise
      try to write to a real Postgres database that isn't reachable from a
      bare pytest run (this suite's DB-backed repositories are exercised
      via Docker Compose instead — see the module docstring). Dedicated
      audit-log tests re-enable it and override the repository dependency
      with ``FakeAuditLogRepository``.
    """
    from backend.shared.config import get_settings
    from backend.shared.rate_limit import reset_memory_store

    reset_memory_store()
    settings = get_settings()
    original_values = {
        "rate_limit_auth_per_minute": settings.rate_limit_auth_per_minute,
        "rate_limit_workflow_per_hour": settings.rate_limit_workflow_per_hour,
        "rate_limit_website_research_per_hour": settings.rate_limit_website_research_per_hour,
        "rate_limit_llm_test_per_hour": settings.rate_limit_llm_test_per_hour,
        "rate_limit_external_draft_per_hour": settings.rate_limit_external_draft_per_hour,
        "rate_limit_reply_sync_per_hour": settings.rate_limit_reply_sync_per_hour,
        "rate_limit_compliance_check_per_minute": settings.rate_limit_compliance_check_per_minute,
        "audit_logs_enabled": settings.audit_logs_enabled,
    }
    for name in original_values:
        if name == "audit_logs_enabled":
            setattr(settings, name, False)
        else:
            setattr(settings, name, 1_000_000)
    yield
    for name, value in original_values.items():
        setattr(settings, name, value)
    reset_memory_store()


class FakeICPProfileRepository(ICPProfileRepository):
    """In-memory ``ICPProfileRepository`` test double. No database involved."""

    def __init__(self) -> None:
        self._profiles: dict[uuid.UUID, ICPProfile] = {}

    async def create(self, profile: ICPProfile) -> ICPProfile:
        now = _now()
        stored = ICPProfile(
            id=uuid.uuid4(),
            name=profile.name,
            description=profile.description,
            target_industries=profile.target_industries,
            excluded_industries=profile.excluded_industries,
            target_company_sizes=profile.target_company_sizes,
            target_locations=profile.target_locations,
            target_languages=profile.target_languages,
            target_keywords=profile.target_keywords,
            negative_keywords=profile.negative_keywords,
            target_pain_points=profile.target_pain_points,
            buying_triggers=profile.buying_triggers,
            required_signals=profile.required_signals,
            excluded_signals=profile.excluded_signals,
            buyer_personas=profile.buyer_personas,
            preferred_titles=profile.preferred_titles,
            excluded_titles=profile.excluded_titles,
            minimum_fit_score=profile.minimum_fit_score,
            scoring_weights=profile.scoring_weights,
            is_active=profile.is_active,
            created_by_user_id=profile.created_by_user_id,
            created_at=now,
            updated_at=now,
        )
        self._profiles[stored.id] = stored
        return stored

    async def list(
        self, limit: int = 100, offset: int = 0, active_only: bool = False
    ) -> list[ICPProfile]:
        items = list(self._profiles.values())
        if active_only:
            items = [p for p in items if p.is_active]
        items.sort(key=lambda p: p.created_at, reverse=True)
        return items[offset : offset + limit]

    async def get_by_id(self, profile_id: uuid.UUID) -> ICPProfile | None:
        return self._profiles.get(profile_id)

    async def update(self, profile: ICPProfile) -> ICPProfile | None:
        if profile.id not in self._profiles:
            return None
        profile.updated_at = _now()
        self._profiles[profile.id] = profile
        return profile

    async def deactivate(self, profile_id: uuid.UUID) -> ICPProfile | None:
        profile = self._profiles.get(profile_id)
        if profile is None:
            return None
        profile.is_active = False
        profile.updated_at = _now()
        return profile

    async def get_active(self, profile_id: uuid.UUID) -> ICPProfile | None:
        profile = self._profiles.get(profile_id)
        if profile is None or not profile.is_active:
            return None
        return profile


def build_fake_icp_service(icp_profiles=None):
    """Build an ``ICPService`` wired to a fresh in-memory fake."""
    from backend.application.sales_strategy.icp_service import ICPService

    return ICPService(icp_profiles or FakeICPProfileRepository())


class FakeOfferProfileRepository(OfferProfileRepository):
    """In-memory ``OfferProfileRepository`` test double. No database involved."""

    def __init__(self) -> None:
        self._profiles: dict[uuid.UUID, OfferProfile] = {}

    async def create(self, profile: OfferProfile) -> OfferProfile:
        now = _now()
        stored = OfferProfile(
            id=uuid.uuid4(),
            name=profile.name,
            main_value_proposition=profile.main_value_proposition,
            description=profile.description,
            target_outcome=profile.target_outcome,
            pain_points_solved=profile.pain_points_solved,
            key_benefits=profile.key_benefits,
            differentiators=profile.differentiators,
            proof_points=profile.proof_points,
            case_study_notes=profile.case_study_notes,
            pricing_notes=profile.pricing_notes,
            call_to_action=profile.call_to_action,
            tone=profile.tone,
            language=profile.language,
            forbidden_claims=profile.forbidden_claims,
            required_disclaimers=profile.required_disclaimers,
            is_active=profile.is_active,
            created_by_user_id=profile.created_by_user_id,
            created_at=now,
            updated_at=now,
        )
        self._profiles[stored.id] = stored
        return stored

    async def list(
        self, limit: int = 100, offset: int = 0, active_only: bool = False
    ) -> list[OfferProfile]:
        items = list(self._profiles.values())
        if active_only:
            items = [p for p in items if p.is_active]
        items.sort(key=lambda p: p.created_at, reverse=True)
        return items[offset : offset + limit]

    async def get_by_id(self, profile_id: uuid.UUID) -> OfferProfile | None:
        return self._profiles.get(profile_id)

    async def update(self, profile: OfferProfile) -> OfferProfile | None:
        if profile.id not in self._profiles:
            return None
        profile.updated_at = _now()
        self._profiles[profile.id] = profile
        return profile

    async def deactivate(self, profile_id: uuid.UUID) -> OfferProfile | None:
        profile = self._profiles.get(profile_id)
        if profile is None:
            return None
        profile.is_active = False
        profile.updated_at = _now()
        return profile

    async def get_active(self, profile_id: uuid.UUID) -> OfferProfile | None:
        profile = self._profiles.get(profile_id)
        if profile is None or not profile.is_active:
            return None
        return profile


def build_fake_offer_service(offer_profiles=None):
    """Build an ``OfferService`` wired to a fresh in-memory fake."""
    from backend.application.sales_strategy.offer_service import OfferService

    return OfferService(offer_profiles or FakeOfferProfileRepository())


class FakeLeadSourcingCampaignRepository(LeadSourcingCampaignRepository):
    """In-memory ``LeadSourcingCampaignRepository`` test double."""

    def __init__(self) -> None:
        self._campaigns: dict[uuid.UUID, LeadSourcingCampaign] = {}

    async def create(self, campaign: LeadSourcingCampaign) -> LeadSourcingCampaign:
        now = _now()
        stored = LeadSourcingCampaign(
            id=uuid.uuid4(),
            name=campaign.name,
            description=campaign.description,
            icp_profile_id=campaign.icp_profile_id,
            offer_profile_id=campaign.offer_profile_id,
            source_type=campaign.source_type,
            search_query=campaign.search_query,
            target_industry=campaign.target_industry,
            target_location=campaign.target_location,
            target_keywords=campaign.target_keywords,
            excluded_keywords=campaign.excluded_keywords,
            max_results=campaign.max_results,
            status=campaign.status,
            created_by_user_id=campaign.created_by_user_id,
            created_at=now,
            updated_at=now,
        )
        self._campaigns[stored.id] = stored
        return stored

    async def list(
        self, limit: int = 100, offset: int = 0, status: str | None = None
    ) -> list[LeadSourcingCampaign]:
        items = list(self._campaigns.values())
        if status:
            items = [c for c in items if c.status == status]
        items.sort(key=lambda c: c.created_at, reverse=True)
        return items[offset : offset + limit]

    async def get_by_id(self, campaign_id: uuid.UUID) -> LeadSourcingCampaign | None:
        return self._campaigns.get(campaign_id)

    async def update(
        self, campaign: LeadSourcingCampaign
    ) -> LeadSourcingCampaign | None:
        if campaign.id not in self._campaigns:
            return None
        campaign.updated_at = _now()
        self._campaigns[campaign.id] = campaign
        return campaign

    async def archive(self, campaign_id: uuid.UUID) -> LeadSourcingCampaign | None:
        campaign = self._campaigns.get(campaign_id)
        if campaign is None:
            return None
        campaign.status = "archived"
        campaign.updated_at = _now()
        return campaign


class FakeLeadSourcingRunRepository(LeadSourcingRunRepository):
    """In-memory ``LeadSourcingRunRepository`` test double."""

    def __init__(self) -> None:
        self._runs: dict[uuid.UUID, LeadSourcingRun] = {}

    async def create(self, run: LeadSourcingRun) -> LeadSourcingRun:
        now = _now()
        stored = LeadSourcingRun(
            id=uuid.uuid4(),
            campaign_id=run.campaign_id,
            status=run.status,
            provider=run.provider,
            started_by_user_id=run.started_by_user_id,
            started_at=run.started_at,
            completed_at=run.completed_at,
            total_candidates_found=run.total_candidates_found,
            total_candidates_saved=run.total_candidates_saved,
            total_duplicates=run.total_duplicates,
            total_blocked_by_do_not_contact=run.total_blocked_by_do_not_contact,
            total_errors=run.total_errors,
            warnings=run.warnings,
            created_at=now,
            updated_at=now,
        )
        self._runs[stored.id] = stored
        return stored

    async def get_by_id(self, run_id: uuid.UUID) -> LeadSourcingRun | None:
        return self._runs.get(run_id)

    async def list(
        self, limit: int = 100, offset: int = 0, campaign_id: uuid.UUID | None = None
    ) -> list[LeadSourcingRun]:
        items = list(self._runs.values())
        if campaign_id is not None:
            items = [r for r in items if r.campaign_id == campaign_id]
        items.sort(key=lambda r: r.created_at, reverse=True)
        return items[offset : offset + limit]

    async def update(self, run: LeadSourcingRun) -> LeadSourcingRun | None:
        if run.id not in self._runs:
            return None
        run.updated_at = _now()
        self._runs[run.id] = run
        return run


class FakeLeadCandidateRepository(LeadCandidateRepository):
    """In-memory ``LeadCandidateRepository`` test double."""

    def __init__(self) -> None:
        self._candidates: dict[uuid.UUID, LeadCandidate] = {}

    async def create(self, candidate: LeadCandidate) -> LeadCandidate:
        now = _now()
        stored = LeadCandidate(
            id=uuid.uuid4(),
            sourcing_run_id=candidate.sourcing_run_id,
            campaign_id=candidate.campaign_id,
            company_name=candidate.company_name,
            company_domain=candidate.company_domain,
            company_website_url=candidate.company_website_url,
            industry=candidate.industry,
            location=candidate.location,
            description=candidate.description,
            source_url=candidate.source_url,
            source_name=candidate.source_name,
            source_type=candidate.source_type,
            public_contact_email=candidate.public_contact_email,
            contact_page_url=candidate.contact_page_url,
            confidence_score=candidate.confidence_score,
            icp_fit_score=candidate.icp_fit_score,
            icp_fit_level=candidate.icp_fit_level,
            matched_signals=candidate.matched_signals,
            negative_signals=candidate.negative_signals,
            do_not_contact_status=candidate.do_not_contact_status,
            duplicate_status=candidate.duplicate_status,
            review_status=candidate.review_status,
            crm_company_id=candidate.crm_company_id,
            crm_lead_id=candidate.crm_lead_id,
            notes=candidate.notes,
            warnings=candidate.warnings,
            created_at=now,
            updated_at=now,
        )
        self._candidates[stored.id] = stored
        return stored

    async def get_by_id(self, candidate_id: uuid.UUID) -> LeadCandidate | None:
        return self._candidates.get(candidate_id)

    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        campaign_id: uuid.UUID | None = None,
        sourcing_run_id: uuid.UUID | None = None,
        review_status: str | None = None,
    ) -> list[LeadCandidate]:
        items = list(self._candidates.values())
        if campaign_id is not None:
            items = [c for c in items if c.campaign_id == campaign_id]
        if sourcing_run_id is not None:
            items = [c for c in items if c.sourcing_run_id == sourcing_run_id]
        if review_status is not None:
            items = [c for c in items if c.review_status == review_status]
        items.sort(key=lambda c: c.created_at, reverse=True)
        return items[offset : offset + limit]

    async def update(self, candidate: LeadCandidate) -> LeadCandidate | None:
        if candidate.id not in self._candidates:
            return None
        candidate.updated_at = _now()
        self._candidates[candidate.id] = candidate
        return candidate

    async def find_existing(
        self, *, company_domain: str | None, company_name: str | None
    ) -> LeadCandidate | None:
        if company_domain:
            needle = company_domain.strip().lower()
            for candidate in self._candidates.values():
                if candidate.company_domain and candidate.company_domain.lower() == needle:
                    return candidate
        if company_name:
            needle = company_name.strip().lower()
            for candidate in self._candidates.values():
                if candidate.company_name and candidate.company_name.lower() == needle:
                    return candidate
        return None


class FakeWebsiteResearchService:
    """Test double for ``WebsiteResearchService``: returns a canned result
    per URL (or an empty-but-valid default), never performs a real network
    fetch. Distinct from the file-local class of the same name in
    ``test_sales_workflow_service.py``, which additionally supports
    ``allow_calls=False`` — this one is for lead sourcing tests, where
    every candidate with a website URL is expected to be researched.
    """

    def __init__(self, responses=None, default_error: Exception | None = None) -> None:
        self._responses = responses or {}
        self._default_error = default_error
        self.calls: list = []

    async def research(self, request):
        from urllib.parse import urlparse

        from backend.application.research.schemas import WebsiteResearchResponse

        self.calls.append(request)
        if request.url in self._responses:
            return self._responses[request.url]
        if self._default_error is not None:
            raise self._default_error
        domain = urlparse(request.url).hostname or ""
        return WebsiteResearchResponse(
            url=request.url,
            final_url=request.url,
            domain=domain,
            title=None,
            meta_description=None,
            extracted_text="",
            text_length=0,
            pages_fetched=1,
            sources_used=[request.url],
            warnings=[],
        )


def build_fake_website_research_service(responses=None, default_error=None):
    """Build a fresh ``FakeWebsiteResearchService``."""
    return FakeWebsiteResearchService(responses=responses, default_error=default_error)


def build_fake_lead_sourcing_service(
    *,
    campaigns=None,
    runs=None,
    candidates=None,
    companies=None,
    leads=None,
    compliance=None,
    icp_service=None,
    website_research=None,
    audit=None,
    settings=None,
):
    """Build a ``LeadSourcingService`` wired to fresh in-memory fakes.

    Every dependency is optional so tests can inject a specific fake (e.g.
    a pre-populated ``FakeCompanyRepository`` for duplicate detection)
    while leaving the rest at sensible, empty defaults.
    """
    from backend.application.lead_sourcing.lead_sourcing_service import (
        LeadSourcingService,
    )
    from backend.shared.config import get_settings

    return LeadSourcingService(
        campaigns=campaigns or FakeLeadSourcingCampaignRepository(),
        runs=runs or FakeLeadSourcingRunRepository(),
        candidates=candidates or FakeLeadCandidateRepository(),
        companies=companies or FakeCompanyRepository(),
        leads=leads or FakeLeadRepository(),
        compliance=compliance or build_fake_compliance_service(),
        icp_service=icp_service or build_fake_icp_service(),
        website_research=website_research or build_fake_website_research_service(),
        audit=audit or build_fake_audit_log_service(),
        settings=settings or get_settings(),
    )


class FakeQualificationRunRepository(QualificationRunRepository):
    """In-memory ``QualificationRunRepository`` test double."""

    def __init__(self) -> None:
        self._runs: dict[uuid.UUID, QualificationRun] = {}

    async def create(self, run: QualificationRun) -> QualificationRun:
        now = _now()
        stored = QualificationRun(
            id=uuid.uuid4(),
            name=run.name,
            source_type=run.source_type,
            icp_profile_id=run.icp_profile_id,
            offer_profile_id=run.offer_profile_id,
            status=run.status,
            started_by_user_id=run.started_by_user_id,
            started_at=run.started_at,
            completed_at=run.completed_at,
            total_items=run.total_items,
            qualified_count=run.qualified_count,
            priority_count=run.priority_count,
            disqualified_count=run.disqualified_count,
            needs_review_count=run.needs_review_count,
            average_score=run.average_score,
            warnings=run.warnings,
            created_at=now,
            updated_at=now,
        )
        self._runs[stored.id] = stored
        return stored

    async def get_by_id(self, run_id: uuid.UUID) -> QualificationRun | None:
        return self._runs.get(run_id)

    async def list(self, limit: int = 100, offset: int = 0) -> list[QualificationRun]:
        items = sorted(self._runs.values(), key=lambda r: r.created_at, reverse=True)
        return items[offset : offset + limit]

    async def update(self, run: QualificationRun) -> QualificationRun | None:
        if run.id not in self._runs:
            return None
        run.updated_at = _now()
        self._runs[run.id] = run
        return run


class FakeQualificationResultRepository(QualificationResultRepository):
    """In-memory ``QualificationResultRepository`` test double."""

    def __init__(self) -> None:
        self._results: dict[uuid.UUID, QualificationResult] = {}

    async def create(self, result: QualificationResult) -> QualificationResult:
        now = _now()
        stored = QualificationResult(
            id=uuid.uuid4(),
            qualification_run_id=result.qualification_run_id,
            lead_candidate_id=result.lead_candidate_id,
            lead_id=result.lead_id,
            company_id=result.company_id,
            icp_profile_id=result.icp_profile_id,
            offer_profile_id=result.offer_profile_id,
            qualification_score=result.qualification_score,
            qualification_level=result.qualification_level,
            qualification_status=result.qualification_status,
            priority_rank=result.priority_rank,
            fit_summary=result.fit_summary,
            score_breakdown=result.score_breakdown,
            positive_signals=result.positive_signals,
            negative_signals=result.negative_signals,
            missing_data=result.missing_data,
            recommended_next_action=result.recommended_next_action,
            recommended_outreach_angle=result.recommended_outreach_angle,
            disqualification_reason=result.disqualification_reason,
            compliance_status=result.compliance_status,
            do_not_contact_status=result.do_not_contact_status,
            duplicate_status=result.duplicate_status,
            pipeline_status=result.pipeline_status,
            confidence_score=result.confidence_score,
            reviewed_by_user_id=result.reviewed_by_user_id,
            reviewed_at=result.reviewed_at,
            created_at=now,
            updated_at=now,
        )
        self._results[stored.id] = stored
        return stored

    async def get_by_id(self, result_id: uuid.UUID) -> QualificationResult | None:
        return self._results.get(result_id)

    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        qualification_run_id: uuid.UUID | None = None,
        qualification_status: str | None = None,
    ) -> list[QualificationResult]:
        items = list(self._results.values())
        if qualification_run_id is not None:
            items = [r for r in items if r.qualification_run_id == qualification_run_id]
        if qualification_status is not None:
            items = [r for r in items if r.qualification_status == qualification_status]
        items.sort(key=lambda r: r.created_at, reverse=True)
        return items[offset : offset + limit]

    async def update(self, result: QualificationResult) -> QualificationResult | None:
        if result.id not in self._results:
            return None
        result.updated_at = _now()
        self._results[result.id] = result
        return result

    async def find_latest_for_candidate(
        self, lead_candidate_id: uuid.UUID
    ) -> QualificationResult | None:
        candidates = [
            r for r in self._results.values() if r.lead_candidate_id == lead_candidate_id
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda r: r.created_at)

    async def find_latest_for_lead(
        self, lead_id: uuid.UUID
    ) -> QualificationResult | None:
        candidates = [r for r in self._results.values() if r.lead_id == lead_id]
        if not candidates:
            return None
        return max(candidates, key=lambda r: r.created_at)


def build_fake_lead_qualification_service(
    *,
    runs=None,
    results=None,
    lead_candidates=None,
    companies=None,
    leads=None,
    compliance=None,
    icp_service=None,
    offer_service=None,
    website_research=None,
    audit=None,
    settings=None,
):
    """Build a ``LeadQualificationService`` wired to fresh in-memory fakes."""
    from backend.application.lead_qualification.lead_qualification_service import (
        LeadQualificationService,
    )
    from backend.shared.config import get_settings

    return LeadQualificationService(
        runs=runs or FakeQualificationRunRepository(),
        results=results or FakeQualificationResultRepository(),
        lead_candidates=lead_candidates or FakeLeadCandidateRepository(),
        companies=companies or FakeCompanyRepository(),
        leads=leads or FakeLeadRepository(),
        compliance=compliance or build_fake_compliance_service(),
        icp_service=icp_service or build_fake_icp_service(),
        offer_service=offer_service or build_fake_offer_service(),
        website_research=website_research or build_fake_website_research_service(),
        audit=audit or build_fake_audit_log_service(),
        settings=settings or get_settings(),
    )


class FakeOutreachCampaignRepository(OutreachCampaignRepository):
    """In-memory ``OutreachCampaignRepository`` test double."""

    def __init__(self) -> None:
        self._campaigns: dict[uuid.UUID, OutreachCampaign] = {}

    async def create(self, campaign: OutreachCampaign) -> OutreachCampaign:
        now = _now()
        stored = OutreachCampaign(
            id=uuid.uuid4(),
            name=campaign.name,
            description=campaign.description,
            icp_profile_id=campaign.icp_profile_id,
            offer_profile_id=campaign.offer_profile_id,
            target_language=campaign.target_language,
            tone=campaign.tone,
            min_qualification_score=campaign.min_qualification_score,
            allowed_qualification_levels=campaign.allowed_qualification_levels,
            excluded_statuses=campaign.excluded_statuses,
            max_queue_items=campaign.max_queue_items,
            status=campaign.status,
            created_by_user_id=campaign.created_by_user_id,
            created_at=now,
            updated_at=now,
        )
        self._campaigns[stored.id] = stored
        return stored

    async def get_by_id(self, campaign_id: uuid.UUID) -> OutreachCampaign | None:
        return self._campaigns.get(campaign_id)

    async def list(
        self, limit: int = 100, offset: int = 0, status: str | None = None
    ) -> list[OutreachCampaign]:
        items = list(self._campaigns.values())
        if status:
            items = [c for c in items if c.status == status]
        items.sort(key=lambda c: c.created_at, reverse=True)
        return items[offset : offset + limit]

    async def update(self, campaign: OutreachCampaign) -> OutreachCampaign | None:
        if campaign.id not in self._campaigns:
            return None
        campaign.updated_at = _now()
        self._campaigns[campaign.id] = campaign
        return campaign

    async def archive(self, campaign_id: uuid.UUID) -> OutreachCampaign | None:
        campaign = self._campaigns.get(campaign_id)
        if campaign is None:
            return None
        campaign.status = "archived"
        campaign.updated_at = _now()
        return campaign

    async def set_status(
        self, campaign_id: uuid.UUID, status: str
    ) -> OutreachCampaign | None:
        campaign = self._campaigns.get(campaign_id)
        if campaign is None:
            return None
        campaign.status = status
        campaign.updated_at = _now()
        return campaign


class FakeOutreachQueueItemRepository(OutreachQueueItemRepository):
    """In-memory ``OutreachQueueItemRepository`` test double."""

    def __init__(self) -> None:
        self._items: dict[uuid.UUID, OutreachQueueItem] = {}

    async def create(self, item: OutreachQueueItem) -> OutreachQueueItem:
        now = _now()
        stored = OutreachQueueItem(
            id=uuid.uuid4(),
            campaign_id=item.campaign_id,
            lead_id=item.lead_id,
            company_id=item.company_id,
            lead_candidate_id=item.lead_candidate_id,
            qualification_result_id=item.qualification_result_id,
            icp_profile_id=item.icp_profile_id,
            offer_profile_id=item.offer_profile_id,
            priority_rank=item.priority_rank,
            qualification_score=item.qualification_score,
            qualification_level=item.qualification_level,
            queue_status=item.queue_status,
            recommended_outreach_angle=item.recommended_outreach_angle,
            personalization_notes=item.personalization_notes,
            compliance_status=item.compliance_status,
            do_not_contact_status=item.do_not_contact_status,
            duplicate_status=item.duplicate_status,
            workflow_run_id=item.workflow_run_id,
            email_draft_id=item.email_draft_id,
            review_id=item.review_id,
            external_draft_id=item.external_draft_id,
            last_action=item.last_action,
            last_error=item.last_error,
            created_by_user_id=item.created_by_user_id,
            assigned_to_user_id=item.assigned_to_user_id,
            created_at=now,
            updated_at=now,
        )
        self._items[stored.id] = stored
        return stored

    async def get_by_id(self, item_id: uuid.UUID) -> OutreachQueueItem | None:
        return self._items.get(item_id)

    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        campaign_id: uuid.UUID | None = None,
        queue_status: str | None = None,
    ) -> list[OutreachQueueItem]:
        items = list(self._items.values())
        if campaign_id is not None:
            items = [i for i in items if i.campaign_id == campaign_id]
        if queue_status is not None:
            items = [i for i in items if i.queue_status == queue_status]
        items.sort(key=lambda i: i.created_at, reverse=True)
        return items[offset : offset + limit]

    async def update(self, item: OutreachQueueItem) -> OutreachQueueItem | None:
        if item.id not in self._items:
            return None
        item.updated_at = _now()
        self._items[item.id] = item
        return item

    async def list_by_campaign(
        self, campaign_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> list[OutreachQueueItem]:
        return await self.list(limit=limit, offset=offset, campaign_id=campaign_id)

    async def list_by_status(
        self, queue_status: str, limit: int = 100, offset: int = 0
    ) -> list[OutreachQueueItem]:
        return await self.list(limit=limit, offset=offset, queue_status=queue_status)

    async def list_ready_for_workflow(
        self, campaign_id: uuid.UUID, limit: int = 100
    ) -> list[OutreachQueueItem]:
        items = [
            i
            for i in self._items.values()
            if i.campaign_id == campaign_id
            and i.queue_status in ("queued", "ready_for_workflow")
        ]
        items.sort(key=lambda i: (i.priority_rank is None, i.priority_rank, i.created_at))
        return items[:limit]

    async def find_existing_item(
        self,
        campaign_id: uuid.UUID,
        *,
        lead_id: uuid.UUID | None,
        company_id: uuid.UUID | None,
        lead_candidate_id: uuid.UUID | None,
    ) -> OutreachQueueItem | None:
        candidates = [i for i in self._items.values() if i.campaign_id == campaign_id]
        if lead_candidate_id is not None:
            candidates = [i for i in candidates if i.lead_candidate_id == lead_candidate_id]
        elif lead_id is not None:
            candidates = [i for i in candidates if i.lead_id == lead_id]
        elif company_id is not None:
            candidates = [i for i in candidates if i.company_id == company_id]
        else:
            return None
        if not candidates:
            return None
        return max(candidates, key=lambda i: i.created_at)


def build_fake_outreach_queue_service(
    *,
    campaigns=None,
    queue_items=None,
    qualification_results=None,
    lead_candidates=None,
    companies=None,
    leads=None,
    compliance=None,
    offer_service=None,
    sales_workflow=None,
    audit=None,
    settings=None,
):
    """Build an ``OutreachQueueService`` wired to fresh in-memory fakes.

    ``sales_workflow`` defaults to a real ``SalesWorkflowService`` built
    entirely from fakes and the deterministic ``MockLLMProvider`` — never a
    network call — so ``prepare_queue_item_workflow``/``prepare_batch``
    exercise the real Sales Workflow / Email Draft creation path.
    """
    from backend.agents.company_intelligence.service import CompanyIntelligenceService
    from backend.agents.email_draft.service import EmailDraftService
    from backend.agents.lead_research.service import LeadResearchService
    from backend.agents.personalization.service import PersonalizationService
    from backend.application.crm.workflow_sync_service import WorkflowCrmSyncService
    from backend.application.outreach.outreach_queue_service import (
        OutreachQueueService,
    )
    from backend.application.workflows.history_service import WorkflowHistoryService
    from backend.application.workflows.sales_workflow import SalesWorkflowService
    from backend.infrastructure.llm.mock_provider import MockLLMProvider
    from backend.shared.config import get_settings

    companies = companies or FakeCompanyRepository()
    leads = leads or FakeLeadRepository()
    compliance = compliance or build_fake_compliance_service()
    offer_service = offer_service or build_fake_offer_service()

    if sales_workflow is None:
        llm = MockLLMProvider()
        sales_workflow = SalesWorkflowService(
            lead_research=LeadResearchService(llm),
            company_intelligence=CompanyIntelligenceService(llm),
            personalization=PersonalizationService(llm),
            email_draft=EmailDraftService(llm),
            history=WorkflowHistoryService(FakeWorkflowRunRepository()),
            crm_sync=WorkflowCrmSyncService(
                companies=companies,
                leads=leads,
                contacts=FakeContactRepository(),
                interactions=FakeInteractionRepository(),
                email_drafts=FakeEmailDraftRepository(),
            ),
            website_research=_unused_website_research_service_for_outreach(),
            compliance=compliance,
            icp_service=build_fake_icp_service(),
            offer_service=offer_service,
        )

    return OutreachQueueService(
        campaigns=campaigns or FakeOutreachCampaignRepository(),
        queue_items=queue_items or FakeOutreachQueueItemRepository(),
        qualification_results=qualification_results or FakeQualificationResultRepository(),
        lead_candidates=lead_candidates or FakeLeadCandidateRepository(),
        companies=companies,
        leads=leads,
        compliance=compliance,
        offer_service=offer_service,
        sales_workflow=sales_workflow,
        audit=audit or build_fake_audit_log_service(),
        settings=settings or get_settings(),
    )


def _unused_website_research_service_for_outreach():
    class _NoWebsiteResearch:
        async def research(self, request):  # noqa: ANN001, ARG002
            raise AssertionError(
                "WebsiteResearchService.research() should not be called from the "
                "Outreach Queue's Sales Workflow preparation (use_website_research "
                "is not requested)."
            )

    return _NoWebsiteResearch()
