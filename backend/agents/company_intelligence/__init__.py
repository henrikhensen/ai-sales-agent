"""Company Intelligence Agent package.

Produces a deeper, strategic analysis of a company from user-provided
information. Performs analysis only — no outreach, no external data fetching,
no fabrication of facts.
"""

from backend.agents.company_intelligence.exceptions import (
    CompanyIntelligenceError,
    InvalidCompanyIntelligenceOutputError,
)
from backend.agents.company_intelligence.prompt import (
    COMPANY_INTELLIGENCE_SYSTEM_PROMPT,
    build_company_intelligence_prompt,
)
from backend.agents.company_intelligence.schemas import (
    CompanyIntelligenceRequest,
    CompanyIntelligenceResponse,
)
from backend.agents.company_intelligence.service import (
    CompanyIntelligenceAgent,
    CompanyIntelligenceService,
)

__all__ = [
    "COMPANY_INTELLIGENCE_SYSTEM_PROMPT",
    "CompanyIntelligenceAgent",
    "CompanyIntelligenceError",
    "CompanyIntelligenceRequest",
    "CompanyIntelligenceResponse",
    "CompanyIntelligenceService",
    "InvalidCompanyIntelligenceOutputError",
    "build_company_intelligence_prompt",
]
