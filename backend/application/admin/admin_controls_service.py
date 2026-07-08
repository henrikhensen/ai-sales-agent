"""Admin Controls: workspace-wide branding defaults and safety toggles.

Everything here reflects and validates *declared admin intent* — it never
substitutes for environment provider configuration, and it never actually
flips a real provider on by itself. Two non-negotiable safety gates
(Human Review, Do-not-contact) can never be turned off through this
service regardless of who asks; enabling real dispatch or manual-send
mode is rejected outright unless the matching environment flag
(``OUTREACH_DISPATCH_ENABLE_REAL_SEND``) is already explicitly set.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Request

from backend.application.admin.schemas import (
    AdminControlsStatus,
    ChecklistItem,
    CustomerSetupChecklistResponse,
    UpdateAdminControlsRequest,
    UpdateWorkspaceSettingsRequest,
    WorkspaceSettingsResponse,
)
from backend.application.audit.audit_log_service import AuditLogService
from backend.domain.entities.workspace_settings import WorkspaceSettings
from backend.domain.exceptions import UnsafeAdminControlChangeError
from backend.domain.repositories.icp_profile_repository import ICPProfileRepository
from backend.domain.repositories.offer_profile_repository import (
    OfferProfileRepository,
)
from backend.domain.repositories.workspace_settings_repository import (
    WorkspaceSettingsRepository,
)
from backend.shared.config import Settings


class AdminControlsService:
    def __init__(
        self,
        workspace_settings: WorkspaceSettingsRepository,
        icp_profiles: ICPProfileRepository,
        offer_profiles: OfferProfileRepository,
        audit: AuditLogService,
        settings: Settings,
    ) -> None:
        self._workspace_settings = workspace_settings
        self._icp_profiles = icp_profiles
        self._offer_profiles = offer_profiles
        self._audit = audit
        self._settings = settings

    # -- workspace settings (get-or-create singleton) ----------------------------------

    async def _get_or_create(self) -> WorkspaceSettings:
        existing = await self._workspace_settings.get()
        if existing is not None:
            return existing
        return await self._workspace_settings.create(
            WorkspaceSettings(
                workspace_name=self._settings.default_workspace_name,
                default_language=self._settings.default_language,
                default_tone=self._settings.default_tone,
                require_human_review=True,
                require_do_not_contact_check=True,
                allow_real_llm_calls=False,
                allow_real_email_drafts=False,
                allow_real_reply_reads=False,
                allow_real_dispatch=False,
                dispatch_mode="draft_only",
                data_retention_enabled=self._settings.data_retention_enabled,
                anonymize_instead_of_delete=(
                    self._settings.data_retention_anonymize_instead_of_delete
                ),
                data_export_enabled=True,
                data_subject_requests_enabled=True,
            )
        )

    async def get_workspace_settings(self) -> WorkspaceSettingsResponse:
        record = await self._get_or_create()
        return self._to_workspace_response(record)

    async def update_workspace_settings(
        self,
        request: UpdateWorkspaceSettingsRequest,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> WorkspaceSettingsResponse:
        record = await self._get_or_create()
        updates = request.model_dump(exclude_unset=True)
        for field_name, value in updates.items():
            setattr(record, field_name, value)
        updated = await self._workspace_settings.update(record)
        assert updated is not None

        await self._audit.record(
            action="workspace_settings_updated",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="workspace_settings",
            entity_id=updated.id,
            metadata={"fields": list(updates.keys())},
            request=http_request,
        )
        return self._to_workspace_response(updated)

    @staticmethod
    def _to_workspace_response(record: WorkspaceSettings) -> WorkspaceSettingsResponse:
        return WorkspaceSettingsResponse(
            id=record.id,
            workspace_name=record.workspace_name,
            company_name=record.company_name,
            company_website=record.company_website,
            default_language=record.default_language,
            default_tone=record.default_tone,
            default_icp_profile_id=record.default_icp_profile_id,
            default_offer_profile_id=record.default_offer_profile_id,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    # -- admin controls (safety toggles) -----------------------------------------------

    def _provider_config_checks(self) -> tuple[bool, bool, bool, bool]:
        real_llm_configured = bool(
            self._settings.llm_enable_real_calls
            and self._settings.llm_provider == "anthropic"
            and self._settings.anthropic_api_key
        )
        email_integration_configured = bool(
            self._settings.email_integration_enable_real_drafts
            and self._settings.email_integration_provider in ("gmail", "outlook")
            and self._settings.email_token_encryption_key
            and (
                (
                    self._settings.email_integration_provider == "gmail"
                    and self._settings.google_client_id
                )
                or (
                    self._settings.email_integration_provider == "outlook"
                    and self._settings.microsoft_client_id
                )
            )
        )
        reply_tracking_configured = bool(
            self._settings.reply_tracking_enable_real_reads
            and self._settings.reply_tracking_provider in ("gmail", "outlook")
            and self._settings.email_token_encryption_key
        )
        real_send_env_enabled = bool(self._settings.outreach_dispatch_enable_real_send)
        return (
            real_llm_configured,
            email_integration_configured,
            reply_tracking_configured,
            real_send_env_enabled,
        )

    def _dispatch_safe(self) -> bool:
        return not (
            self._settings.outreach_dispatch_mode == "manual_send"
            and self._settings.outreach_dispatch_enable_real_send
        )

    async def get_admin_controls(self) -> AdminControlsStatus:
        record = await self._get_or_create()
        (
            real_llm_configured,
            email_integration_configured,
            reply_tracking_configured,
            real_send_env_enabled,
        ) = self._provider_config_checks()

        warnings: list[str] = []
        if record.allow_real_llm_calls and not real_llm_configured:
            warnings.append(
                "allow_real_llm_calls is on, but LLM_ENABLE_REAL_CALLS/ANTHROPIC_API_KEY "
                "are not fully configured — real calls stay inactive regardless."
            )
        if record.allow_real_email_drafts and not email_integration_configured:
            warnings.append(
                "allow_real_email_drafts is on, but the Gmail/Outlook OAuth "
                "environment is not fully configured — drafts stay mock-only."
            )
        if record.allow_real_reply_reads and not reply_tracking_configured:
            warnings.append(
                "allow_real_reply_reads is on, but Reply Tracking's OAuth "
                "environment is not fully configured — reads stay mock-only."
            )
        if not self._dispatch_safe():
            warnings.append(
                "dispatch_mode is 'manual_send' with real send enabled — a "
                "confirmed manual send may be attempted (mock provider only; "
                "Gmail/Outlook never implement real sending)."
            )

        return AdminControlsStatus(
            require_human_review=record.require_human_review,
            require_do_not_contact_check=record.require_do_not_contact_check,
            allow_real_llm_calls=record.allow_real_llm_calls,
            allow_real_email_drafts=record.allow_real_email_drafts,
            allow_real_reply_reads=record.allow_real_reply_reads,
            allow_real_dispatch=record.allow_real_dispatch,
            dispatch_mode=record.dispatch_mode,
            real_llm_configured=real_llm_configured,
            email_integration_configured=email_integration_configured,
            reply_tracking_configured=reply_tracking_configured,
            real_send_env_enabled=real_send_env_enabled,
            data_retention_enabled=record.data_retention_enabled,
            anonymize_instead_of_delete=record.anonymize_instead_of_delete,
            data_export_enabled=record.data_export_enabled,
            data_subject_requests_enabled=record.data_subject_requests_enabled,
            legal_review_required=True,
            warnings=warnings,
            blockers=[],
        )

    async def update_admin_controls(
        self,
        request: UpdateAdminControlsRequest,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> AdminControlsStatus:
        record = await self._get_or_create()
        updates = request.model_dump(exclude_unset=True)

        blockers: list[str] = []
        if updates.get("require_human_review") is False:
            blockers.append(
                "require_human_review can never be turned off — Human Review "
                "is a non-negotiable safety gate in this system."
            )
        if updates.get("require_do_not_contact_check") is False:
            blockers.append(
                "require_do_not_contact_check can never be turned off — "
                "Do-not-contact is a non-negotiable safety gate in this system."
            )
        _, _, _, real_send_env_enabled = self._provider_config_checks()
        if updates.get("allow_real_dispatch") is True and not real_send_env_enabled:
            blockers.append(
                "allow_real_dispatch cannot be enabled: "
                "OUTREACH_DISPATCH_ENABLE_REAL_SEND is not set in the environment. "
                "Real dispatch requires every safety gate to pass, including "
                "explicit environment activation."
            )
        if updates.get("dispatch_mode") == "manual_send" and not real_send_env_enabled:
            blockers.append(
                "dispatch_mode cannot be set to 'manual_send': "
                "OUTREACH_DISPATCH_ENABLE_REAL_SEND is not set in the environment."
            )

        if blockers:
            # record_independent: this call is immediately followed by a
            # raise, which would otherwise roll back the ambient request
            # session (see get_session) and silently drop the audit trail
            # of the very rejection it's meant to record.
            await self._audit.record_independent(
                action="unsafe_admin_control_change_blocked",
                result="blocked",
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                entity_type="workspace_settings",
                entity_id=record.id,
                reason="; ".join(blockers),
                request=http_request,
            )
            raise UnsafeAdminControlChangeError(blockers)

        for field_name, value in updates.items():
            setattr(record, field_name, value)
        updated = await self._workspace_settings.update(record)
        assert updated is not None

        await self._audit.record(
            action="admin_controls_updated",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="workspace_settings",
            entity_id=updated.id,
            metadata={"fields": list(updates.keys())},
            request=http_request,
        )
        return await self.get_admin_controls()

    # -- setup checklist ------------------------------------------------------------------

    async def get_setup_checklist(self) -> CustomerSetupChecklistResponse:
        has_offer = bool(await self._offer_profiles.list(limit=1, active_only=True))
        has_icp = bool(await self._icp_profiles.list(limit=1, active_only=True))
        (
            real_llm_configured,
            email_integration_configured,
            reply_tracking_configured,
            _real_send_env_enabled,
        ) = self._provider_config_checks()

        items = [
            ChecklistItem(
                key="offer_profile",
                label="Offer Profile vorhanden",
                status="passed" if has_offer else "blocker",
                detail=None if has_offer else "Lege mindestens ein aktives Offer Profile an.",
            ),
            ChecklistItem(
                key="icp_profile",
                label="ICP Profile vorhanden",
                status="passed" if has_icp else "blocker",
                detail=None if has_icp else "Lege mindestens ein aktives ICP Profile an.",
            ),
            ChecklistItem(
                key="do_not_contact",
                label="Do-not-contact aktiv",
                status="passed",
                detail="Strukturell immer aktiv — kann nicht deaktiviert werden.",
            ),
            ChecklistItem(
                key="human_review",
                label="Human Review aktiv",
                status="passed",
                detail="Strukturell immer aktiv — kann nicht deaktiviert werden.",
            ),
            ChecklistItem(
                key="llm_safe_mode",
                label="LLM Safe Mode geprüft",
                status="warning" if self._settings.llm_enable_real_calls else "passed",
                detail=(
                    "Echte LLM Calls sind aktiviert (LLM_ENABLE_REAL_CALLS=true)."
                    if self._settings.llm_enable_real_calls
                    else None
                ),
            ),
            ChecklistItem(
                key="email_integration_safe_mode",
                label="Email Integration Safe Mode geprüft",
                status=(
                    "warning"
                    if self._settings.email_integration_enable_real_drafts
                    else "passed"
                ),
                detail=(
                    "Echte Drafts sind aktiviert (EMAIL_INTEGRATION_ENABLE_REAL_DRAFTS=true)."
                    if self._settings.email_integration_enable_real_drafts
                    else None
                ),
            ),
            ChecklistItem(
                key="reply_tracking_safe_mode",
                label="Reply Tracking Safe Mode geprüft",
                status=(
                    "warning"
                    if self._settings.reply_tracking_enable_real_reads
                    else "passed"
                ),
                detail=(
                    "Echtes Reply-Lesen ist aktiviert (REPLY_TRACKING_ENABLE_REAL_READS=true)."
                    if self._settings.reply_tracking_enable_real_reads
                    else None
                ),
            ),
            ChecklistItem(
                key="dispatch_safe_mode",
                label="Dispatch Safe Mode geprüft",
                status="passed" if self._dispatch_safe() else "warning",
                detail=(
                    None
                    if self._dispatch_safe()
                    else "manual_send + Real Send sind gleichzeitig aktiv."
                ),
            ),
            ChecklistItem(
                key="audit_logs",
                label="Audit Logs aktiv",
                status="passed" if self._settings.audit_logs_enabled else "blocker",
                detail=None if self._settings.audit_logs_enabled else "AUDIT_LOGS_ENABLED=false.",
            ),
            ChecklistItem(
                key="rate_limits",
                label="Rate Limits aktiv",
                status="passed" if self._settings.rate_limit_enabled else "blocker",
                detail=None if self._settings.rate_limit_enabled else "RATE_LIMIT_ENABLED=false.",
            ),
            ChecklistItem(
                key="backup_setup",
                label="Backup Setup vorhanden",
                status="passed" if self._settings.enable_backups else "warning",
                detail=(
                    None
                    if self._settings.enable_backups
                    else "ENABLE_BACKUPS=false — kein Backup-Job konfiguriert."
                ),
            ),
            ChecklistItem(
                key="system_status",
                label="System Status ok",
                status="not_checked",
                detail="Siehe GET /api/v1/system/status für Live-Details.",
            ),
            ChecklistItem(
                key="customer_readiness",
                label="Customer Readiness ok",
                status="not_checked",
                detail="Siehe CUSTOMER_READINESS.md — rechtliche Prüfung bleibt erforderlich.",
            ),
        ]

        if any(item.status == "blocker" for item in items):
            overall = "blocker"
        elif any(item.status == "warning" for item in items):
            overall = "warning"
        elif any(item.status == "not_checked" for item in items):
            overall = "not_checked"
        else:
            overall = "passed"

        return CustomerSetupChecklistResponse(items=items, overall_status=overall)

    # -- shared config accessors (used by OnboardingService) ------------------------------

    def provider_config_checks(self) -> tuple[bool, bool, bool, bool]:
        return self._provider_config_checks()

    def dispatch_safe(self) -> bool:
        return self._dispatch_safe()
