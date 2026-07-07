from uuid import UUID

from sqlalchemy import select

from backend.domain.entities.reply import Reply
from backend.domain.enums import EmailProviderType, ReplyCategory, ReplySentiment
from backend.domain.repositories.reply_repository import ReplyRepository
from backend.infrastructure.database.models.reply import ReplyModel
from backend.infrastructure.repositories.base import SQLAlchemyRepository


class SQLAlchemyReplyRepository(
    SQLAlchemyRepository[ReplyModel, Reply], ReplyRepository
):
    """SQLAlchemy-backed :class:`ReplyRepository`."""

    model = ReplyModel

    def _to_entity(self, orm_obj: ReplyModel) -> Reply:
        return Reply(
            id=orm_obj.id,
            lead_id=orm_obj.lead_id,
            company_id=orm_obj.company_id,
            email_draft_id=orm_obj.email_draft_id,
            external_draft_id=orm_obj.external_draft_id,
            provider=orm_obj.provider,
            provider_message_id=orm_obj.provider_message_id,
            provider_thread_id=orm_obj.provider_thread_id,
            provider_message_url=orm_obj.provider_message_url,
            from_email=orm_obj.from_email,
            from_name=orm_obj.from_name,
            to_email=orm_obj.to_email,
            subject=orm_obj.subject,
            body_preview=orm_obj.body_preview,
            body_text=orm_obj.body_text,
            received_at=orm_obj.received_at,
            detected_intent=orm_obj.detected_intent,
            sentiment=orm_obj.sentiment,
            reply_category=orm_obj.reply_category,
            confidence_score=orm_obj.confidence_score,
            is_read=orm_obj.is_read,
            is_archived=orm_obj.is_archived,
            last_error=orm_obj.last_error,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )

    def _to_orm(self, entity: Reply) -> ReplyModel:
        return ReplyModel(
            lead_id=entity.lead_id,
            company_id=entity.company_id,
            email_draft_id=entity.email_draft_id,
            external_draft_id=entity.external_draft_id,
            provider=entity.provider,
            provider_message_id=entity.provider_message_id,
            provider_thread_id=entity.provider_thread_id,
            provider_message_url=entity.provider_message_url,
            from_email=entity.from_email,
            from_name=entity.from_name,
            to_email=entity.to_email,
            subject=entity.subject,
            body_preview=entity.body_preview,
            body_text=entity.body_text,
            received_at=entity.received_at,
            detected_intent=entity.detected_intent,
            sentiment=entity.sentiment,
            reply_category=entity.reply_category,
            confidence_score=entity.confidence_score,
            is_read=entity.is_read,
            is_archived=entity.is_archived,
            last_error=entity.last_error,
        )

    def _apply(self, orm_obj: ReplyModel, entity: Reply) -> None:
        orm_obj.lead_id = entity.lead_id
        orm_obj.company_id = entity.company_id
        orm_obj.email_draft_id = entity.email_draft_id
        orm_obj.external_draft_id = entity.external_draft_id
        orm_obj.detected_intent = entity.detected_intent
        orm_obj.sentiment = entity.sentiment
        orm_obj.reply_category = entity.reply_category
        orm_obj.confidence_score = entity.confidence_score
        orm_obj.is_read = entity.is_read
        orm_obj.is_archived = entity.is_archived
        orm_obj.last_error = entity.last_error

    async def get_by_provider_message_id(
        self, provider: EmailProviderType, provider_message_id: str
    ) -> Reply | None:
        stmt = select(ReplyModel).where(
            ReplyModel.provider == provider,
            ReplyModel.provider_message_id == provider_message_id,
        )
        result = await self._session.execute(stmt)
        orm_obj = result.scalars().first()
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def list_by_lead(
        self, lead_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[Reply]:
        stmt = (
            select(ReplyModel)
            .where(ReplyModel.lead_id == lead_id)
            .order_by(ReplyModel.received_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def list_by_email_draft(
        self, email_draft_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[Reply]:
        stmt = (
            select(ReplyModel)
            .where(ReplyModel.email_draft_id == email_draft_id)
            .order_by(ReplyModel.received_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def list_filtered(
        self,
        *,
        category: ReplyCategory | None = None,
        sentiment: ReplySentiment | None = None,
        is_read: bool | None = None,
        is_archived: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Reply]:
        stmt = select(ReplyModel)
        if category is not None:
            stmt = stmt.where(ReplyModel.reply_category == category)
        if sentiment is not None:
            stmt = stmt.where(ReplyModel.sentiment == sentiment)
        if is_read is not None:
            stmt = stmt.where(ReplyModel.is_read == is_read)
        if is_archived is not None:
            stmt = stmt.where(ReplyModel.is_archived == is_archived)
        stmt = stmt.order_by(ReplyModel.received_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def mark_read(self, reply_id: UUID, is_read: bool = True) -> Reply | None:
        orm_obj = await self._session.get(self.model, reply_id)
        if orm_obj is None:
            return None
        orm_obj.is_read = is_read
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def archive(self, reply_id: UUID, is_archived: bool = True) -> Reply | None:
        orm_obj = await self._session.get(self.model, reply_id)
        if orm_obj is None:
            return None
        orm_obj.is_archived = is_archived
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)
