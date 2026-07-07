"""Website research: fetch a single public URL and extract readable text.

Analysis only — this router never sends an email, never contacts the
company, never submits a form on the target site, and never triggers an
LLM call. It only ever fetches the exact URL the caller supplies: no
automatic mass research, no LinkedIn scraping, no login bypass (the
fetcher only follows public, unauthenticated redirects and refuses
localhost/private/internal targets).
"""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.dependencies.auth import RequireSalesReviewerOrAdminDep
from backend.api.v1.dependencies import WebsiteResearchServiceDep
from backend.application.research.exceptions import (
    InvalidWebsiteURLError,
    WebsiteFetchFailedError,
)
from backend.application.research.schemas import (
    WebsiteResearchRequest,
    WebsiteResearchResponse,
)
from backend.shared.rate_limit import rate_limit

router = APIRouter(prefix="/research", tags=["research"])

_website_research_rate_limit = rate_limit(
    "website_research", "rate_limit_website_research_per_hour", 3600
)


@router.post(
    "/website",
    response_model=WebsiteResearchResponse,
    dependencies=[Depends(_website_research_rate_limit)],
)
async def research_website(
    payload: WebsiteResearchRequest,
    service: WebsiteResearchServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> WebsiteResearchResponse:
    """Fetch the supplied public URL and extract readable text from it.

    Requires an active admin, reviewer, or sales account. Analysis only:
    never sends an email, contacts the company, submits a form, or
    triggers an LLM call. Fetches exactly the URL supplied — never a list
    of URLs, and never a login-gated page such as LinkedIn. Rate-limited
    per user (``RATE_LIMIT_WEBSITE_RESEARCH_PER_HOUR``).
    """
    try:
        return await service.research(payload)
    except InvalidWebsiteURLError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except WebsiteFetchFailedError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
