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
from backend.agents.lead_research.exceptions import InvalidLeadResearchOutputError
from backend.agents.lead_research.schemas import (
    LeadResearchRequest,
    LeadResearchResponse,
)
from backend.api.v1.dependencies import (
    CompanyIntelligenceServiceDep,
    LeadResearchServiceDep,
    LLMProviderDep,
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
