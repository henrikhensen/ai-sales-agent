from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend.api.dependencies.auth import CurrentUserDep
from backend.api.v1.dependencies import AuditLogServiceDep, AuthServiceDep
from backend.api.v1.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserRead,
)
from backend.domain.exceptions import EmailAlreadyRegisteredError, InvalidCredentialsError
from backend.shared.rate_limit import rate_limit
from backend.shared.security import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

_auth_rate_limit = rate_limit("auth", "rate_limit_auth_per_minute", 60)


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_auth_rate_limit)],
)
async def register(
    payload: UserCreate,
    service: AuthServiceDep,
    audit: AuditLogServiceDep,
    request: Request,
) -> UserRead:
    """Register a new local user account.

    Passwords are hashed with bcrypt and never stored or returned in plain
    text. No external identity provider and no OAuth in this phase.
    Rate-limited per IP (``RATE_LIMIT_AUTH_PER_MINUTE``).
    """
    try:
        user = await service.register(
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
            role=payload.role,
        )
    except EmailAlreadyRegisteredError as exc:
        await audit.record(
            action="user_register",
            result="failed",
            entity_type="user",
            reason="email already registered",
            request=request,
        )
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    await audit.record(
        action="user_register",
        result="success",
        actor_user_id=user.id,
        actor_role=user.role.value,
        entity_type="user",
        entity_id=user.id,
        request=request,
    )
    return UserRead.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(_auth_rate_limit)],
)
async def login(
    payload: LoginRequest,
    service: AuthServiceDep,
    audit: AuditLogServiceDep,
    request: Request,
) -> TokenResponse:
    """Authenticate with email + password and receive a JWT access token.

    Use the token as ``Authorization: Bearer <token>`` on protected
    endpoints (e.g. ``GET /auth/me``). Rate-limited per IP
    (``RATE_LIMIT_AUTH_PER_MINUTE``) to slow down credential-stuffing.
    """
    try:
        user = await service.authenticate(payload.email, payload.password)
    except InvalidCredentialsError as exc:
        await audit.record(
            action="login",
            result="failed",
            entity_type="user",
            reason="invalid credentials",
            request=request,
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    token = create_access_token(subject=str(user.id))
    await audit.record(
        action="login",
        result="success",
        actor_user_id=user.id,
        actor_role=user.role.value,
        entity_type="user",
        entity_id=user.id,
        request=request,
    )
    return TokenResponse(access_token=token)


@router.get("/me", response_model=CurrentUserResponse)
async def read_current_user(current_user: CurrentUserDep) -> CurrentUserResponse:
    """Return the currently authenticated user, resolved from the access token."""
    return CurrentUserResponse.model_validate(current_user)
