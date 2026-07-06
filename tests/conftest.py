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

from backend.domain.entities.company import Company
from backend.domain.entities.contact import Contact
from backend.domain.entities.do_not_contact_entry import DoNotContactEntry
from backend.domain.entities.email_draft import EmailDraft
from backend.domain.entities.email_provider_connection import EmailProviderConnection
from backend.domain.entities.external_email_draft import ExternalEmailDraft
from backend.domain.entities.interaction import Interaction
from backend.domain.entities.lead import Lead
from backend.domain.entities.review_event import ReviewEvent
from backend.domain.entities.user import User
from backend.domain.entities.workflow_run import WorkflowRun
from backend.domain.enums import (
    EmailDraftReviewStatus,
    EmailProviderType,
    PipelineStatus,
    WorkflowReviewStatus,
)
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
from backend.domain.repositories.interaction_repository import InteractionRepository
from backend.domain.repositories.lead_repository import LeadRepository
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
