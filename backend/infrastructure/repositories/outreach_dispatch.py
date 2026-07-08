from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.entities.outreach_dispatch import OutreachDispatch
from backend.domain.repositories.outreach_dispatch_repository import (
    OutreachDispatchRepository,
)
from backend.infrastructure.database.models.outreach_dispatch import (
    OutreachDispatchModel,
)

_TERMINAL_STATUSES = ("cancelled", "failed", "archived")


class SQLAlchemyOutreachDispatchRepository(OutreachDispatchRepository):
    """SQLAlchemy-backed :class:`OutreachDispatchRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, dispatch: OutreachDispatch) -> OutreachDispatch:
        orm_obj = OutreachDispatchModel(
            queue_item_id=dispatch.queue_item_id,
            outreach_campaign_id=dispatch.outreach_campaign_id,
            lead_id=dispatch.lead_id,
            company_id=dispatch.company_id,
            email_draft_id=dispatch.email_draft_id,
            external_draft_id=dispatch.external_draft_id,
            review_id=dispatch.review_id,
            provider=dispatch.provider,
            dispatch_mode=dispatch.dispatch_mode,
            dispatch_status=dispatch.dispatch_status,
            recipient_email=dispatch.recipient_email,
            subject_snapshot=dispatch.subject_snapshot,
            body_preview_snapshot=dispatch.body_preview_snapshot,
            final_confirmation_by_user_id=dispatch.final_confirmation_by_user_id,
            final_confirmation_at=dispatch.final_confirmation_at,
            compliance_acknowledged_by_user_id=dispatch.compliance_acknowledged_by_user_id,
            compliance_acknowledged_at=dispatch.compliance_acknowledged_at,
            do_not_contact_checked_at=dispatch.do_not_contact_checked_at,
            human_review_checked_at=dispatch.human_review_checked_at,
            provider_message_id=dispatch.provider_message_id,
            provider_draft_id=dispatch.provider_draft_id,
            provider_url=dispatch.provider_url,
            last_error=dispatch.last_error,
            created_by_user_id=dispatch.created_by_user_id,
        )
        self._session.add(orm_obj)
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def get_by_id(self, dispatch_id: UUID) -> OutreachDispatch | None:
        orm_obj = await self._session.get(OutreachDispatchModel, dispatch_id)
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        queue_item_id: UUID | None = None,
        dispatch_status: str | None = None,
    ) -> list[OutreachDispatch]:
        stmt = select(OutreachDispatchModel)
        if queue_item_id is not None:
            stmt = stmt.where(OutreachDispatchModel.queue_item_id == queue_item_id)
        if dispatch_status is not None:
            stmt = stmt.where(OutreachDispatchModel.dispatch_status == dispatch_status)
        stmt = (
            stmt.order_by(OutreachDispatchModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def update(self, dispatch: OutreachDispatch) -> OutreachDispatch | None:
        orm_obj = await self._session.get(OutreachDispatchModel, dispatch.id)
        if orm_obj is None:
            return None
        orm_obj.email_draft_id = dispatch.email_draft_id
        orm_obj.external_draft_id = dispatch.external_draft_id
        orm_obj.review_id = dispatch.review_id
        orm_obj.provider = dispatch.provider
        orm_obj.dispatch_mode = dispatch.dispatch_mode
        orm_obj.dispatch_status = dispatch.dispatch_status
        orm_obj.recipient_email = dispatch.recipient_email
        orm_obj.subject_snapshot = dispatch.subject_snapshot
        orm_obj.body_preview_snapshot = dispatch.body_preview_snapshot
        orm_obj.final_confirmation_by_user_id = dispatch.final_confirmation_by_user_id
        orm_obj.final_confirmation_at = dispatch.final_confirmation_at
        orm_obj.compliance_acknowledged_by_user_id = (
            dispatch.compliance_acknowledged_by_user_id
        )
        orm_obj.compliance_acknowledged_at = dispatch.compliance_acknowledged_at
        orm_obj.do_not_contact_checked_at = dispatch.do_not_contact_checked_at
        orm_obj.human_review_checked_at = dispatch.human_review_checked_at
        orm_obj.provider_message_id = dispatch.provider_message_id
        orm_obj.provider_draft_id = dispatch.provider_draft_id
        orm_obj.provider_url = dispatch.provider_url
        orm_obj.last_error = dispatch.last_error
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def find_active_for_queue_item(
        self, queue_item_id: UUID
    ) -> OutreachDispatch | None:
        stmt = (
            select(OutreachDispatchModel)
            .where(OutreachDispatchModel.queue_item_id == queue_item_id)
            .where(OutreachDispatchModel.dispatch_status.notin_(_TERMINAL_STATUSES))
            .order_by(OutreachDispatchModel.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        orm_obj = result.scalars().first()
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def count_since(
        self, created_by_user_id: UUID | None, since: datetime
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(OutreachDispatchModel)
            .where(OutreachDispatchModel.created_at >= since)
            .where(OutreachDispatchModel.dispatch_status.notin_(("cancelled", "failed")))
        )
        if created_by_user_id is not None:
            stmt = stmt.where(
                OutreachDispatchModel.created_by_user_id == created_by_user_id
            )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    @staticmethod
    def _to_entity(orm_obj: OutreachDispatchModel) -> OutreachDispatch:
        return OutreachDispatch(
            id=orm_obj.id,
            queue_item_id=orm_obj.queue_item_id,
            outreach_campaign_id=orm_obj.outreach_campaign_id,
            lead_id=orm_obj.lead_id,
            company_id=orm_obj.company_id,
            email_draft_id=orm_obj.email_draft_id,
            external_draft_id=orm_obj.external_draft_id,
            review_id=orm_obj.review_id,
            provider=orm_obj.provider,
            dispatch_mode=orm_obj.dispatch_mode,
            dispatch_status=orm_obj.dispatch_status,
            recipient_email=orm_obj.recipient_email,
            subject_snapshot=orm_obj.subject_snapshot,
            body_preview_snapshot=orm_obj.body_preview_snapshot,
            final_confirmation_by_user_id=orm_obj.final_confirmation_by_user_id,
            final_confirmation_at=orm_obj.final_confirmation_at,
            compliance_acknowledged_by_user_id=orm_obj.compliance_acknowledged_by_user_id,
            compliance_acknowledged_at=orm_obj.compliance_acknowledged_at,
            do_not_contact_checked_at=orm_obj.do_not_contact_checked_at,
            human_review_checked_at=orm_obj.human_review_checked_at,
            provider_message_id=orm_obj.provider_message_id,
            provider_draft_id=orm_obj.provider_draft_id,
            provider_url=orm_obj.provider_url,
            last_error=orm_obj.last_error,
            created_by_user_id=orm_obj.created_by_user_id,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )
