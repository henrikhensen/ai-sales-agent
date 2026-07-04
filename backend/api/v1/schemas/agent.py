from pydantic import BaseModel, Field


class DemoAgentRequest(BaseModel):
    """Request body for running the demo agent."""

    message: str = Field(min_length=1, max_length=2000)


class DemoAgentResult(BaseModel):
    """The demo agent's produced output."""

    reply: str
    char_count: int


class DemoAgentResponse(BaseModel):
    """Response body for a demo agent run."""

    agent: str
    provider: str
    output: DemoAgentResult
