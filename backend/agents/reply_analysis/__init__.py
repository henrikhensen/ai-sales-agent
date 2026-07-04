"""Reply Analysis Agent package.

Classifies and analyses a lead's reply to a prior outreach and recommends a
next action for a human. Performs analysis only — no automatic reply, no
meeting booking, no contact of any kind, and no fabrication of facts. Human
approval remains mandatory before any action is taken.
"""

from backend.agents.reply_analysis.exceptions import (
    InvalidReplyAnalysisOutputError,
    ReplyAnalysisError,
)
from backend.agents.reply_analysis.prompt import (
    REPLY_ANALYSIS_SYSTEM_PROMPT,
    build_reply_analysis_prompt,
)
from backend.agents.reply_analysis.schemas import (
    ReplyAnalysisRequest,
    ReplyAnalysisResponse,
)
from backend.agents.reply_analysis.service import (
    ReplyAnalysisAgent,
    ReplyAnalysisService,
)

__all__ = [
    "REPLY_ANALYSIS_SYSTEM_PROMPT",
    "InvalidReplyAnalysisOutputError",
    "ReplyAnalysisAgent",
    "ReplyAnalysisError",
    "ReplyAnalysisRequest",
    "ReplyAnalysisResponse",
    "ReplyAnalysisService",
    "build_reply_analysis_prompt",
]
