from backend.agents.base import BaseAgent
from backend.agents.prompts import DEMO_AGENT_SYSTEM_PROMPT, build_demo_prompt
from backend.agents.schemas import AgentInput, AgentOutput


class DemoAgentInput(AgentInput):
    """Input for the demo agent."""

    message: str


class DemoAgentOutput(AgentOutput):
    """Output for the demo agent."""

    reply: str
    char_count: int


class DemoAgent(BaseAgent[DemoAgentInput, DemoAgentOutput]):
    """Minimal agent that echoes a reply. Used only to verify the framework.

    Contains no sales, research, or scoring logic.
    """

    name = "demo"
    input_model = DemoAgentInput
    output_model = DemoAgentOutput
    system_prompt = DEMO_AGENT_SYSTEM_PROMPT

    def build_prompt(self, agent_input: DemoAgentInput) -> str:
        return build_demo_prompt(agent_input.message)
