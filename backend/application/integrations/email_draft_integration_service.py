"""Gmail/Outlook Draft Integration service.

Orchestrates OAuth connection management and external draft creation for
Gmail/Outlook/Mock. Never sends an email — this only ever creates a draft
at a provider, and only when a user consciously requests it (there is no
call site anywhere in the Sales Workflow that invokes this service).

Do-not-contact and Human Review both take precedence over this
integration and cannot be bypassed: :meth:`create_external_draft` checks
both before ever calling the configured provider, and persists the
outcome (created or blocked, and why) as the draft's external-draft audit
record either way.
"""

from __future__ import annotations

import logging
from uuid import UUID

from backend.application.compliance.do_not_contact_service import DoNotContactService
from backend.application.integrations.schemas import (
    CreateExternalEmailDraftResponse,
    EmailIntegrationProvidersResponse,
    EmailIntegrationStatusResponse,
    EmailProviderInfo,
    ExternalEmailDraftResponse,
    ExternalEmailDraftStatusResponse,
    StartEmailProviderConnectionResponse,
)
from backend.domain.entities.external_email_draft import ExternalEmailDraft
from backend.domain.enums import (
    EmailDraftReviewStatus,
    EmailProviderType,
    ExternalDraftBlockReason,
    ExternalDraftProviderStatus,
)
from backend.domain.exceptions import EmailDraftNotFoundError
from backend.domain.repositories.company_repository import CompanyRepository
from backend.domain.repositories.contact_repository import ContactRepository
from backend.domain.repositories.email_draft_repository import EmailDraftRepository
from backend.domain.repositories.email_provider_connection_repository import (
    EmailProviderConnectionRepository,
)
from backend.domain.repositories.external_email_draft_repository import (
    ExternalEmailDraftRepository,
)
from backend.domain.repositories.workflow_run_repository import WorkflowRunRepository
from backend.infrastructure.email_integration.base import (
    EmailDraftProvider,
    EmailIntegrationAuthError,
    EmailIntegrationConfigError,
    EmailIntegrationConnectionError,
    EmailIntegrationError,
    EmailIntegrationProviderError,
    EmailIntegrationRateLimitError,
    EmailIntegrationTimeoutError,
    ExternalDraftRequest,
)
from backend.infrastructure.email_integration.factory import (
    create_email_draft_provider,
)
from backend.infrastructure.email_integration.oauth_state import parse_oauth_state
from backend.shared.config import Settings

logger = logging.getLogger("backend.email_integration")

_DISPLAY_NAMES = {"mock": "Mock", "gmail": "Gmail", "outlook": "Outlook"}


class EmailDraftIntegrationService:
    """Coordinates provider connections and external draft creation."""

    def __init__(
        self,
        connections: EmailProviderConnectionRepository,
        external_drafts: ExternalEmailDraftRepository,
        email_drafts: EmailDraftRepository,
        companies: CompanyRepository,
        workflow_runs: WorkflowRunRepository,
        contacts: ContactRepository,
        compliance: DoNotContactService,
        settings: Settings,
    ) -> None:
        self._connections = connections
        self._external_drafts = external_drafts
        self._email_drafts = email_drafts
        self._companies = companies
        self._workflow_runs = workflow_runs
        self._contacts = contacts
        self._compliance = compliance
        self._settings = settings

    def _active_provider_name(self) -> str:
        return self._settings.email_integration_provider.strip().lower()

    def _build_provider(self) -> EmailDraftProvider:
        return create_email_draft_provider(self._connections, self._settings)

    def _redirect_uri(self, provider: str) -> str:
        base = self._settings.oauth_redirect_base_url.rstrip("/")
        return f"{base}/api/v1/integrations/email/{provider}/callback"

    # -- status / providers ----------------------------------------------------

    async def get_status(self, user_id: UUID) -> EmailIntegrationStatusResponse:
        active = self._active_provider_name()
        real_enabled = self._settings.email_integration_enable_real_drafts
        safe_mode = active == "mock" or not real_enabled

        if active in ("gmail", "outlook") and real_enabled:
            configured = self._is_configured(active)
            if not configured:
                return EmailIntegrationStatusResponse(
                    active_provider=active,
                    real_drafts_enabled=real_enabled,
                    safe_mode=True,
                    connected=False,
                    message=(
                        f"EMAIL_INTEGRATION_PROVIDER={active} and "
                        "EMAIL_INTEGRATION_ENABLE_REAL_DRAFTS=true, but the "
                        "required OAuth configuration is missing, so the "
                        "mock provider is used instead. No real draft is "
                        "created and no cost or risk is incurred."
                    ),
                )

        provider = self._build_provider()
        status = await provider.get_provider_status(user_id)
        if safe_mode and active != "mock":
            message = (
                f"EMAIL_INTEGRATION_PROVIDER={active} but "
                "EMAIL_INTEGRATION_ENABLE_REAL_DRAFTS is not true, so the "
                "mock provider is used instead. No real draft is created."
            )
        elif active == "mock":
            message = "Mock provider is active. No real Gmail/Outlook draft is ever created."
        else:
            message = status.message
        return EmailIntegrationStatusResponse(
            active_provider=provider.name,
            real_drafts_enabled=real_enabled,
            safe_mode=provider.name == "mock",
            connected=status.connected,
            external_account_email=status.external_account_email,
            message=message,
        )

    def _is_configured(self, provider: str) -> bool:
        if provider == "gmail":
            return bool(
                self._settings.google_client_id
                and self._settings.google_client_secret
                and self._settings.email_token_encryption_key
            )
        if provider == "outlook":
            return bool(
                self._settings.microsoft_client_id
                and self._settings.microsoft_client_secret
                and self._settings.email_token_encryption_key
            )
        return True

    async def list_providers(self, user_id: UUID) -> EmailIntegrationProvidersResponse:
        active = self._active_provider_name()
        items: list[EmailProviderInfo] = []
        for provider_type in EmailProviderType:
            name = provider_type.value
            connection = await self._connections.get_active_for_user(
                user_id, provider_type
            )
            items.append(
                EmailProviderInfo(
                    provider=name,
                    display_name=_DISPLAY_NAMES[name],
                    is_active_provider=name == active,
                    requires_oauth=name != "mock",
                    configured=self._is_configured(name),
                    connected=connection is not None,
                    external_account_email=(
                        connection.external_account_email if connection else None
                    ),
                )
            )
        return EmailIntegrationProvidersResponse(items=items)

    # -- OAuth connection lifecycle ---------------------------------------------

    async def start_connection(
        self, user_id: UUID, provider: EmailProviderType
    ) -> StartEmailProviderConnectionResponse:
        redirect_uri = self._redirect_uri(provider.value)
        instance = self._build_provider_instance(provider)
        result = await instance.start_oauth_connection(user_id, redirect_uri)
        return StartEmailProviderConnectionResponse(
            provider=provider.value,
            authorization_url=result.authorization_url,
            message=(
                "Open this URL to authorize draft-only access. No email "
                "will ever be sent through this connection."
            ),
        )

    async def handle_callback(
        self, provider: EmailProviderType, code: str, state: str
    ) -> tuple[UUID, bool]:
        """Complete an OAuth callback. Returns ``(user_id, connected)``."""
        state_user_id, state_provider = parse_oauth_state(state)
        if state_provider != provider:
            raise EmailIntegrationConfigError(
                "OAuth state does not match the requested provider."
            )
        redirect_uri = self._redirect_uri(provider.value)
        instance = self._build_provider_instance(provider)
        status = await instance.handle_oauth_callback(
            state_user_id, code, state, redirect_uri
        )
        return state_user_id, status.connected

    async def disconnect(self, user_id: UUID, provider: EmailProviderType) -> None:
        instance = self._build_provider_instance(provider)
        await instance.disconnect_provider(user_id)

    def _build_provider_instance(
        self, provider: EmailProviderType
    ) -> EmailDraftProvider:
        """Build a provider instance for connection management, independent
        of which provider is currently active for draft creation — a user
        may pre-connect an account before an admin switches the system to
        it. Falls back to mock if real drafts are disabled or
        misconfigured, same as :func:`create_email_draft_provider`.
        """
        overridden = self._settings.model_copy(
            update={"email_integration_provider": provider.value}
        )
        return create_email_draft_provider(self._connections, overridden)

    # -- external draft creation -------------------------------------------------

    async def create_external_draft(
        self, user_id: UUID, email_draft_id: UUID
    ) -> CreateExternalEmailDraftResponse:
        draft = await self._email_drafts.get(email_draft_id)
        if draft is None:
            raise EmailDraftNotFoundError(email_draft_id)

        if draft.review_status != EmailDraftReviewStatus.APPROVED:
            return await self._record_blocked(
                draft.id,
                user_id,
                ExternalDraftBlockReason.REVIEW_NOT_APPROVED,
                (
                    "This email draft is not approved "
                    f"(review_status='{draft.review_status.value}'). It must be "
                    "approved by a reviewer or admin before an external draft "
                    "can be created. Approval still never sends anything."
                ),
            )

        company = await self._companies.get(draft.company_id)
        contact_email = None
        if draft.workflow_run_id is not None:
            run = await self._workflow_runs.get_by_id(draft.workflow_run_id)
            if run is not None and run.contact_id is not None:
                contact = await self._contacts.get(run.contact_id)
                contact_email = contact.email if contact else None

        block = await self._compliance.check(
            email=contact_email,
            domain=company.domain if company else None,
            company_name=company.name if company else None,
        )
        if block.is_blocked:
            return await self._record_blocked(
                draft.id,
                user_id,
                ExternalDraftBlockReason.DO_NOT_CONTACT,
                (
                    "Do-not-contact blockiert Outreach: this target matches "
                    f"an active opt-out entry (matched by {block.matched_by}). "
                    "No external draft was created and no provider was called."
                ),
            )

        try:
            provider = self._build_provider()
        except EmailIntegrationError as exc:
            return await self._record_blocked(
                draft.id,
                user_id,
                ExternalDraftBlockReason.PROVIDER_NOT_CONFIGURED,
                str(exc),
            )

        subject = draft.subject_lines[0] if draft.subject_lines else "(No subject)"
        subject = subject[: self._settings.email_draft_max_subject_chars]
        body = draft.email_body[: self._settings.email_draft_max_body_chars]

        try:
            result = await provider.create_external_draft(
                user_id,
                ExternalDraftRequest(
                    subject=subject, body=body, recipient_email=contact_email
                ),
            )
        except (
            EmailIntegrationConfigError,
            EmailIntegrationAuthError,
        ) as exc:
            return await self._record_blocked(
                draft.id, user_id, ExternalDraftBlockReason.PROVIDER_NOT_CONFIGURED, str(exc)
            )
        except (
            EmailIntegrationRateLimitError,
            EmailIntegrationTimeoutError,
            EmailIntegrationConnectionError,
            EmailIntegrationProviderError,
        ) as exc:
            logger.warning(
                "external draft creation failed for draft %s via %s: %s",
                draft.id,
                provider.name,
                type(exc).__name__,
            )
            saved = await self._upsert_external_draft(
                draft.id,
                provider_name=provider.name,
                status=ExternalDraftProviderStatus.FAILED,
                created_by_user_id=user_id,
                last_error=str(exc),
            )
            return CreateExternalEmailDraftResponse(
                blocked=False,
                block_reason=ExternalDraftBlockReason.PROVIDER_ERROR.value,
                external_draft=ExternalEmailDraftResponse.model_validate(saved),
                message=str(exc),
            )

        saved = await self._upsert_external_draft(
            draft.id,
            provider_name=result.provider,
            status=result.status,
            provider_draft_id=result.provider_draft_id,
            provider_draft_url=result.provider_draft_url,
            created_by_user_id=user_id,
        )
        return CreateExternalEmailDraftResponse(
            blocked=False,
            external_draft=ExternalEmailDraftResponse.model_validate(saved),
            message=result.message,
        )

    async def get_external_draft_status(
        self, email_draft_id: UUID
    ) -> ExternalEmailDraftStatusResponse:
        draft = await self._email_drafts.get(email_draft_id)
        if draft is None:
            raise EmailDraftNotFoundError(email_draft_id)

        existing = await self._external_drafts.get_by_email_draft_id(email_draft_id)
        if existing is None:
            return ExternalEmailDraftStatusResponse(
                exists=False, message="No external draft has been created yet."
            )
        return ExternalEmailDraftStatusResponse(
            exists=True,
            external_draft=ExternalEmailDraftResponse.model_validate(existing),
            message="External draft metadata found.",
        )

    # -- helpers -----------------------------------------------------------------

    async def _record_blocked(
        self,
        email_draft_id: UUID,
        user_id: UUID,
        reason: ExternalDraftBlockReason,
        detail: str,
    ) -> CreateExternalEmailDraftResponse:
        saved = await self._upsert_external_draft(
            email_draft_id,
            provider_name=self._active_provider_name(),
            status=ExternalDraftProviderStatus.BLOCKED,
            created_by_user_id=user_id,
            last_error=f"{reason.value}: {detail}",
        )
        return CreateExternalEmailDraftResponse(
            blocked=True,
            block_reason=reason.value,
            external_draft=ExternalEmailDraftResponse.model_validate(saved),
            message=detail,
        )

    async def _upsert_external_draft(
        self,
        email_draft_id: UUID,
        *,
        provider_name: str,
        status: ExternalDraftProviderStatus,
        created_by_user_id: UUID | None,
        provider_draft_id: str | None = None,
        provider_draft_url: str | None = None,
        last_error: str | None = None,
    ) -> ExternalEmailDraft:
        existing = await self._external_drafts.get_by_email_draft_id(email_draft_id)
        entity = ExternalEmailDraft(
            id=existing.id if existing else None,
            email_draft_id=email_draft_id,
            provider=EmailProviderType(provider_name),
            provider_status=status,
            provider_draft_id=provider_draft_id,
            provider_draft_url=provider_draft_url,
            created_by_user_id=created_by_user_id,
            last_error=last_error,
            is_active=True,
        )
        if existing is None:
            return await self._external_drafts.create(entity)
        updated = await self._external_drafts.update(entity)
        assert updated is not None
        return updated
