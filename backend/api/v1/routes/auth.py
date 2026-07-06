from fastapi import APIRouter, HTTPException, status

from backend.api.dependencies.auth import CurrentUserDep
from backend.api.v1.dependencies import AuthServiceDep
from backend.api.v1.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserRead,
)
from backend.domain.exceptions import EmailAlreadyRegisteredError, InvalidCredentialsError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, service: AuthServiceDep) -> UserRead:
    """Register a new local user account.

    Passwords are hashed with bcrypt and never stored or returned in plain
    text. No external identity provider and no OAuth in this phase.
    """
    try:
        user = await service.register(
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
            role=payload.role,
        )
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, service: AuthServiceDep) -> TokenResponse:
    """Authenticate with email + password and receive a JWT access token.

    Use the token as ``Authorization: Bearer <token>`` on protected
    endpoints (e.g. ``GET /auth/me``).
    """
    try:
        token = await service.login(payload.email, payload.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return TokenResponse(access_token=token)


@router.get("/me", response_model=CurrentUserResponse)
async def read_current_user(current_user: CurrentUserDep) -> CurrentUserResponse:
    """Return the currently authenticated user, resolved from the access token."""
    return CurrentUserResponse.model_validate(current_user)
