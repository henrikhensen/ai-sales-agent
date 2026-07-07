"""Gmail reply tracking provider.

Prepared for real use but never invoked unless
``REPLY_TRACKING_PROVIDER=gmail`` and
``REPLY_TRACKING_ENABLE_REAL_READS=true`` are both set (enforced by
``backend.infrastructure.reply_tracking.factory``, not by this class).
Reuses the same OAuth connection storage as
``backend.infrastructure.email_integration.gmail_provider.GmailDraftProvider``
(encrypted tokens, same repository) — it only ever reads messages that
already exist in the connected mailbox. There is no send method anywhere
in this class.
"""

from __future__ import annotations

import base64
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

_TOKEN_URL = "https://oauth2.googleapis.com/token"
_MESSAGES_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
# Any of these grants read access; the draft-only connection scope
# (gmail.compose) grants none of them.
_READ_SCOPES = (
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://mail.google.com/",
)


class GmailReplyTrackingProvider(ReplyTrackingProvider):
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
            raise ReplyTrackingConfigError(
                "GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET are not set; cannot "
                "use the gmail reply tracking provider."
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
        has_read_scope = bool(connection) and self._has_read_scope(connection.scope)
        message = "Not connected to Gmail."
        if connection and has_read_scope:
            message = "Connected to Gmail with read access."
        elif connection and not has_read_scope:
            message = (
                "Connected to Gmail, but only with draft-only scope — "
                "reconnect with read access to sync replies."
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
        granted = (scope or "").split()
        return any(required in granted for required in _READ_SCOPES)

    async def _get_valid_access_token(self, user_id: UUID) -> str:
        connection = await self._connections.get_active_for_user(
            user_id, EmailProviderType.GMAIL
        )
        if connection is None or not connection.encrypted_access_token:
            raise ReplyTrackingAuthError(
                "No active Gmail connection. Connect Gmail before syncing replies."
            )
        if not self._has_read_scope(connection.scope):
            raise ReplyTrackingPermissionError(
                "The connected Gmail account only granted draft-only access. "
                "Reconnect Gmail with read permission to sync replies."
            )
        if connection.token_expires_at and connection.token_expires_at <= datetime.now(
            UTC
        ):
            return await self._refresh_access_token(connection)
        return self._token_cipher.decrypt(connection.encrypted_access_token)

    async def _refresh_access_token(self, connection) -> str:
        if not connection.encrypted_refresh_token:
            raise ReplyTrackingAuthError(
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
                raise ReplyTrackingTimeoutError(
                    "Timed out refreshing the Gmail access token."
                ) from exc
            except httpx.HTTPError as exc:
                raise ReplyTrackingConnectionError(
                    "Could not reach Google to refresh the access token."
                ) from exc

        if response.status_code != 200:
            raise ReplyTrackingAuthError(
                "Gmail refresh token was rejected; reconnect Gmail."
            )
        payload = response.json()
        access_token = payload.get("access_token")
        if not access_token:
            raise ReplyTrackingProviderError(
                "Google did not return a refreshed access token."
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

        from_clause = " OR ".join(f"from:{email}" for email in request.known_emails)
        query = f"({from_clause})"
        if request.since is not None:
            query += f" after:{int(request.since.timestamp())}"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                list_response = await client.get(
                    _MESSAGES_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"q": query, "maxResults": request.max_messages},
                )
            except httpx.TimeoutException as exc:
                raise ReplyTrackingTimeoutError(
                    "Timed out listing Gmail messages."
                ) from exc
            except httpx.HTTPError as exc:
                raise ReplyTrackingConnectionError(
                    "Could not reach Gmail to list messages."
                ) from exc

        self._raise_for_status(list_response, "list messages")
        message_ids = [
            item["id"] for item in list_response.json().get("messages", [])
        ]

        messages: list[SyncedReplyMessage] = []
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for message_id in message_ids[: request.max_messages]:
                try:
                    detail_response = await client.get(
                        f"{_MESSAGES_URL}/{message_id}",
                        headers={"Authorization": f"Bearer {access_token}"},
                        params={"format": "full"},
                    )
                except httpx.TimeoutException as exc:
                    raise ReplyTrackingTimeoutError(
                        "Timed out reading a Gmail message."
                    ) from exc
                except httpx.HTTPError as exc:
                    raise ReplyTrackingConnectionError(
                        "Could not reach Gmail to read a message."
                    ) from exc

                self._raise_for_status(detail_response, "read message")
                messages.append(self._parse_message(detail_response.json()))

        return messages

    def _parse_message(self, payload: dict) -> SyncedReplyMessage:
        headers = {
            header["name"].lower(): header["value"]
            for header in payload.get("payload", {}).get("headers", [])
        }
        from_header = headers.get("from", "")
        from_name, from_email = self._split_from_header(from_header)
        internal_date_ms = int(payload.get("internalDate", "0"))
        received_at = (
            datetime.fromtimestamp(internal_date_ms / 1000, tz=UTC)
            if internal_date_ms
            else datetime.now(UTC)
        )
        body_text = self._extract_body(payload.get("payload", {})) or payload.get(
            "snippet", ""
        )
        message_id = payload.get("id", "")
        return SyncedReplyMessage(
            provider_message_id=message_id,
            provider_thread_id=payload.get("threadId"),
            from_email=from_email,
            from_name=from_name,
            to_email=headers.get("to"),
            subject=headers.get("subject"),
            body_text=body_text,
            received_at=received_at,
            provider_message_url=self.get_reply_provider_message_url(message_id),
        )

    @staticmethod
    def _split_from_header(value: str) -> tuple[str | None, str]:
        if "<" in value and ">" in value:
            name_part, email_part = value.split("<", 1)
            return name_part.strip(' "') or None, email_part.split(">")[0].strip()
        return None, value.strip()

    @staticmethod
    def _extract_body(payload: dict) -> str:
        if payload.get("mimeType") == "text/plain" and "data" in payload.get(
            "body", {}
        ):
            data = payload["body"]["data"]
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
        for part in payload.get("parts", []) or []:
            found = GmailReplyTrackingProvider._extract_body(part)
            if found:
                return found
        return ""

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
                    f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{provider_thread_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
            except httpx.TimeoutException as exc:
                raise ReplyTrackingTimeoutError(
                    "Timed out reading a Gmail thread."
                ) from exc
            except httpx.HTTPError as exc:
                raise ReplyTrackingConnectionError(
                    "Could not reach Gmail to read a thread."
                ) from exc

        self._raise_for_status(response, "read thread")
        return [
            self._parse_message(message)
            for message in response.json().get("messages", [])
        ]

    def get_reply_provider_message_url(self, provider_message_id: str) -> str | None:
        return f"https://mail.google.com/mail/u/0/#all/{provider_message_id}"

    @staticmethod
    def _raise_for_status(response: httpx.Response, action: str) -> None:
        if response.status_code == 401:
            raise ReplyTrackingAuthError(
                "Gmail access token was rejected; reconnect Gmail."
            )
        if response.status_code == 403:
            raise ReplyTrackingPermissionError(
                "Gmail refused this request — the connected account may be "
                "missing read permission."
            )
        if response.status_code == 429:
            raise ReplyTrackingRateLimitError(
                "Gmail's rate limit was exceeded. Try again later."
            )
        if response.status_code >= 400:
            logger.warning(
                "gmail %s failed with status %s", action, response.status_code
            )
            raise ReplyTrackingProviderError(
                f"Gmail returned an error (status {response.status_code})."
            )
