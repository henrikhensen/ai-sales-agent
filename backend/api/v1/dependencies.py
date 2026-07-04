from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.use_cases.create_company import CreateCompanyUseCase
from backend.application.use_cases.create_lead import CreateLeadUseCase
from backend.application.use_cases.update_lead_status import UpdateLeadStatusUseCase
from backend.domain.repositories.company_repository import CompanyRepository
from backend.domain.repositories.lead_repository import LeadRepository
from backend.infrastructure.database.session import get_session
from backend.infrastructure.repositories.company import SQLAlchemyCompanyRepository
from backend.infrastructure.repositories.lead import SQLAlchemyLeadRepository

SessionDep = Annotated[AsyncSession, Depends(get_session)]


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
