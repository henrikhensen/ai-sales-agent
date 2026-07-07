"""Outlook (Microsoft Graph) reply tracking provider.

Prepared for real use but never invoked unless
``REPLY_TRACKING_PROVIDER=outlook`` and
``REPLY_TRACKING_ENABLE_REAL_READS=true`` are both set (enforced by
``backend.infrastructure.reply_tracking.factory``, not by this class).
Reuses the same OAuth connection storage as
``backend.infrastructure.email_integration.outlook_provider.
OutlookDraftProvider`` — the existing ``Mail.ReadWrite`` scope already
grants read access, so no additional scope is required. There is no send
method anywhere in this class; ``Mail.Send`` is never requested or used.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx

from backend.domain.enums import EmailProviderType
from backend.domain.repositories.email_provider_connection_repository import (
    EmailProviderConnectionRepository,
)
from backend.infrastructure.email_integration.token_crypto import TokenCipher
from backend.infrastructure.reply_tracking.base import (
    ProviderConnectionStatus,
    ReplySyncRequest,
    ReplyTrackingAuthError,
    ReplyTrackingConfigError,
    ReplyTrackingConnectionError,
    ReplyTrackingPermissionError,
    ReplyTrackingProvider,
    ReplyTrackingProviderError,
    ReplyTrackingRateLimitError,
    ReplyTrackingTimeoutError,
    SyncedReplyMessage,
)

logger = logging.getLogger("backend.reply_tracking")

_GRAPH_BASE = "https://graph.microsoft.com/v1.0"
_SELECT_FIELDS = "id,conversationId,subject,from,toRecipients,receivedDateTime,body,webLink"
# Either grant already includes read access; Mail.Send is never checked for
# or used here.
_READ_SCOPES = ("Mail.ReadWrite", "Mail.Read")


class OutlookReplyTrackingProvider(ReplyTrackingProvider):
    name = "outlook"

    def __init__(
        self,
        *,
        client_id: str | None,
        client_secret: str | None,
        tenant_id: str,
        connections: EmailProviderConnectionRepository,
        token_cipher: TokenCipher,
        timeout: float = 30,
    ) -> None:
        if not client_id or not client_secret:
            raise ReplyTrackingConfigError(
                "MICROSOFT_CLIENT_ID/MICROSOFT_CLIENT_SECRET are not set; "
                "cannot use the outlook reply tracking provider."
            )
        self._client_id = client_id
        self._client_secret = client_secret
        self._tenant_id = tenant_id or "common"
        self._connections = connections
        self._token_cipher = token_cipher
        self._timeout = timeout

    @property
    def _token_url(self) -> str:
        return (
            f"https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/token"
        )

    async def get_provider_status(self, user_id: UUID) -> ProviderConnectionStatus:
        connection = await self._connections.get_active_for_user(
            user_id, EmailProviderType.OUTLOOK
        )
        has_read_scope = bool(connection) and self._has_read_scope(connection.scope)
        message = "Not connected to Outlook."
        if connection and has_read_scope:
            message = "Connected to Outlook with read access."
        elif connection and not has_read_scope:
            message = (
                "Connected to Outlook, but without read access — reconnect "
                "with Mail.ReadWrite to sync replies."
            )
        return ProviderConnectionStatus(
            provider=self.name,
            connected=bool(connection) and has_read_scope,
            external_account_email=(
                connection.external_account_email if connection else None
            ),
            message=message,
        )

    @staticmethod
    def _has_read_scope(scope: str | None) -> bool:
        granted = scope or ""
        return any(required in granted for required in _READ_SCOPES)

    async def _get_valid_access_token(self, user_id: UUID) -> str:
        connection = await self._connections.get_active_for_user(
            user_id, EmailProviderType.OUTLOOK
        )
        if connection is None or not connection.encrypted_access_token:
            raise ReplyTrackingAuthError(
                "No active Outlook connection. Connect Outlook before "
                "syncing replies."
            )
        if not self._has_read_scope(connection.scope):
            raise ReplyTrackingPermissionError(
                "The connected Outlook account does not have read "
                "permission. Reconnect Outlook to sync replies."
            )
        if connection.token_expires_at and connection.token_expires_at <= datetime.now(
            UTC
        ):
            return await self._refresh_access_token(connection)
        return self._token_cipher.decrypt(connection.encrypted_access_token)

    async def _refresh_access_token(self, connection) -> str:
        if not connection.encrypted_refresh_token:
            raise ReplyTrackingAuthError(
                "Outlook access token expired and no refresh token is "
                "stored; reconnect Outlook."
            )
        refresh_token = self._token_cipher.decrypt(connection.encrypted_refresh_token)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(
                    self._token_url,
                    data={
                        "refresh_token": refresh_token,
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "grant_type": "refresh_token",
                    },
                )
            except httpx.TimeoutException as exc:
                raise ReplyTrackingTimeoutError(
                    "Timed out refreshing the Outlook access token."
                ) from exc
            except httpx.HTTPError as exc:
                raise ReplyTrackingConnectionError(
                    "Could not reach Microsoft to refresh the access token."
                ) from exc

        if response.status_code != 200:
            raise ReplyTrackingAuthError(
                "Outlook refresh token was rejected; reconnect Outlook."
            )
        payload = response.json()
        access_token = payload.get("access_token")
        if not access_token:
            raise ReplyTrackingProviderError(
                "Microsoft did not return a refreshed access token."
            )
        expires_in = payload.get("expires_in", 3600)
        connection.encrypted_access_token = self._token_cipher.encrypt(access_token)
        connection.token_expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
        await self._connections.update(connection)
        return access_token

    async def _search_messages(
        self, user_id: UUID, request: ReplySyncRequest
    ) -> list[SyncedReplyMessage]:
        if not request.known_emails:
            return []
        access_token = await self._get_valid_access_token(user_id)

        from_clauses = " or ".join(
            f"from/emailAddress/address eq '{email}'" for email in request.known_emails
        )
        filter_parts = [f"({from_clauses})"]
        if request.since is not None:
            filter_parts.append(
                f"receivedDateTime ge {request.since.strftime('%Y-%m-%dT%H:%M:%SZ')}"
            )
        params = {
            "$filter": " and ".join(filter_parts),
            "$top": request.max_messages,
            "$orderby": "receivedDateTime desc",
            "$select": _SELECT_FIELDS,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.get(
                    f"{_GRAPH_BASE}/me/messages",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params=params,
                )
            except httpx.TimeoutException as exc:
                raise ReplyTrackingTimeoutError(
                    "Timed out listing Outlook messages."
                ) from exc
            except httpx.HTTPError as exc:
                raise ReplyTrackingConnectionError(
                    "Could not reach Outlook to list messages."
                ) from exc

        self._raise_for_status(response, "list messages")
        return [
            self._parse_message(item)
            for item in response.json().get("value", [])[: request.max_messages]
        ]

    def _parse_message(self, payload: dict) -> SyncedReplyMessage:
        from_address = (payload.get("from") or {}).get("emailAddress", {})
        to_recipients = payload.get("toRecipients") or []
        to_email = (
            to_recipients[0].get("emailAddress", {}).get("address")
            if to_recipients
            else None
        )
        received_at_raw = payload.get("receivedDateTime")
        received_at = (
            datetime.fromisoformat(received_at_raw.replace("Z", "+00:00"))
            if received_at_raw
            else datetime.now(UTC)
        )
        message_id = payload.get("id", "")
        return SyncedReplyMessage(
            provider_message_id=message_id,
            provider_thread_id=payload.get("conversationId"),
            from_email=from_address.get("address", ""),
            from_name=from_address.get("name"),
            to_email=to_email,
            subject=payload.get("subject"),
            body_text=(payload.get("body") or {}).get("content", ""),
            received_at=received_at,
            provider_message_url=payload.get("webLink")
            or self.get_reply_provider_message_url(message_id),
        )

    async def sync_replies_for_draft(
        self, user_id: UUID, request: ReplySyncRequest
    ) -> list[SyncedReplyMessage]:
        return await self._search_messages(user_id, request)

    async def sync_replies_for_lead(
        self, user_id: UUID, request: ReplySyncRequest
    ) -> list[SyncedReplyMessage]:
        return await self._search_messages(user_id, request)

    async def sync_recent_replies(
        self, user_id: UUID, request: ReplySyncRequest
    ) -> list[SyncedReplyMessage]:
        return await self._search_messages(user_id, request)

    async def get_thread_messages(
        self, user_id: UUID, provider_thread_id: str
    ) -> list[SyncedReplyMessage]:
        access_token = await self._get_valid_access_token(user_id)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.get(
                    f"{_GRAPH_BASE}/me/messages",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={
                        "$filter": f"conversationId eq '{provider_thread_id}'",
                        "$select": _SELECT_FIELDS,
                        "$orderby": "receivedDateTime asc",
                    },
                )
            except httpx.TimeoutException as exc:
                raise ReplyTrackingTimeoutError(
                    "Timed out reading an Outlook thread."
                ) from exc
            except httpx.HTTPError as exc:
                raise ReplyTrackingConnectionError(
                    "Could not reach Outlook to read a thread."
                ) from exc

        self._raise_for_status(response, "read thread")
        return [self._parse_message(item) for item in response.json().get("value", [])]

    def get_reply_provider_message_url(self, provider_message_id: str) -> str | None:
        return f"https://outlook.office.com/mail/deeplink/read/{provider_message_id}"

    @staticmethod
    def _raise_for_status(response: httpx.Response, action: str) -> None:
        if response.status_code == 401:
            raise ReplyTrackingAuthError(
                "Outlook access token was rejected; reconnect Outlook."
            )
        if response.status_code == 403:
            raise ReplyTrackingPermissionError(
                "Outlook refused this request — the connected account may "
                "be missing read permission."
            )
        if response.status_code == 429:
            raise ReplyTrackingRateLimitError(
                "Outlook's rate limit was exceeded. Try again later."
            )
        if response.status_code >= 400:
            logger.warning(
                "outlook %s failed with status %s", action, response.status_code
            )
            raise ReplyTrackingProviderError(
                f"Outlook returned an error (status {response.status_code})."
            )
