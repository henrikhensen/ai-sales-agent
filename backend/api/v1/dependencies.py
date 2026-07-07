from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.company_intelligence.service import CompanyIntelligenceService
from backend.agents.email_draft.service import EmailDraftService
from backend.agents.lead_research.service import LeadResearchService
from backend.agents.personalization.service import PersonalizationService
from backend.agents.reply_analysis.service import ReplyAnalysisService
from backend.application.audit.audit_log_service import AuditLogService
from backend.application.auth.auth_service import AuthService
from backend.application.compliance.compliance_status_service import (
    ComplianceStatusService,
)
from backend.application.compliance.do_not_contact_service import (
    DoNotContactService,
)
from backend.application.crm.pipeline_service import PipelineService
from backend.application.crm.workflow_sync_service import WorkflowCrmSyncService
from backend.application.integrations.email_draft_integration_service import (
    EmailDraftIntegrationService,
)
from backend.application.integrations.reply_tracking_service import (
    ReplyTrackingService,
)
from backend.application.lead_qualification.lead_qualification_service import (
    LeadQualificationService,
)
from backend.application.lead_sourcing.lead_sourcing_service import (
    LeadSourcingService,
)
from backend.application.research.website_research_service import (
    WebsiteResearchService,
)
from backend.application.reviews.review_service import ReviewService
from backend.application.sales_strategy.icp_service import ICPService
from backend.application.sales_strategy.offer_service import OfferService
from backend.application.settings.llm_settings_service import LLMSettingsService
from backend.application.settings.system_status_service import SystemStatusService
from backend.application.use_cases.create_company import CreateCompanyUseCase
from backend.application.use_cases.create_lead import CreateLeadUseCase
from backend.application.use_cases.update_lead_status import UpdateLeadStatusUseCase
from backend.application.workflows.history_service import WorkflowHistoryService
from backend.application.workflows.sales_workflow import SalesWorkflowService
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
from backend.domain.repositories.offer_profile_repository import (
    OfferProfileRepository,
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
from backend.infrastructure.database.session import get_session
from backend.infrastructure.llm.base import LLMProvider
from backend.infrastructure.llm.factory import create_llm_provider
from backend.infrastructure.repositories.audit_log import SQLAlchemyAuditLogRepository
from backend.infrastructure.repositories.company import SQLAlchemyCompanyRepository
from backend.infrastructure.repositories.contact import SQLAlchemyContactRepository
from backend.infrastructure.repositories.do_not_contact import (
    SQLAlchemyDoNotContactRepository,
)
from backend.infrastructure.repositories.email_draft import (
    SQLAlchemyEmailDraftRepository,
)
from backend.infrastructure.repositories.email_provider_connection import (
    SQLAlchemyEmailProviderConnectionRepository,
)
from backend.infrastructure.repositories.external_email_draft import (
    SQLAlchemyExternalEmailDraftRepository,
)
from backend.infrastructure.repositories.icp_profile import (
    SQLAlchemyICPProfileRepository,
)
from backend.infrastructure.repositories.interaction import (
    SQLAlchemyInteractionRepository,
)
from backend.infrastructure.repositories.lead import SQLAlchemyLeadRepository
from backend.infrastructure.repositories.lead_candidate import (
    SQLAlchemyLeadCandidateRepository,
)
from backend.infrastructure.repositories.lead_sourcing_campaign import (
    SQLAlchemyLeadSourcingCampaignRepository,
)
from backend.infrastructure.repositories.lead_sourcing_run import (
    SQLAlchemyLeadSourcingRunRepository,
)
from backend.infrastructure.repositories.offer_profile import (
    SQLAlchemyOfferProfileRepository,
)
from backend.infrastructure.repositories.qualification_result import (
    SQLAlchemyQualificationResultRepository,
)
from backend.infrastructure.repositories.qualification_run import (
    SQLAlchemyQualificationRunRepository,
)
from backend.infrastructure.repositories.reply import SQLAlchemyReplyRepository
from backend.infrastructure.repositories.review_event import (
    SQLAlchemyReviewEventRepository,
)
from backend.infrastructure.repositories.user import SQLAlchemyUserRepository
from backend.infrastructure.repositories.workflow_run import (
    SQLAlchemyWorkflowRunRepository,
)
from backend.infrastructure.web.fetcher import WebFetcher
from backend.shared.config import get_settings

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# -- LLM provider ---------------------------------------------------------

def get_llm_provider() -> LLMProvider:
    return create_llm_provider()


LLMProviderDep = Annotated[LLMProvider, Depends(get_llm_provider)]


# -- website research ---------------------------------------------------------
# Defined before "agents"/"workflows" below since SalesWorkflowService (in the
# "workflows" section) now depends on WebsiteResearchServiceDep.

def get_web_fetcher() -> WebFetcher:
    settings = get_settings()
    return WebFetcher(
        timeout_seconds=settings.website_fetch_timeout_seconds,
        max_bytes=settings.website_fetch_max_bytes,
        user_agent=settings.website_research_user_agent,
    )


WebFetcherDep = Annotated[WebFetcher, Depends(get_web_fetcher)]


def get_website_research_service(fetcher: WebFetcherDep) -> WebsiteResearchService:
    settings = get_settings()
    return WebsiteResearchService(
        fetcher, max_pages_cap=settings.website_research_max_pages
    )


WebsiteResearchServiceDep = Annotated[
    WebsiteResearchService, Depends(get_website_research_service)
]


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

def get_audit_log_repository(session: SessionDep) -> AuditLogRepository:
    return SQLAlchemyAuditLogRepository(session)


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


def get_do_not_contact_repository(session: SessionDep) -> DoNotContactRepository:
    return SQLAlchemyDoNotContactRepository(session)


def get_external_email_draft_repository(
    session: SessionDep,
) -> ExternalEmailDraftRepository:
    return SQLAlchemyExternalEmailDraftRepository(session)


def get_email_provider_connection_repository(
    session: SessionDep,
) -> EmailProviderConnectionRepository:
    return SQLAlchemyEmailProviderConnectionRepository(session)


def get_reply_repository(session: SessionDep) -> ReplyRepository:
    return SQLAlchemyReplyRepository(session)


AuditLogRepositoryDep = Annotated[
    AuditLogRepository, Depends(get_audit_log_repository)
]
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
DoNotContactRepositoryDep = Annotated[
    DoNotContactRepository, Depends(get_do_not_contact_repository)
]
ExternalEmailDraftRepositoryDep = Annotated[
    ExternalEmailDraftRepository, Depends(get_external_email_draft_repository)
]
EmailProviderConnectionRepositoryDep = Annotated[
    EmailProviderConnectionRepository,
    Depends(get_email_provider_connection_repository),
]
ReplyRepositoryDep = Annotated[ReplyRepository, Depends(get_reply_repository)]


# -- compliance ---------------------------------------------------------------
# Defined before "workflows" below since SalesWorkflowService now depends on
# DoNotContactServiceDep, and before ReviewServiceDep for the same reason.

def get_do_not_contact_service(
    entries: DoNotContactRepositoryDep,
) -> DoNotContactService:
    return DoNotContactService(entries)


DoNotContactServiceDep = Annotated[
    DoNotContactService, Depends(get_do_not_contact_service)
]


def get_compliance_status_service() -> ComplianceStatusService:
    return ComplianceStatusService(get_settings())


ComplianceStatusServiceDep = Annotated[
    ComplianceStatusService, Depends(get_compliance_status_service)
]


# -- email draft integration (Gmail/Outlook) ---------------------------------

def get_email_draft_integration_service(
    connections: EmailProviderConnectionRepositoryDep,
    external_drafts: ExternalEmailDraftRepositoryDep,
    email_drafts: EmailDraftRepositoryDep,
    companies: CompanyRepositoryDep,
    workflow_runs: WorkflowRunRepositoryDep,
    contacts: ContactRepositoryDep,
    compliance: DoNotContactServiceDep,
) -> EmailDraftIntegrationService:
    return EmailDraftIntegrationService(
        connections=connections,
        external_drafts=external_drafts,
        email_drafts=email_drafts,
        companies=companies,
        workflow_runs=workflow_runs,
        contacts=contacts,
        compliance=compliance,
        settings=get_settings(),
    )


EmailDraftIntegrationServiceDep = Annotated[
    EmailDraftIntegrationService, Depends(get_email_draft_integration_service)
]


# -- reply tracking (Gmail/Outlook) -------------------------------------------

def get_reply_tracking_service(
    replies: ReplyRepositoryDep,
    connections: EmailProviderConnectionRepositoryDep,
    leads: LeadRepositoryDep,
    companies: CompanyRepositoryDep,
    contacts: ContactRepositoryDep,
    email_drafts: EmailDraftRepositoryDep,
    external_drafts: ExternalEmailDraftRepositoryDep,
    workflow_runs: WorkflowRunRepositoryDep,
    interactions: InteractionRepositoryDep,
    compliance: DoNotContactServiceDep,
    reply_analysis: ReplyAnalysisServiceDep,
) -> ReplyTrackingService:
    return ReplyTrackingService(
        replies=replies,
        connections=connections,
        leads=leads,
        companies=companies,
        contacts=contacts,
        email_drafts=email_drafts,
        external_drafts=external_drafts,
        workflow_runs=workflow_runs,
        interactions=interactions,
        compliance=compliance,
        reply_analysis=reply_analysis,
        settings=get_settings(),
    )


ReplyTrackingServiceDep = Annotated[
    ReplyTrackingService, Depends(get_reply_tracking_service)
]


# -- sales strategy (ICP / Offer profiles) -----------------------------------
# Defined before "workflows" below since SalesWorkflowService optionally
# depends on ICPServiceDep/OfferServiceDep.

def get_icp_profile_repository(session: SessionDep) -> ICPProfileRepository:
    return SQLAlchemyICPProfileRepository(session)


ICPProfileRepositoryDep = Annotated[
    ICPProfileRepository, Depends(get_icp_profile_repository)
]


def get_icp_service(icp_profiles: ICPProfileRepositoryDep) -> ICPService:
    return ICPService(icp_profiles)


ICPServiceDep = Annotated[ICPService, Depends(get_icp_service)]


def get_offer_profile_repository(session: SessionDep) -> OfferProfileRepository:
    return SQLAlchemyOfferProfileRepository(session)


OfferProfileRepositoryDep = Annotated[
    OfferProfileRepository, Depends(get_offer_profile_repository)
]


def get_offer_service(offer_profiles: OfferProfileRepositoryDep) -> OfferService:
    return OfferService(offer_profiles)


OfferServiceDep = Annotated[OfferService, Depends(get_offer_service)]


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


def get_pipeline_service(leads: LeadRepositoryDep) -> PipelineService:
    return PipelineService(leads)


PipelineServiceDep = Annotated[PipelineService, Depends(get_pipeline_service)]


def get_sales_workflow_service(
    lead_research: LeadResearchServiceDep,
    company_intelligence: CompanyIntelligenceServiceDep,
    personalization: PersonalizationServiceDep,
    email_draft: EmailDraftServiceDep,
    history: WorkflowHistoryServiceDep,
    crm_sync: WorkflowCrmSyncServiceDep,
    website_research: WebsiteResearchServiceDep,
    compliance: DoNotContactServiceDep,
    icp_service: ICPServiceDep,
    offer_service: OfferServiceDep,
) -> SalesWorkflowService:
    return SalesWorkflowService(
        lead_research=lead_research,
        company_intelligence=company_intelligence,
        personalization=personalization,
        email_draft=email_draft,
        history=history,
        crm_sync=crm_sync,
        website_research=website_research,
        compliance=compliance,
        icp_service=icp_service,
        offer_service=offer_service,
    )


SalesWorkflowServiceDep = Annotated[
    SalesWorkflowService, Depends(get_sales_workflow_service)
]


def get_review_service(
    email_drafts: EmailDraftRepositoryDep,
    workflow_runs: WorkflowRunRepositoryDep,
    review_events: ReviewEventRepositoryDep,
    companies: CompanyRepositoryDep,
    compliance: DoNotContactServiceDep,
) -> ReviewService:
    return ReviewService(
        email_drafts=email_drafts,
        workflow_runs=workflow_runs,
        review_events=review_events,
        companies=companies,
        compliance=compliance,
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


def get_system_status_service() -> SystemStatusService:
    return SystemStatusService(get_settings())


SystemStatusServiceDep = Annotated[
    SystemStatusService, Depends(get_system_status_service)
]


# -- audit ----------------------------------------------------------------

def get_audit_log_service(audit_logs: AuditLogRepositoryDep) -> AuditLogService:
    return AuditLogService(audit_logs, get_settings())


AuditLogServiceDep = Annotated[AuditLogService, Depends(get_audit_log_service)]


# -- lead sourcing ------------------------------------------------------------
# Defined last since LeadSourcingService depends on DoNotContactServiceDep,
# ICPServiceDep, WebsiteResearchServiceDep, and AuditLogServiceDep, all
# defined above.

def get_lead_sourcing_campaign_repository(
    session: SessionDep,
) -> LeadSourcingCampaignRepository:
    return SQLAlchemyLeadSourcingCampaignRepository(session)


LeadSourcingCampaignRepositoryDep = Annotated[
    LeadSourcingCampaignRepository, Depends(get_lead_sourcing_campaign_repository)
]


def get_lead_sourcing_run_repository(session: SessionDep) -> LeadSourcingRunRepository:
    return SQLAlchemyLeadSourcingRunRepository(session)


LeadSourcingRunRepositoryDep = Annotated[
    LeadSourcingRunRepository, Depends(get_lead_sourcing_run_repository)
]


def get_lead_candidate_repository(session: SessionDep) -> LeadCandidateRepository:
    return SQLAlchemyLeadCandidateRepository(session)


LeadCandidateRepositoryDep = Annotated[
    LeadCandidateRepository, Depends(get_lead_candidate_repository)
]


def get_lead_sourcing_service(
    campaigns: LeadSourcingCampaignRepositoryDep,
    runs: LeadSourcingRunRepositoryDep,
    candidates: LeadCandidateRepositoryDep,
    companies: CompanyRepositoryDep,
    leads: LeadRepositoryDep,
    compliance: DoNotContactServiceDep,
    icp_service: ICPServiceDep,
    website_research: WebsiteResearchServiceDep,
    audit: AuditLogServiceDep,
) -> LeadSourcingService:
    return LeadSourcingService(
        campaigns=campaigns,
        runs=runs,
        candidates=candidates,
        companies=companies,
        leads=leads,
        compliance=compliance,
        icp_service=icp_service,
        website_research=website_research,
        audit=audit,
        settings=get_settings(),
    )


LeadSourcingServiceDep = Annotated[
    LeadSourcingService, Depends(get_lead_sourcing_service)
]


# -- lead qualification ---------------------------------------------------------
# Defined last since LeadQualificationService depends on DoNotContactServiceDep,
# ICPServiceDep, OfferServiceDep, WebsiteResearchServiceDep, and
# AuditLogServiceDep, all defined above.

def get_qualification_run_repository(
    session: SessionDep,
) -> QualificationRunRepository:
    return SQLAlchemyQualificationRunRepository(session)


QualificationRunRepositoryDep = Annotated[
    QualificationRunRepository, Depends(get_qualification_run_repository)
]


def get_qualification_result_repository(
    session: SessionDep,
) -> QualificationResultRepository:
    return SQLAlchemyQualificationResultRepository(session)


QualificationResultRepositoryDep = Annotated[
    QualificationResultRepository, Depends(get_qualification_result_repository)
]


def get_lead_qualification_service(
    runs: QualificationRunRepositoryDep,
    results: QualificationResultRepositoryDep,
    lead_candidates: LeadCandidateRepositoryDep,
    companies: CompanyRepositoryDep,
    leads: LeadRepositoryDep,
    compliance: DoNotContactServiceDep,
    icp_service: ICPServiceDep,
    offer_service: OfferServiceDep,
    website_research: WebsiteResearchServiceDep,
    audit: AuditLogServiceDep,
) -> LeadQualificationService:
    return LeadQualificationService(
        runs=runs,
        results=results,
        lead_candidates=lead_candidates,
        companies=companies,
        leads=leads,
        compliance=compliance,
        icp_service=icp_service,
        offer_service=offer_service,
        website_research=website_research,
        audit=audit,
        settings=get_settings(),
    )


LeadQualificationServiceDep = Annotated[
    LeadQualificationService, Depends(get_lead_qualification_service)
]
