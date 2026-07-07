from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.entities.qualification_result import QualificationResult
from backend.domain.repositories.qualification_result_repository import (
    QualificationResultRepository,
)
from backend.infrastructure.database.models.qualification_result import (
    QualificationResultModel,
)


class SQLAlchemyQualificationResultRepository(QualificationResultRepository):
    """SQLAlchemy-backed :class:`QualificationResultRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, result: QualificationResult) -> QualificationResult:
        orm_obj = QualificationResultModel(
            qualification_run_id=result.qualification_run_id,
            lead_candidate_id=result.lead_candidate_id,
            lead_id=result.lead_id,
            company_id=result.company_id,
            icp_profile_id=result.icp_profile_id,
            offer_profile_id=result.offer_profile_id,
            qualification_score=result.qualification_score,
            qualification_level=result.qualification_level,
            qualification_status=result.qualification_status,
            priority_rank=result.priority_rank,
            fit_summary=result.fit_summary,
            score_breakdown=result.score_breakdown,
            positive_signals=result.positive_signals,
            negative_signals=result.negative_signals,
            missing_data=result.missing_data,
            recommended_next_action=result.recommended_next_action,
            recommended_outreach_angle=result.recommended_outreach_angle,
            disqualification_reason=result.disqualification_reason,
            compliance_status=result.compliance_status,
            do_not_contact_status=result.do_not_contact_status,
            duplicate_status=result.duplicate_status,
            pipeline_status=result.pipeline_status,
            confidence_score=result.confidence_score,
            reviewed_by_user_id=result.reviewed_by_user_id,
            reviewed_at=result.reviewed_at,
        )
        self._session.add(orm_obj)
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def get_by_id(self, result_id: UUID) -> QualificationResult | None:
        orm_obj = await self._session.get(QualificationResultModel, result_id)
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        qualification_run_id: UUID | None = None,
        qualification_status: str | None = None,
    ) -> list[QualificationResult]:
        stmt = select(QualificationResultModel)
        if qualification_run_id is not None:
            stmt = stmt.where(
                QualificationResultModel.qualification_run_id == qualification_run_id
            )
        if qualification_status is not None:
            stmt = stmt.where(
                QualificationResultModel.qualification_status == qualification_status
            )
        stmt = (
            stmt.order_by(QualificationResultModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def update(self, result: QualificationResult) -> QualificationResult | None:
        orm_obj = await self._session.get(QualificationResultModel, result.id)
        if orm_obj is None:
            return None
        orm_obj.qualification_score = result.qualification_score
        orm_obj.qualification_level = result.qualification_level
        orm_obj.qualification_status = result.qualification_status
        orm_obj.priority_rank = result.priority_rank
        orm_obj.fit_summary = result.fit_summary
        orm_obj.score_breakdown = result.score_breakdown
        orm_obj.positive_signals = result.positive_signals
        orm_obj.negative_signals = result.negative_signals
        orm_obj.missing_data = result.missing_data
        orm_obj.recommended_next_action = result.recommended_next_action
        orm_obj.recommended_outreach_angle = result.recommended_outreach_angle
        orm_obj.disqualification_reason = result.disqualification_reason
        orm_obj.compliance_status = result.compliance_status
        orm_obj.do_not_contact_status = result.do_not_contact_status
        orm_obj.duplicate_status = result.duplicate_status
        orm_obj.pipeline_status = result.pipeline_status
        orm_obj.confidence_score = result.confidence_score
        orm_obj.reviewed_by_user_id = result.reviewed_by_user_id
        orm_obj.reviewed_at = result.reviewed_at
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def find_latest_for_candidate(
        self, lead_candidate_id: UUID
    ) -> QualificationResult | None:
        stmt = (
            select(QualificationResultModel)
            .where(QualificationResultModel.lead_candidate_id == lead_candidate_id)
            .order_by(QualificationResultModel.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        orm_obj = result.scalars().first()
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def find_latest_for_lead(self, lead_id: UUID) -> QualificationResult | None:
        stmt = (
            select(QualificationResultModel)
            .where(QualificationResultModel.lead_id == lead_id)
            .order_by(QualificationResultModel.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        orm_obj = result.scalars().first()
        return self._to_entity(orm_obj) if orm_obj is not None else None

    @staticmethod
    def _to_entity(orm_obj: QualificationResultModel) -> QualificationResult:
        return QualificationResult(
            id=orm_obj.id,
            qualification_run_id=orm_obj.qualification_run_id,
            lead_candidate_id=orm_obj.lead_candidate_id,
            lead_id=orm_obj.lead_id,
            company_id=orm_obj.company_id,
            icp_profile_id=orm_obj.icp_profile_id,
            offer_profile_id=orm_obj.offer_profile_id,
            qualification_score=orm_obj.qualification_score,
            qualification_level=orm_obj.qualification_level,
            qualification_status=orm_obj.qualification_status,
            priority_rank=orm_obj.priority_rank,
            fit_summary=orm_obj.fit_summary,
            score_breakdown=orm_obj.score_breakdown,
            positive_signals=orm_obj.positive_signals,
            negative_signals=orm_obj.negative_signals,
            missing_data=orm_obj.missing_data,
            recommended_next_action=orm_obj.recommended_next_action,
            recommended_outreach_angle=orm_obj.recommended_outreach_angle,
            disqualification_reason=orm_obj.disqualification_reason,
            compliance_status=orm_obj.compliance_status,
            do_not_contact_status=orm_obj.do_not_contact_status,
            duplicate_status=orm_obj.duplicate_status,
            pipeline_status=orm_obj.pipeline_status,
            confidence_score=orm_obj.confidence_score,
            reviewed_by_user_id=orm_obj.reviewed_by_user_id,
            reviewed_at=orm_obj.reviewed_at,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )
