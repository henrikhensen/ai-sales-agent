from fastapi import APIRouter, Query

from backend.api.dependencies.auth import RequireAdminUserDep
from backend.api.v1.dependencies import UserRepositoryDep
from backend.api.v1.schemas.auth import UserListResponse, UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=UserListResponse)
async def list_users(
    repository: UserRepositoryDep,
    _current_user: RequireAdminUserDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> UserListResponse:
    """List registered user accounts. Requires an active admin account."""
    users = await repository.list(limit=limit, offset=offset)
    return UserListResponse(items=[UserRead.model_validate(user) for user in users])
