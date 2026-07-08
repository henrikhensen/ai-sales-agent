"""Admin Controls: workspace branding defaults and safety toggles.

Admin-only throughout — every mutating endpoint validates the change
against non-negotiable safety gates (Human Review, Do-not-contact) and
against whether the environment actually backs a requested real-provider
flag. No secret, API key, or token is ever returned here.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend.api.dependencies.auth import RequireAdminUserDep
from backend.api.v1.dependencies import AdminControlsServiceDep
from backend.application.admin.schemas import (
    AdminControlsStatus,
    CustomerSetupChecklistResponse,
    UpdateAdminControlsRequest,
    UpdateWorkspaceSettingsRequest,
    WorkspaceSettingsResponse,
)
from backend.domain.exceptions import UnsafeAdminControlChangeError
from backend.shared.rate_limit import rate_limit

router = APIRouter(prefix="/admin", tags=["admin"])

_admin_update_rate_limit = Depends(
    rate_limit("admin_controls_update", "rate_limit_default_per_minute", 60)
)


@router.get("/workspace-settings", response_model=WorkspaceSettingsResponse)
async def get_workspace_settings(
    service: AdminControlsServiceDep,
    _current_user: RequireAdminUserDep,
) -> WorkspaceSettingsResponse:
    return await service.get_workspace_settings()


@router.patch(
    "/workspace-settings",
    response_model=WorkspaceSettingsResponse,
    dependencies=[_admin_update_rate_limit],
)
async def update_workspace_settings(
    payload: UpdateWorkspaceSettingsRequest,
    service: AdminControlsServiceDep,
    current_user: RequireAdminUserDep,
    request: Request,
) -> WorkspaceSettingsResponse:
    return await service.update_workspace_settings(
        payload,
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        http_request=request,
    )


@router.get("/controls", response_model=AdminControlsStatus)
async def get_admin_controls(
    service: AdminControlsServiceDep,
    _current_user: RequireAdminUserDep,
) -> AdminControlsStatus:
    return await service.get_admin_controls()


@router.patch(
    "/controls",
    response_model=AdminControlsStatus,
    dependencies=[_admin_update_rate_limit],
)
async def update_admin_controls(
    payload: UpdateAdminControlsRequest,
    service: AdminControlsServiceDep,
    current_user: RequireAdminUserDep,
    request: Request,
) -> AdminControlsStatus:
    """Update safety toggles. Human Review and Do-not-contact can never be
    turned off; enabling real dispatch or manual-send mode is rejected
    outright unless OUTREACH_DISPATCH_ENABLE_REAL_SEND is already set in
    the environment. Rejected changes are not partially applied.
    """
    try:
        return await service.update_admin_controls(
            payload,
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except UnsafeAdminControlChangeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/setup-checklist", response_model=CustomerSetupChecklistResponse)
async def get_setup_checklist(
    service: AdminControlsServiceDep,
    _current_user: RequireAdminUserDep,
) -> CustomerSetupChecklistResponse:
    return await service.get_setup_checklist()
