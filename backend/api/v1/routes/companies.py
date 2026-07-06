from fastapi import APIRouter, Query, status

from backend.api.dependencies.auth import (
    RequireSalesOrAdminDep,
    RequireSalesReviewerOrAdminDep,
)
from backend.api.v1.dependencies import CompanyRepositoryDep, CreateCompanyUseCaseDep
from backend.api.v1.schemas.company import CompanyCreate, CompanyResponse
from backend.application.use_cases.create_company import CreateCompanyCommand

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    payload: CompanyCreate,
    use_case: CreateCompanyUseCaseDep,
    _current_user: RequireSalesOrAdminDep,
) -> CompanyResponse:
    """Create a new company. Requires an active sales or admin account —
    reviewer accounts may read CRM data but not write it.
    """
    command = CreateCompanyCommand(
        name=payload.name,
        domain=payload.domain,
        industry=payload.industry,
    )
    company = await use_case.execute(command)
    return CompanyResponse.model_validate(company)


@router.get("", response_model=list[CompanyResponse])
async def list_companies(
    repository: CompanyRepositoryDep,
    _current_user: RequireSalesReviewerOrAdminDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[CompanyResponse]:
    """List companies, newest first. Read-only, any active admin, sales, or
    reviewer account.
    """
    companies = await repository.list(limit=limit, offset=offset)
    return [CompanyResponse.model_validate(company) for company in companies]
