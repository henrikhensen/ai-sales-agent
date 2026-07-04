"""Lead Research Agent package.

Analyses a company from user-provided information and returns a structured
lead profile. Performs analysis only — no outreach, no external data fetching,
no fabrication of facts.
"""

from backend.agents.lead_research.exceptions import (
    InvalidLeadResearchOutputError,
    LeadResearchError,
)
from backend.agents.lead_research.prompt import (
    LEAD_RESEARCH_SYSTEM_PROMPT,
    build_lead_research_prompt,
)
from backend.agents.lead_research.schemas import (
    LeadResearchRequest,
    LeadResearchResponse,
)
from backend.agents.lead_research.service import (
    LeadResearchAgent,
    LeadResearchService,
)

__all__ = [
    "LEAD_RESEARCH_SYSTEM_PROMPT",
    "InvalidLeadResearchOutputError",
    "LeadResearchAgent",
    "LeadResearchError",
    "LeadResearchRequest",
    "LeadResearchResponse",
    "LeadResearchService",
    "build_lead_research_prompt",
]
