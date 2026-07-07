"""Reply Inbox: list, inspect, mark read/archived, and sync replies read
from Gmail/Outlook/Mock.

No endpoint here — or anywhere in this integration — can send a reply or
any other email. Every endpoint either reads stored replies, changes their
read/archived flag, or triggers a read-only sync from the configured
provider.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from backend.api.dependencies.auth import (
    RequireSalesOrAdminDep,
    RequireSalesReviewerOrAdminDep,
)
from backend.api.v1.dependencies import ReplyTrackingServiceDep
from backend.application.integrations.reply_schemas import (
    ReplyListResponse,
    ReplyResponse,
    SyncRepliesResponse,
)
from backend.domain.enums import ReplyCategory, ReplySentiment
from backend.domain.exceptions import ReplyNotFoundError

router = APIRouter(prefix="/replies", tags=["replies"])


@router.get("", response_model=ReplyListResponse)
async def list_replies(
    service: ReplyTrackingServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
    category: ReplyCategory | None = Query(default=None),
    sentiment: ReplySentiment | None = Query(default=None),
    is_read: bool | None = Query(default=None),
    is_archived: bool | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> ReplyListResponse:
    """List replies, newest first, optionally filtered.

    Read-only, any active admin, sales, or reviewer account.
    """
    return await service.list_replies(
        category=category,
        sentiment=sentiment,
        is_read=is_read,
        is_archived=is_archived,
        limit=limit,
        offset=offset,
    )


@router.get("/{reply_id}", response_model=ReplyResponse)
async def get_reply(
    reply_id: UUID,
    service: ReplyTrackingServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> ReplyResponse:
    """Return a single reply. Read-only, any active admin, sales, or
    reviewer account."""
    try:
        return await service.get_reply(reply_id)
    except ReplyNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{reply_id}/read", response_model=ReplyResponse)
async def mark_reply_read(
    reply_id: UUID,
    service: ReplyTrackingServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
    is_read: bool = Query(default=True),
) -> ReplyResponse:
    """Set a reply's read flag. Any active admin, sales, or reviewer
    account. Bookkeeping only — never sends anything."""
    try:
        return await service.mark_read(reply_id, is_read)
    except ReplyNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{reply_id}/archive", response_model=ReplyResponse)
async def archive_reply(
    reply_id: UUID,
    service: ReplyTrackingServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
    is_archived: bool = Query(default=True),
) -> ReplyResponse:
    """Set a reply's archived flag. Any active admin, sales, or reviewer
    account. Bookkeeping only — never sends anything."""
    try:
        return await service.archive_reply(reply_id, is_archived)
    except ReplyNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/sync-recent", response_model=SyncRepliesResponse)
async def sync_recent_replies(
    service: ReplyTrackingServiceDep,
    current_user: RequireSalesOrAdminDep,
) -> SyncRepliesResponse:
    """Sync recent replies across known lead/contact emails.

    Requires an active admin or sales account — reviewer accounts may view
    replies but not trigger a sync. Only ever reads messages that already
    exist in the connected mailbox (Mock by default); never sends anything.
    """
    return await service.sync_recent_replies(current_user.id)
