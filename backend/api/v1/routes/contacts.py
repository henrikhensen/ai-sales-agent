from fastapi import APIRouter, Query

from backend.api.v1.dependencies import ContactRepositoryDep
from backend.api.v1.schemas.contact import ContactResponse

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("", response_model=list[ContactResponse])
async def list_contacts(
    repository: ContactRepositoryDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[ContactResponse]:
    """List contacts, newest first. Read-only."""
    contacts = await repository.list(limit=limit, offset=offset)
    return [ContactResponse.model_validate(contact) for contact in contacts]
