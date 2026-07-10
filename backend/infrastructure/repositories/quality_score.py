from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.entities.quality_score import QualityScore
from backend.domain.repositories.quality_score_repository import (
    QualityScoreRepository,
)
from backend.infrastructure.database.models.quality_score import QualityScoreModel


class SQLAlchemyQualityScoreRepository(QualityScoreRepository):
    """SQLAlchemy-backed :class:`QualityScoreRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, score: QualityScore) -> QualityScore:
        orm_obj = QualityScoreModel(
            entity_type=score.entity_type,
            entity_id=score.entity_id,
            score_total=score.score_total,
            score_level=score.score_level,
            score_breakdown=score.score_breakdown,
            strengths=score.strengths,
            weaknesses=score.weaknesses,
            warnings=score.warnings,
            recommended_improvements=score.recommended_improvements,
            compliance_flags=score.compliance_flags,
            evaluated_by=score.evaluated_by,
            evaluated_by_user_id=score.evaluated_by_user_id,
            provider=score.provider,
            workflow_run_id=score.workflow_run_id,
            email_draft_id=score.email_draft_id,
            lead_id=score.lead_id,
            company_id=score.company_id,
            lead_candidate_id=score.lead_candidate_id,
            qualification_result_id=score.qualification_result_id,
            outreach_queue_item_id=score.outreach_queue_item_id,
            reply_id=score.reply_id,
        )
        self._session.add(orm_obj)
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def get_by_id(self, score_id: UUID) -> QualityScore | None:
        orm_obj = await self._session.get(QualityScoreModel, score_id)
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def update(self, score: QualityScore) -> QualityScore | None:
        orm_obj = await self._session.get(QualityScoreModel, score.id)
        if orm_obj is None:
            return None
        orm_obj.score_total = score.score_total
        orm_obj.score_level = score.score_level
        orm_obj.score_breakdown = score.score_breakdown
        orm_obj.strengths = score.strengths
        orm_obj.weaknesses = score.weaknesses
        orm_obj.warnings = score.warnings
        orm_obj.recommended_improvements = score.recommended_improvements
        orm_obj.compliance_flags = score.compliance_flags
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def find_latest_for_entity(
        self, entity_type: str, entity_id: UUID
    ) -> QualityScore | None:
        stmt = (
            select(QualityScoreModel)
            .where(
                QualityScoreModel.entity_type == entity_type,
                QualityScoreModel.entity_id == entity_id,
            )
            .order_by(QualityScoreModel.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        orm_obj = result.scalars().first()
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def list_for_entity(
        self, entity_type: str, entity_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[QualityScore]:
        stmt = (
            select(QualityScoreModel)
            .where(
                QualityScoreModel.entity_type == entity_type,
                QualityScoreModel.entity_id == entity_id,
            )
            .order_by(QualityScoreModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        entity_type: str | None = None,
        score_level: str | None = None,
    ) -> list[QualityScore]:
        stmt = select(QualityScoreModel)
        if entity_type is not None:
            stmt = stmt.where(QualityScoreModel.entity_type == entity_type)
        if score_level is not None:
            stmt = stmt.where(QualityScoreModel.score_level == score_level)
        stmt = stmt.order_by(QualityScoreModel.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def list_all_latest(
        self, entity_type: str | None = None, limit: int = 1000
    ) -> list[QualityScore]:
        # Simple, correct-but-not-maximally-efficient approach: fetch a
        # generous newest-first page and keep only the first occurrence
        # per (entity_type, entity_id) — adequate at this project's scale
        # (see CUSTOMER_READINESS.md "Known Limitations").
        stmt = select(QualityScoreModel).order_by(QualityScoreModel.created_at.desc())
        if entity_type is not None:
            stmt = stmt.where(QualityScoreModel.entity_type == entity_type)
        stmt = stmt.limit(limit)
        result = await self._session.execute(stmt)
        seen: set[tuple[str, UUID]] = set()
        latest: list[QualityScore] = []
        for row in result.scalars().all():
            key = (row.entity_type, row.entity_id)
            if key in seen:
                continue
            seen.add(key)
            latest.append(self._to_entity(row))
        return latest

    @staticmethod
    def _to_entity(orm_obj: QualityScoreModel) -> QualityScore:
        return QualityScore(
            id=orm_obj.id,
            entity_type=orm_obj.entity_type,
            entity_id=orm_obj.entity_id,
            score_total=orm_obj.score_total,
            score_level=orm_obj.score_level,
            score_breakdown=orm_obj.score_breakdown,
            strengths=orm_obj.strengths,
            weaknesses=orm_obj.weaknesses,
            warnings=orm_obj.warnings,
            recommended_improvements=orm_obj.recommended_improvements,
            compliance_flags=orm_obj.compliance_flags,
            evaluated_by=orm_obj.evaluated_by,
            evaluated_by_user_id=orm_obj.evaluated_by_user_id,
            provider=orm_obj.provider,
            workflow_run_id=orm_obj.workflow_run_id,
            email_draft_id=orm_obj.email_draft_id,
            lead_id=orm_obj.lead_id,
            company_id=orm_obj.company_id,
            lead_candidate_id=orm_obj.lead_candidate_id,
            qualification_result_id=orm_obj.qualification_result_id,
            outreach_queue_item_id=orm_obj.outreach_queue_item_id,
            reply_id=orm_obj.reply_id,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )
