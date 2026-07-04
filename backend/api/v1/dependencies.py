from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.company_intelligence.service import CompanyIntelligenceService
from backend.agents.email_draft.service import EmailDraftService
from backend.agents.lead_research.service import LeadResearchService
from backend.agents.personalization.service import PersonalizationService
from backend.application.use_cases.create_company import CreateCompanyUseCase
from backend.application.use_cases.create_lead import CreateLeadUseCase
from backend.application.use_cases.update_lead_status import UpdateLeadStatusUseCase
from backend.domain.repositories.company_repository import CompanyRepository
from backend.domain.repositories.lead_repository import LeadRepository
from backend.infrastructure.database.session import get_session
from backend.infrastructure.llm.base import LLMProvider
from backend.infrastructure.llm.factory import create_llm_provider
from backend.infrastructure.repositories.company import SQLAlchemyCompanyRepository
from backend.infrastructure.repositories.lead import SQLAlchemyLeadRepository

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


# -- repositories (domain ports -> infrastructure adapters) ---------------

def get_company_repository(session: SessionDep) -> CompanyRepository:
    return SQLAlchemyCompanyRepository(session)


def get_lead_repository(session: SessionDep) -> LeadRepository:
    return SQLAlchemyLeadRepository(session)


CompanyRepositoryDep = Annotated[CompanyRepository, Depends(get_company_repository)]
LeadRepositoryDep = Annotated[LeadRepository, Depends(get_lead_repository)]


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
