"""Gmail draft provider.

Prepared for real use but never invoked unless
``EMAIL_INTEGRATION_PROVIDER=gmail`` and
``EMAIL_INTEGRATION_ENABLE_REAL_DRAFTS=true`` are both set (enforced by
``backend.infrastructure.email_integration.factory``, not by this class).
Requests only the ``gmail.compose`` scope — never ``gmail.send``. There is
no send method anywhere in this class; it can only create a draft or
report on one that already exists.
"""

from __future__ import annotations

import base64
import logging
from datetime import UTC, datetime, timedelta
from email.mime.text import MIMEText
from urllib.parse import urlencode
from uuid import UUID

import httpx

from backend.domain.entities.email_provider_connection import EmailProviderConnection
from backend.domain.enums import EmailProviderType, ExternalDraftProviderStatus
from backend.domain.repositories.email_provider_connection_repository import (
    EmailProviderConnectionRepository,
)
from backend.infrastructure.email_integration.base import (
    EmailDraftProvider,
    EmailIntegrationAuthError,
    EmailIntegrationConfigError,
    EmailIntegrationConnectionError,
    EmailIntegrationProviderError,
    EmailIntegrationRateLimitError,
    EmailIntegrationTimeoutError,
    ExternalDraftRequest,
    ExternalDraftResult,
    OAuthStartResult,
    ProviderConnectionStatus,
)
from backend.infrastructure.email_integration.oauth_state import create_oauth_state
from backend.infrastructure.email_integration.token_crypto import TokenCipher

logger = logging.getLogger("backend.email_integration")

_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_DRAFTS_URL = "https://gmail.googleapis.com/gmail/v1/users/me/drafts"
_SCOPE = "https://www.googleapis.com/auth/gmail.compose"


class GmailDraftProvider(EmailDraftProvider):
    name = "gmail"

    def __init__(
        self,
        *,
        client_id: str | None,
        client_secret: str | None,
        connections: EmailProviderConnectionRepository,
        token_cipher: TokenCipher,
        timeout: float = 30,
    ) -> None:
        if not client_id or not client_secret:
            raise EmailIntegrationConfigError(
                "GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET are not set; cannot "
                "use the gmail provider."
            )
        self._client_id = client_id
        self._client_secret = client_secret
        self._connections = connections
        self._token_cipher = token_cipher
        self._timeout = timeout

    async def get_provider_status(self, user_id: UUID) -> ProviderConnectionStatus:
        connection = await self._connections.get_active_for_user(
            user_id, EmailProviderType.GMAIL
        )
        return ProviderConnectionStatus(
            provider=self.name,
            connected=connection is not None,
            external_account_email=(
                connection.external_account_email if connection else None
            ),
            message="Connected to Gmail." if connection else "Not connected to Gmail.",
        )

    async def start_oauth_connection(
        self, user_id: UUID, redirect_uri: str
    ) -> OAuthStartResult:
        state = create_oauth_state(user_id, EmailProviderType.GMAIL)
        params = {
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": _SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return OAuthStartResult(
            authorization_url=f"{_AUTH_URL}?{urlencode(params)}", state=state
        )

    async def handle_oauth_callback(
        self, user_id: UUID, code: str, state: str, redirect_uri: str
    ) -> ProviderConnectionStatus:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(
                    _TOKEN_URL,
                    data={
                        "code": code,
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "redirect_uri": redirect_uri,
                        "grant_type": "authorization_code",
                    },
                )
            except httpx.TimeoutException as exc:
                raise EmailIntegrationTimeoutError(
                    "Timed out exchanging the authorization code."
                ) from exc
            except httpx.HTTPError as exc:
                raise EmailIntegrationConnectionError(
                    "Could not reach Google to exchange the authorization code."
                ) from exc

        if response.status_code != 200:
            logger.warning(
                "gmail token exchange failed with status %s", response.status_code
            )
            raise EmailIntegrationProviderError(
                f"Google rejected the authorization code (status {response.status_code})."
            )

        payload = response.json()
        access_token = payload.get("access_token")
        refresh_token = payload.get("refresh_token")
        expires_in = payload.get("expires_in", 3600)
        if not access_token:
            raise EmailIntegrationProviderError("Google did not return an access token.")

        existing = await self._connections.get_active_for_user(
            user_id, EmailProviderType.GMAIL
        )
        connection = existing or EmailProviderConnection(
            user_id=user_id, provider=EmailProviderType.GMAIL
        )
        connection.encrypted_access_token = self._token_cipher.encrypt(access_token)
        if refresh_token:
            connection.encrypted_refresh_token = self._token_cipher.encrypt(
                refresh_token
            )
        connection.token_expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
        connection.scope = _SCOPE
        connection.is_active = True

        if existing is None:
            await self._connections.create(connection)
        else:
            await self._connections.update(connection)

        return await self.get_provider_status(user_id)

    async def disconnect_provider(self, user_id: UUID) -> None:
        await self._connections.deactivate_for_user(user_id, EmailProviderType.GMAIL)

    async def _get_valid_access_token(self, user_id: UUID) -> str:
        connection = await self._connections.get_active_for_user(
            user_id, EmailProviderType.GMAIL
        )
        if connection is None or not connection.encrypted_access_token:
            raise EmailIntegrationAuthError(
                "No active Gmail connection. Connect Gmail before creating "
                "an external draft."
            )
        if connection.token_expires_at and connection.token_expires_at <= datetime.now(
            UTC
        ):
            return await self._refresh_access_token(connection)
        return self._token_cipher.decrypt(connection.encrypted_access_token)

    async def _refresh_access_token(
        self, connection: EmailProviderConnection
    ) -> str:
        if not connection.encrypted_refresh_token:
            raise EmailIntegrationAuthError(
                "Gmail access token expired and no refresh token is stored; "
                "reconnect Gmail."
            )
        refresh_token = self._token_cipher.decrypt(connection.encrypted_refresh_token)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(
                    _TOKEN_URL,
                    data={
                        "refresh_token": refresh_token,
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "grant_type": "refresh_token",
                    },
                )
            except httpx.TimeoutException as exc:
                raise EmailIntegrationTimeoutError(
                    "Timed out refreshing the Gmail access token."
                ) from exc
            except httpx.HTTPError as exc:
                raise EmailIntegrationConnectionError(
                    "Could not reach Google to refresh the access token."
                ) from exc

        if response.status_code != 200:
            raise EmailIntegrationAuthError(
                "Gmail refresh token was rejected; reconnect Gmail."
            )
        payload = response.json()
        access_token = payload.get("access_token")
        if not access_token:
            raise EmailIntegrationProviderError(
                "Google did not return a refreshed access token."
            )
        expires_in = payload.get("expires_in", 3600)
        connection.encrypted_access_token = self._token_cipher.encrypt(access_token)
        connection.token_expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
        await self._connections.update(connection)
        return access_token

    async def create_external_draft(
        self, user_id: UUID, request: ExternalDraftRequest
    ) -> ExternalDraftResult:
        access_token = await self._get_valid_access_token(user_id)
        message = MIMEText(request.body)
        message["subject"] = request.subject
        if request.recipient_email:
            message["to"] = request.recipient_email
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(
                    _DRAFTS_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                    json={"message": {"raw": raw}},
                )
            except httpx.TimeoutException as exc:
                raise EmailIntegrationTimeoutError(
                    "Timed out creating the Gmail draft."
                ) from exc
            except httpx.HTTPError as exc:
                raise EmailIntegrationConnectionError(
                    "Could not reach Gmail to create the draft."
                ) from exc

        self._raise_for_status(response, "create")

        payload = response.json()
        draft_id = payload.get("id")
        return ExternalDraftResult(
            provider=self.name,
            status=ExternalDraftProviderStatus.CREATED,
            provider_draft_id=draft_id,
            provider_draft_url=(
                f"https://mail.google.com/mail/u/0/#drafts?compose={draft_id}"
                if draft_id
                else None
            ),
            message="Gmail draft created. It has not been sent.",
        )

    async def get_external_draft_status(
        self, user_id: UUID, provider_draft_id: str
    ) -> ExternalDraftResult:
        access_token = await self._get_valid_access_token(user_id)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.get(
                    f"{_DRAFTS_URL}/{provider_draft_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
            except httpx.TimeoutException as exc:
                raise EmailIntegrationTimeoutError(
                    "Timed out checking the Gmail draft status."
                ) from exc
            except httpx.HTTPError as exc:
                raise EmailIntegrationConnectionError(
                    "Could not reach Gmail to check the draft status."
                ) from exc

        self._raise_for_status(response, "status check")

        return ExternalDraftResult(
            provider=self.name,
            status=ExternalDraftProviderStatus.CREATED,
            provider_draft_id=provider_draft_id,
            provider_draft_url=(
                f"https://mail.google.com/mail/u/0/#drafts?compose={provider_draft_id}"
            ),
            message="Gmail draft exists. It has not been sent.",
        )

    @staticmethod
    def _raise_for_status(response: httpx.Response, action: str) -> None:
        if response.status_code == 401:
            raise EmailIntegrationAuthError(
                "Gmail access token was rejected; reconnect Gmail."
            )
        if response.status_code == 404:
            raise EmailIntegrationProviderError(
                "Gmail draft was not found — it may have been deleted."
            )
        if response.status_code == 429:
            raise EmailIntegrationRateLimitError(
                "Gmail's rate limit was exceeded. Try again later."
            )
        if response.status_code >= 400:
            logger.warning(
                "gmail %s failed with status %s", action, response.status_code
            )
            raise EmailIntegrationProviderError(
                f"Gmail returned an error (status {response.status_code})."
            )
