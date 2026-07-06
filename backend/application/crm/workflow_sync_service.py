"""CRM Sync for Sales Workflows.

After a sales workflow run has produced its analysis and email draft,
``WorkflowCrmSyncService`` finds-or-creates the Company and Lead the run
belongs to, optionally finds-or-creates a Contact, saves the produced email
draft, and records an Interaction/Activity summarizing what happened.

This is bookkeeping only: it never sends an email, never contacts anyone,
and never books a meeting. Everything it writes is a draft or an internal
CRM record awaiting human review.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from backend.application.workflows.schemas import (
    SalesWorkflowRequest,
    SalesWorkflowResponse,
)
from backend.domain.entities.company import Company
from backend.domain.entities.contact import Contact
from backend.domain.entities.email_draft import EmailDraft
from backend.domain.entities.interaction import Interaction
from backend.domain.entities.lead import Lead
from backend.domain.enums import InteractionType, LeadSource, PipelineStatus
from backend.domain.repositories.company_repository import CompanyRepository
from backend.domain.repositories.contact_repository import ContactRepository
from backend.domain.repositories.email_draft_repository import EmailDraftRepository
from backend.domain.repositories.interaction_repository import InteractionRepository
from backend.domain.repositories.lead_repository import LeadRepository


@dataclass(frozen=True)
class WorkflowCrmLinks:
    """CRM entity ids produced by syncing one completed sales workflow run."""

    company_id: UUID
    lead_id: UUID
    contact_id: UUID | None = None
    email_draft_id: UUID | None = None


class WorkflowCrmSyncService:
    """Persists CRM bookkeeping for a completed sales workflow run.

    Only ever creates or updates CRM records (Company, Lead, an optional
    Contact, an email draft, and an Interaction/Activity). It never sends an
    email, contacts anyone, or books a meeting.
    """

    def __init__(
        self,
        companies: CompanyRepository,
        leads: LeadRepository,
        contacts: ContactRepository,
        interactions: InteractionRepository,
        email_drafts: EmailDraftRepository,
    ) -> None:
        self._companies = companies
        self._leads = leads
        self._contacts = contacts
        self._interactions = interactions
        self._email_drafts = email_drafts

    async def sync(
        self,
        request: SalesWorkflowRequest,
        response: SalesWorkflowResponse,
        workflow_run_id: UUID,
    ) -> WorkflowCrmLinks:
        """Sync CRM records for one completed run and return their ids.

        If the run was blocked by an active do-not-contact entry
        (``response.email_draft is None``), Company/Lead/Contact records are
        still synced (so the block is visible in the CRM), but no email
        draft is created, no Interaction other than the block itself is
        recorded, and the lead's pipeline stage does NOT advance to
        "draft_created".
        """
        company = await self._find_or_create_company(request)
        lead = await self._find_or_create_lead(company.id)
        contact = await self._find_or_create_contact(company.id, request)

        if response.email_draft is None:
            await self._record_blocked_interaction(lead.id, workflow_run_id, response)
            return WorkflowCrmLinks(
                company_id=company.id,
                lead_id=lead.id,
                contact_id=contact.id if contact is not None else None,
                email_draft_id=None,
            )

        email_draft = await self._save_email_draft(
            company.id, lead.id, workflow_run_id, response
        )
        # Every successful sales workflow run produces an email draft, so the
        # lead's pipeline stage advances to "draft_created" right away. A
        # later phase may introduce an intermediate "research_completed"
        # stage; for now this single transition is sufficient (see the CRM
        # Pipeline section of the README).
        await self._leads.update_pipeline_status(lead.id, PipelineStatus.DRAFT_CREATED)
        await self._record_interaction(lead.id, email_draft.id, workflow_run_id, response)

        return WorkflowCrmLinks(
            company_id=company.id,
            lead_id=lead.id,
            contact_id=contact.id if contact is not None else None,
            email_draft_id=email_draft.id,
        )

    async def _find_or_create_company(self, request: SalesWorkflowRequest) -> Company:
        existing = await self._companies.find_by_name(request.company_name)
        if existing is not None:
            return existing
        website_domain = (
            request.website_url.host if request.website_url is not None else None
        )
        return await self._companies.create(
            Company(
                name=request.company_name,
                domain=website_domain,
                industry=request.industry,
            )
        )

    async def _find_or_create_lead(self, company_id: UUID) -> Lead:
        existing_leads = await self._leads.list_by_company(company_id, limit=1)
        if existing_leads:
            return existing_leads[0]
        return await self._leads.create(
            Lead(company_id=company_id, source=LeadSource.OUTBOUND)
        )

    async def _find_or_create_contact(
        self, company_id: UUID, request: SalesWorkflowRequest
    ) -> Contact | None:
        # A Contact requires a first/last name, so we can only create one
        # when an actual recipient name is known — a role alone (e.g.
        # "Head of Operations") is not a person we can record.
        if not request.recipient_name:
            return None
        parts = request.recipient_name.strip().split(maxsplit=1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""
        existing = await self._contacts.find_by_company_and_name(
            company_id, first_name, last_name
        )
        if existing is not None:
            return existing
        return await self._contacts.create(
            Contact(
                company_id=company_id,
                first_name=first_name,
                last_name=last_name,
                email=request.recipient_email,
            )
        )

    async def _save_email_draft(
        self,
        company_id: UUID,
        lead_id: UUID,
        workflow_run_id: UUID,
        response: SalesWorkflowResponse,
    ) -> EmailDraft:
        return await self._email_drafts.create(
            EmailDraft(
                company_id=company_id,
                lead_id=lead_id,
                workflow_run_id=workflow_run_id,
                subject_lines=list(response.email_draft.subject_lines),
                email_body=response.email_draft.email_body,
                status="draft",
            )
        )

    async def _record_interaction(
        self,
        lead_id: UUID,
        email_draft_id: UUID,
        workflow_run_id: UUID,
        response: SalesWorkflowResponse,
    ) -> Interaction:
        summary = (
            f"Sales workflow run {workflow_run_id} produced an email draft "
            f"(id {email_draft_id}) for {response.company_name}. Draft only "
            "— no email was sent and no contact was made."
        )
        return await self._interactions.create(
            Interaction(
                lead_id=lead_id,
                type=InteractionType.WORKFLOW_RUN,
                status="draft_created",
                notes=summary,
            )
        )

    async def _record_blocked_interaction(
        self,
        lead_id: UUID,
        workflow_run_id: UUID,
        response: SalesWorkflowResponse,
    ) -> Interaction:
        summary = (
            f"Sales workflow run {workflow_run_id} for {response.company_name} "
            "was blocked by an active do-not-contact entry. No email draft "
            "was created and no contact was made."
        )
        return await self._interactions.create(
            Interaction(
                lead_id=lead_id,
                type=InteractionType.WORKFLOW_RUN,
                status="do_not_contact_blocked",
                notes=summary,
            )
        )
