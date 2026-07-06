from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.company_intelligence.service import CompanyIntelligenceService
from backend.agents.email_draft.service import EmailDraftService
from backend.agents.lead_research.service import LeadResearchService
from backend.agents.personalization.service import PersonalizationService
from backend.agents.reply_analysis.service import ReplyAnalysisService
from backend.application.auth.auth_service import AuthService
from backend.application.crm.workflow_sync_service import WorkflowCrmSyncService
from backend.application.reviews.review_service import ReviewService
from backend.application.settings.llm_settings_service import LLMSettingsService
from backend.application.use_cases.create_company import CreateCompanyUseCase
from backend.application.use_cases.create_lead import CreateLeadUseCase
from backend.application.use_cases.update_lead_status import UpdateLeadStatusUseCase
from backend.application.workflows.history_service import WorkflowHistoryService
from backend.application.workflows.sales_workflow import SalesWorkflowService
from backend.domain.repositories.company_repository import CompanyRepository
from backend.domain.repositories.contact_repository import ContactRepository
from backend.domain.repositories.email_draft_repository import EmailDraftRepository
from backend.domain.repositories.interaction_repository import InteractionRepository
from backend.domain.repositories.lead_repository import LeadRepository
from backend.domain.repositories.review_event_repository import ReviewEventRepository
from backend.domain.repositories.user_repository import UserRepository
from backend.domain.repositories.workflow_run_repository import WorkflowRunRepository
from backend.infrastructure.database.session import get_session
from backend.infrastructure.llm.base import LLMProvider
from backend.infrastructure.llm.factory import create_llm_provider
from backend.infrastructure.repositories.company import SQLAlchemyCompanyRepository
from backend.infrastructure.repositories.contact import SQLAlchemyContactRepository
from backend.infrastructure.repositories.email_draft import (
    SQLAlchemyEmailDraftRepository,
)
from backend.infrastructure.repositories.interaction import (
    SQLAlchemyInteractionRepository,
)
from backend.infrastructure.repositories.lead import SQLAlchemyLeadRepository
from backend.infrastructure.repositories.review_event import (
    SQLAlchemyReviewEventRepository,
)
from backend.infrastructure.repositories.user import SQLAlchemyUserRepository
from backend.infrastructure.repositories.workflow_run import (
    SQLAlchemyWorkflowRunRepository,
)
from backend.shared.config import get_settings

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# -- LLM provider ---------------------------------------------------------

def get_llm_provider() -> LLMProvider:
    return create_llm_provider()


LLMProviderDep = Annotated[LLMProvider, Depends(get_llm_provider)]


# -- agents ---------------------------------------------------------------

def get_lead_research_service(llm: LLMProviderDep) -> LeadResearchService:
    return LeadResearchService(llm)


LeadResearchServiceDep = Annotated[
    LeadResearchService, Depends(get_lead_research_service)
]


def get_company_intelligence_service(
    llm: LLMProviderDep,
) -> CompanyIntelligenceService:
    return CompanyIntelligenceService(llm)


CompanyIntelligenceServiceDep = Annotated[
    CompanyIntelligenceService, Depends(get_company_intelligence_service)
]


def get_personalization_service(llm: LLMProviderDep) -> PersonalizationService:
    return PersonalizationService(llm)


PersonalizationServiceDep = Annotated[
    PersonalizationService, Depends(get_personalization_service)
]


def get_email_draft_service(llm: LLMProviderDep) -> EmailDraftService:
    return EmailDraftService(llm)


EmailDraftServiceDep = Annotated[EmailDraftService, Depends(get_email_draft_service)]


def get_reply_analysis_service(llm: LLMProviderDep) -> ReplyAnalysisService:
    return ReplyAnalysisService(llm)


ReplyAnalysisServiceDep = Annotated[
    ReplyAnalysisService, Depends(get_reply_analysis_service)
]


# -- repositories (domain ports -> infrastructure adapters) ---------------

def get_company_repository(session: SessionDep) -> CompanyRepository:
    return SQLAlchemyCompanyRepository(session)


def get_lead_repository(session: SessionDep) -> LeadRepository:
    return SQLAlchemyLeadRepository(session)


def get_workflow_run_repository(session: SessionDep) -> WorkflowRunRepository:
    return SQLAlchemyWorkflowRunRepository(session)


def get_contact_repository(session: SessionDep) -> ContactRepository:
    return SQLAlchemyContactRepository(session)


def get_interaction_repository(session: SessionDep) -> InteractionRepository:
    return SQLAlchemyInteractionRepository(session)


def get_email_draft_repository(session: SessionDep) -> EmailDraftRepository:
    return SQLAlchemyEmailDraftRepository(session)


def get_review_event_repository(session: SessionDep) -> ReviewEventRepository:
    return SQLAlchemyReviewEventRepository(session)


def get_user_repository(session: SessionDep) -> UserRepository:
    return SQLAlchemyUserRepository(session)


CompanyRepositoryDep = Annotated[CompanyRepository, Depends(get_company_repository)]
LeadRepositoryDep = Annotated[LeadRepository, Depends(get_lead_repository)]
ContactRepositoryDep = Annotated[ContactRepository, Depends(get_contact_repository)]
InteractionRepositoryDep = Annotated[
    InteractionRepository, Depends(get_interaction_repository)
]
EmailDraftRepositoryDep = Annotated[
    EmailDraftRepository, Depends(get_email_draft_repository)
]
ReviewEventRepositoryDep = Annotated[
    ReviewEventRepository, Depends(get_review_event_repository)
]
UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]
WorkflowRunRepositoryDep = Annotated[
    WorkflowRunRepository, Depends(get_workflow_run_repository)
]


# -- workflows --------------------------------------------------------------

def get_workflow_history_service(
    workflow_runs: WorkflowRunRepositoryDep,
) -> WorkflowHistoryService:
    return WorkflowHistoryService(workflow_runs)


WorkflowHistoryServiceDep = Annotated[
    WorkflowHistoryService, Depends(get_workflow_history_service)
]


def get_workflow_crm_sync_service(
    companies: CompanyRepositoryDep,
    leads: LeadRepositoryDep,
    contacts: ContactRepositoryDep,
    interactions: InteractionRepositoryDep,
    email_drafts: EmailDraftRepositoryDep,
) -> WorkflowCrmSyncService:
    return WorkflowCrmSyncService(
        companies=companies,
        leads=leads,
        contacts=contacts,
        interactions=interactions,
        email_drafts=email_drafts,
    )


WorkflowCrmSyncServiceDep = Annotated[
    WorkflowCrmSyncService, Depends(get_workflow_crm_sync_service)
]


def get_sales_workflow_service(
    lead_research: LeadResearchServiceDep,
    company_intelligence: CompanyIntelligenceServiceDep,
    personalization: PersonalizationServiceDep,
    email_draft: EmailDraftServiceDep,
    history: WorkflowHistoryServiceDep,
    crm_sync: WorkflowCrmSyncServiceDep,
) -> SalesWorkflowService:
    return SalesWorkflowService(
        lead_research=lead_research,
        company_intelligence=company_intelligence,
        personalization=personalization,
        email_draft=email_draft,
        history=history,
        crm_sync=crm_sync,
    )


SalesWorkflowServiceDep = Annotated[
    SalesWorkflowService, Depends(get_sales_workflow_service)
]


def get_review_service(
    email_drafts: EmailDraftRepositoryDep,
    workflow_runs: WorkflowRunRepositoryDep,
    review_events: ReviewEventRepositoryDep,
) -> ReviewService:
    return ReviewService(
        email_drafts=email_drafts,
        workflow_runs=workflow_runs,
        review_events=review_events,
    )


ReviewServiceDep = Annotated[ReviewService, Depends(get_review_service)]


# -- auth -------------------------------------------------------------------

def get_auth_service(users: UserRepositoryDep) -> AuthService:
    return AuthService(users)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


# -- use cases ------------------------------------------------------------

def get_create_company_use_case(
    companies: CompanyRepositoryDep,
) -> CreateCompanyUseCase:
    return CreateCompanyUseCase(companies)


def get_create_lead_use_case(
    leads: LeadRepositoryDep,
    companies: CompanyRepositoryDep,
) -> CreateLeadUseCase:
    return CreateLeadUseCase(leads, companies)


def get_update_lead_status_use_case(
    leads: LeadRepositoryDep,
) -> UpdateLeadStatusUseCase:
    return UpdateLeadStatusUseCase(leads)


CreateCompanyUseCaseDep = Annotated[
    CreateCompanyUseCase, Depends(get_create_company_use_case)
]
CreateLeadUseCaseDep = Annotated[CreateLeadUseCase, Depends(get_create_lead_use_case)]
UpdateLeadStatusUseCaseDep = Annotated[
    UpdateLeadStatusUseCase, Depends(get_update_lead_status_use_case)
]


# -- settings ---------------------------------------------------------------

def get_llm_settings_service() -> LLMSettingsService:
    return LLMSettingsService(get_settings())


LLMSettingsServiceDep = Annotated[
    LLMSettingsService, Depends(get_llm_settings_service)
]
