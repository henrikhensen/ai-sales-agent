from fastapi import APIRouter, HTTPException, status

from backend.agents import default_registry
from backend.agents.company_intelligence.exceptions import (
    InvalidCompanyIntelligenceOutputError,
)
from backend.agents.company_intelligence.schemas import (
    CompanyIntelligenceRequest,
    CompanyIntelligenceResponse,
)
from backend.agents.demo_agent import DemoAgent, DemoAgentInput
from backend.agents.email_draft.exceptions import InvalidEmailDraftOutputError
from backend.agents.email_draft.schemas import EmailDraftRequest, EmailDraftResponse
from backend.agents.lead_research.exceptions import InvalidLeadResearchOutputError
from backend.agents.lead_research.schemas import (
    LeadResearchRequest,
    LeadResearchResponse,
)
from backend.agents.personalization.exceptions import (
    InvalidPersonalizationOutputError,
)
from backend.agents.personalization.schemas import (
    PersonalizationRequest,
    PersonalizationResponse,
)
from backend.api.v1.dependencies import (
    CompanyIntelligenceServiceDep,
    EmailDraftServiceDep,
    LeadResearchServiceDep,
    LLMProviderDep,
    PersonalizationServiceDep,
)
from backend.api.v1.schemas.agent import (
    DemoAgentRequest,
    DemoAgentResponse,
    DemoAgentResult,
)

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/demo", response_model=DemoAgentResponse)
async def run_demo_agent(
    payload: DemoAgentRequest,
    llm: LLMProviderDep,
) -> DemoAgentResponse:
    """Run the demo agent against the configured LLM provider.

    With the default ``mock`` provider this executes fully offline and is used
    to verify the agent framework end-to-end.
    """
    agent = default_registry.create(DemoAgent.name, llm)
    result = await agent.run(DemoAgentInput(message=payload.message))
    return DemoAgentResponse(
        agent=result.agent,
        provider=result.provider,
        output=DemoAgentResult(**result.output.model_dump()),
    )


@router.post("/lead-research", response_model=LeadResearchResponse)
async def run_lead_research_agent(
    payload: LeadResearchRequest,
    service: LeadResearchServiceDep,
) -> LeadResearchResponse:
    """Analyse a company from the supplied information and return a lead profile.

    Analysis only: this endpoint never contacts the company, sends messages, or
    fabricates facts. Any outreach remains a separate, human-approved step.
    """
    try:
        return await service.research(payload)
    except InvalidLeadResearchOutputError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Lead research failed: {exc.reason}",
        ) from exc


@router.post("/company-intelligence", response_model=CompanyIntelligenceResponse)
async def run_company_intelligence_agent(
    payload: CompanyIntelligenceRequest,
    service: CompanyIntelligenceServiceDep,
) -> CompanyIntelligenceResponse:
    """Produce a strategic company profile from the supplied information.

    Analysis only: this endpoint never contacts the company, sends messages, or
    fabricates facts. Any outreach remains a separate, human-approved step.
    """
    try:
        return await service.analyze(payload)
    except InvalidCompanyIntelligenceOutputError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Company intelligence failed: {exc.reason}",
        ) from exc


@router.post("/personalization", response_model=PersonalizationResponse)
async def run_personalization_agent(
    payload: PersonalizationRequest,
    service: PersonalizationServiceDep,
) -> PersonalizationResponse:
    """Produce a personalization strategy from the supplied sales context.

    Strategy only: this endpoint never contacts the company, drafts or sends
    messages, or fabricates facts. Any outreach remains a separate,
    human-approved step.
    """
    try:
        return await service.personalize(payload)
    except InvalidPersonalizationOutputError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Personalization failed: {exc.reason}",
        ) from exc


@router.post("/email-draft", response_model=EmailDraftResponse)
async def run_email_draft_agent(
    payload: EmailDraftRequest,
    service: EmailDraftServiceDep,
) -> EmailDraftResponse:
    """Produce a human-reviewable email draft from the supplied context.

    Draft only: this endpoint never sends an email, contacts the company, or
    fabricates facts. Sending remains a separate, human-approved step.
    """
    try:
        return await service.draft(payload)
    except InvalidEmailDraftOutputError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Email draft failed: {exc.reason}",
        ) from exc
