"""Signed ``state`` parameter for OAuth authorization requests.

The OAuth callback is a plain browser redirect (Google/Microsoft send the
user's browser straight to our callback URL) — it cannot carry an
``Authorization: Bearer`` header, so it must recover *which user* is
completing the flow from the ``state`` value instead. Reuses this
project's existing JWT signing (``backend.shared.security``) rather than
introducing a second signing mechanism.
"""

from __future__ import annotations

import json
from datetime import timedelta
from uuid import UUID

from backend.domain.enums import EmailProviderType
from backend.infrastructure.email_integration.base import EmailIntegrationConfigError
from backend.shared.security import InvalidTokenError, create_access_token, decode_access_token

_STATE_TTL = timedelta(minutes=10)


def create_oauth_state(user_id: UUID, provider: EmailProviderType) -> str:
    """Create a short-lived, signed state token binding this OAuth
    authorization attempt to ``user_id`` and ``provider``."""
    payload = json.dumps({"user_id": str(user_id), "provider": provider.value})
    return create_access_token(subject=payload, expires_delta=_STATE_TTL)


def parse_oauth_state(state: str) -> tuple[UUID, EmailProviderType]:
    """Recover ``(user_id, provider)`` from a state token created by
    :func:`create_oauth_state`.

    Raises :class:`EmailIntegrationConfigError` if the state is missing,
    expired, malformed, or was signed for a different provider.
    """
    try:
        claims = decode_access_token(state)
        data = json.loads(claims["sub"])
        return UUID(data["user_id"]), EmailProviderType(data["provider"])
    except (InvalidTokenError, KeyError, ValueError, json.JSONDecodeError) as exc:
        raise EmailIntegrationConfigError(
            "OAuth state is invalid or expired; please restart the "
            "connection process."
        ) from exc
