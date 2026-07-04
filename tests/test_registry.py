import pytest

from backend.agents.demo_agent import DemoAgent
from backend.agents.exceptions import (
    AgentAlreadyRegisteredError,
    AgentNotFoundError,
)
from backend.agents.registry import AgentRegistry, default_registry
from backend.infrastructure.llm.mock_provider import MockLLMProvider


def test_register_and_create():
    registry = AgentRegistry()
    registry.register(DemoAgent)

    assert registry.is_registered("demo")
    assert registry.names() == ["demo"]

    agent = registry.create("demo", MockLLMProvider())
    assert isinstance(agent, DemoAgent)


def test_create_unknown_agent_raises():
    registry = AgentRegistry()
    with pytest.raises(AgentNotFoundError):
        registry.create("does-not-exist", MockLLMProvider())


def test_duplicate_registration_raises():
    registry = AgentRegistry()
    registry.register(DemoAgent)
    with pytest.raises(AgentAlreadyRegisteredError):
        registry.register(DemoAgent)


def test_default_registry_has_demo_agent():
    assert default_registry.is_registered("demo")
