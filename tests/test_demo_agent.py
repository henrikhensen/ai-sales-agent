from backend.agents.demo_agent import DemoAgent, DemoAgentInput, DemoAgentOutput
from backend.infrastructure.llm.mock_provider import MockLLMProvider


async def test_demo_agent_runs_with_mock_provider():
    agent = DemoAgent(MockLLMProvider())

    result = await agent.run(DemoAgentInput(message="hello"))

    assert result.agent == "demo"
    assert result.provider == "mock"
    assert isinstance(result.output, DemoAgentOutput)

    expected_prompt = "Message: hello"
    assert result.output.reply == f"[mock] {expected_prompt}"
    assert result.output.char_count == len(expected_prompt)


async def test_demo_agent_output_is_validated_type():
    agent = DemoAgent(MockLLMProvider())
    result = await agent.run(DemoAgentInput(message="anything"))
    # raw dict is preserved alongside the validated model
    assert set(result.raw) == {"reply", "char_count"}
