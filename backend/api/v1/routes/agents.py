from fastapi import APIRouter

from backend.agents import default_registry
from backend.agents.demo_agent import DemoAgent, DemoAgentInput
from backend.api.v1.dependencies import LLMProviderDep
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
