from fastapi import APIRouter, Query

from backend.api.v1.dependencies import InteractionRepositoryDep
from backend.api.v1.schemas.interaction import InteractionResponse

router = APIRouter(prefix="/interactions", tags=["interactions"])


@router.get("", response_model=list[InteractionResponse])
async def list_interactions(
    repository: InteractionRepositoryDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[InteractionResponse]:
    """List interactions/activities, newest first. Read-only."""
    interactions = await repository.list(limit=limit, offset=offset)
    return [InteractionResponse.model_validate(interaction) for interaction in interactions]
