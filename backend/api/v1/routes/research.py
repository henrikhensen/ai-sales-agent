"""Website research: fetch a single public URL and extract readable text.

Analysis only — this router never sends an email, never contacts the
company, never submits a form on the target site, and never triggers an
LLM call. It only ever fetches the exact URL the caller supplies: no
automatic mass research, no LinkedIn scraping, no login bypass (the
fetcher only follows public, unauthenticated redirects and refuses
localhost/private/internal targets).
"""

from fastapi import APIRouter, HTTPException, status

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

router = APIRouter(prefix="/research", tags=["research"])


@router.post("/website", response_model=WebsiteResearchResponse)
async def research_website(
    payload: WebsiteResearchRequest,
    service: WebsiteResearchServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> WebsiteResearchResponse:
    """Fetch the supplied public URL and extract readable text from it.

    Requires an active admin, reviewer, or sales account. Analysis only:
    never sends an email, contacts the company, submits a form, or
    triggers an LLM call. Fetches exactly the URL supplied — never a list
    of URLs, and never a login-gated page such as LinkedIn.
    """
    try:
        return await service.research(payload)
    except InvalidWebsiteURLError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except WebsiteFetchFailedError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
