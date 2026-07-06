from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from backend.domain.entities.email_draft import EmailDraft
from backend.domain.enums import EmailDraftReviewStatus
from backend.domain.repositories.email_draft_repository import EmailDraftRepository
from backend.infrastructure.database.models.email_draft import EmailDraftModel
from backend.infrastructure.repositories.base import SQLAlchemyRepository


class SQLAlchemyEmailDraftRepository(
    SQLAlchemyRepository[EmailDraftModel, EmailDraft], EmailDraftRepository
):
    """SQLAlchemy-backed :class:`EmailDraftRepository`."""

    model = EmailDraftModel

    def _to_entity(self, orm_obj: EmailDraftModel) -> EmailDraft:
        return EmailDraft(
            id=orm_obj.id,
            company_id=orm_obj.company_id,
            lead_id=orm_obj.lead_id,
            workflow_run_id=orm_obj.workflow_run_id,
            subject_lines=orm_obj.subject_lines,
            email_body=orm_obj.email_body,
            status=orm_obj.status,
            review_status=orm_obj.review_status,
            reviewer_name=orm_obj.reviewer_name,
            review_comment=orm_obj.review_comment,
            reviewed_at=orm_obj.reviewed_at,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )

    def _to_orm(self, entity: EmailDraft) -> EmailDraftModel:
        return EmailDraftModel(
            company_id=entity.company_id,
            lead_id=entity.lead_id,
            workflow_run_id=entity.workflow_run_id,
            subject_lines=entity.subject_lines,
            email_body=entity.email_body,
            status=entity.status,
            review_status=entity.review_status,
            reviewer_name=entity.reviewer_name,
            review_comment=entity.review_comment,
            reviewed_at=entity.reviewed_at,
        )

    def _apply(self, orm_obj: EmailDraftModel, entity: EmailDraft) -> None:
        orm_obj.lead_id = entity.lead_id
        orm_obj.workflow_run_id = entity.workflow_run_id
        orm_obj.subject_lines = entity.subject_lines
        orm_obj.email_body = entity.email_body
        orm_obj.status = entity.status
        orm_obj.review_status = entity.review_status
        orm_obj.reviewer_name = entity.reviewer_name
        orm_obj.review_comment = entity.review_comment
        orm_obj.reviewed_at = entity.reviewed_at

    async def list_by_company(
        self, company_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[EmailDraft]:
        stmt = (
            select(EmailDraftModel)
            .where(EmailDraftModel.company_id == company_id)
            .order_by(EmailDraftModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def update_review_status(
        self,
        email_draft_id: UUID,
        review_status: EmailDraftReviewStatus,
        reviewer_name: str | None = None,
        comment: str | None = None,
    ) -> EmailDraft | None:
        orm_obj = await self._session.get(EmailDraftModel, email_draft_id)
        if orm_obj is None:
            return None
        orm_obj.review_status = review_status
        orm_obj.reviewer_name = reviewer_name
        orm_obj.review_comment = comment
        orm_obj.reviewed_at = datetime.now(timezone.utc)
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)
