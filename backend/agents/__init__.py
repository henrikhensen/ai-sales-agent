"""AI agent framework.

Importing this package registers the built-in agents into ``default_registry``.
"""

from backend.agents.company_intelligence.service import CompanyIntelligenceAgent
from backend.agents.demo_agent import DemoAgent
from backend.agents.lead_research.service import LeadResearchAgent
from backend.agents.registry import AgentRegistry, default_registry

default_registry.register(DemoAgent)
default_registry.register(LeadResearchAgent)
default_registry.register(CompanyIntelligenceAgent)

__all__ = [
    "AgentRegistry",
    "CompanyIntelligenceAgent",
    "DemoAgent",
    "LeadResearchAgent",
    "default_registry",
]
