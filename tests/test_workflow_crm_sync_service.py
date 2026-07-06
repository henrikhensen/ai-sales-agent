import uuid

from backend.application.crm.workflow_sync_service import WorkflowCrmLinks
from backend.application.workflows.schemas import SalesWorkflowRequest, SalesWorkflowResponse
from backend.domain.enums import InteractionType, PipelineStatus
from tests.conftest import (
    FakeCompanyRepository,
    FakeContactRepository,
    FakeEmailDraftRepository,
    FakeInteractionRepository,
    FakeLeadRepository,
)


def _build_service():
    from backend.application.crm.workflow_sync_service import WorkflowCrmSyncService

    companies = FakeCompanyRepository()
    leads = FakeLeadRepository()
    contacts = FakeContactRepository()
    interactions = FakeInteractionRepository()
    email_drafts = FakeEmailDraftRepository()
    service = WorkflowCrmSyncService(
        companies=companies,
        leads=leads,
        contacts=contacts,
        interactions=interactions,
        email_drafts=email_drafts,
    )
    return service, companies, leads, contacts, interactions, email_drafts


def _sample_request(**overrides) -> SalesWorkflowRequest:
    defaults = dict(
        company_name="Acme GmbH",
        website_url="https://acme.example.com",
        product_or_service_offered="Freight API",
    )
    defaults.update(overrides)
    return SalesWorkflowRequest(**defaults)


def _sample_response(**overrides) -> SalesWorkflowResponse:
    defaults = dict(
        workflow_id="placeholder",
        status="completed",
        company_name="Acme GmbH",
        lead_research={
            "company_name": "Acme GmbH",
            "short_summary": "A logistics company.",
            "confidence_score": 0.6,
        },
        company_intelligence={
            "company_name": "Acme GmbH",
            "business_summary": "A logistics company.",
            "positioning_summary": "Efficiency-focused carrier.",
            "confidence_score": 0.6,
        },
        personalization={
            "company_name": "Acme GmbH",
            "personalization_summary": "Focus on efficiency gains.",
            "confidence_score": 0.6,
        },
        email_draft={
            "company_name": "Acme GmbH",
            "subject_lines": ["Quick question", "Freight visibility", "Worth a look?"],
            "email_body": "Dear team, ...",
            "confidence_score": 0.6,
        },
        confidence_score=0.6,
    )
    defaults.update(overrides)
    return SalesWorkflowResponse(**defaults)


async def test_sync_creates_company_lead_email_draft_and_interaction():
    service, companies, leads, contacts, interactions, email_drafts = _build_service()
    request = _sample_request()
    response = _sample_response()
    workflow_run_id = uuid.uuid4()

    links = await service.sync(request, response, workflow_run_id)

    assert isinstance(links, WorkflowCrmLinks)
    assert links.contact_id is None

    company = await companies.get(links.company_id)
    assert company.name == "Acme GmbH"
    assert company.domain == "acme.example.com"

    lead = await leads.get(links.lead_id)
    assert lead.company_id == links.company_id
    assert lead.pipeline_status == PipelineStatus.DRAFT_CREATED
    assert lead.pipeline_updated_at is not None

    draft = await email_drafts.get(links.email_draft_id)
    assert draft.company_id == links.company_id
    assert draft.lead_id == links.lead_id
    assert draft.workflow_run_id == workflow_run_id
    assert draft.status == "draft"
    assert draft.subject_lines == ["Quick question", "Freight visibility", "Worth a look?"]

    all_interactions = await interactions.list_by_lead(links.lead_id)
    assert len(all_interactions) == 1
    interaction = all_interactions[0]
    assert interaction.type == InteractionType.WORKFLOW_RUN
    assert interaction.status == "draft_created"
    assert "no email was sent" in interaction.notes.lower()

    assert len(await contacts.list()) == 0


async def test_sync_reuses_existing_company_and_lead():
    service, companies, leads, _contacts, _interactions, _email_drafts = _build_service()
    request = _sample_request()
    response = _sample_response()

    first_links = await service.sync(request, response, uuid.uuid4())
    second_links = await service.sync(request, response, uuid.uuid4())

    assert first_links.company_id == second_links.company_id
    assert first_links.lead_id == second_links.lead_id
    assert len(await companies.list()) == 1
    assert len(await leads.list()) == 1
    # Each sync still produces its own email draft.
    assert first_links.email_draft_id != second_links.email_draft_id


async def test_sync_creates_contact_when_recipient_name_given():
    service, _companies, _leads, contacts, _interactions, _email_drafts = _build_service()
    request = _sample_request(recipient_name="Jane Doe")
    response = _sample_response()

    links = await service.sync(request, response, uuid.uuid4())

    assert links.contact_id is not None
    contact = await contacts.get(links.contact_id)
    assert contact.first_name == "Jane"
    assert contact.last_name == "Doe"
    assert contact.company_id == links.company_id


async def test_sync_reuses_existing_contact_by_name():
    service, _companies, _leads, contacts, _interactions, _email_drafts = _build_service()
    request = _sample_request(recipient_name="Jane Doe")
    response = _sample_response()

    first_links = await service.sync(request, response, uuid.uuid4())
    second_links = await service.sync(request, response, uuid.uuid4())

    assert first_links.contact_id == second_links.contact_id
    assert len(await contacts.list()) == 1


async def test_sync_skips_contact_without_recipient_name():
    service, _companies, _leads, contacts, _interactions, _email_drafts = _build_service()
    request = _sample_request()
    response = _sample_response()

    links = await service.sync(request, response, uuid.uuid4())

    assert links.contact_id is None
    assert len(await contacts.list()) == 0
