"""Personalization Engine package.

Turns company, lead and analysis context into a structured personalization
strategy for a human seller. Performs strategy work only — no outreach, no
external data fetching, no fabrication of facts, and no ready-to-send message.
"""

from backend.agents.personalization.exceptions import (
    InvalidPersonalizationOutputError,
    PersonalizationError,
)
from backend.agents.personalization.prompt import (
    PERSONALIZATION_SYSTEM_PROMPT,
    build_personalization_prompt,
)
from backend.agents.personalization.schemas import (
    PersonalizationRequest,
    PersonalizationResponse,
)
from backend.agents.personalization.service import (
    PersonalizationAgent,
    PersonalizationService,
)

__all__ = [
    "PERSONALIZATION_SYSTEM_PROMPT",
    "InvalidPersonalizationOutputError",
    "PersonalizationAgent",
    "PersonalizationError",
    "PersonalizationRequest",
    "PersonalizationResponse",
    "PersonalizationService",
    "build_personalization_prompt",
]
