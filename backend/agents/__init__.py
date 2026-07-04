"""AI agent framework.

Importing this package registers the built-in agents into ``default_registry``.
"""

from backend.agents.company_intelligence.service import CompanyIntelligenceAgent
from backend.agents.demo_agent import DemoAgent
from backend.agents.email_draft.service import EmailDraftAgent
from backend.agents.lead_research.service import LeadResearchAgent
from backend.agents.personalization.service import PersonalizationAgent
from backend.agents.registry import AgentRegistry, default_registry
from backend.agents.reply_analysis.service import ReplyAnalysisAgent

default_registry.register(DemoAgent)
default_registry.register(LeadResearchAgent)
default_registry.register(CompanyIntelligenceAgent)
default_registry.register(PersonalizationAgent)
default_registry.register(EmailDraftAgent)
default_registry.register(ReplyAnalysisAgent)

__all__ = [
    "AgentRegistry",
    "CompanyIntelligenceAgent",
    "DemoAgent",
    "EmailDraftAgent",
    "LeadResearchAgent",
    "PersonalizationAgent",
    "ReplyAnalysisAgent",
    "default_registry",
]
