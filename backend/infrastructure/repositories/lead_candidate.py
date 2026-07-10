from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.entities.lead_candidate import LeadCandidate
from backend.domain.repositories.lead_candidate_repository import (
    LeadCandidateRepository,
)
from backend.infrastructure.database.models.lead_candidate import LeadCandidateModel


class SQLAlchemyLeadCandidateRepository(LeadCandidateRepository):
    """SQLAlchemy-backed :class:`LeadCandidateRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, candidate: LeadCandidate) -> LeadCandidate:
        orm_obj = LeadCandidateModel(
            sourcing_run_id=candidate.sourcing_run_id,
            campaign_id=candidate.campaign_id,
            company_name=candidate.company_name,
            company_domain=candidate.company_domain,
            company_website_url=candidate.company_website_url,
            industry=candidate.industry,
            location=candidate.location,
            description=candidate.description,
            source_url=candidate.source_url,
            source_name=candidate.source_name,
            source_type=candidate.source_type,
            public_contact_email=candidate.public_contact_email,
            contact_page_url=candidate.contact_page_url,
            confidence_score=candidate.confidence_score,
            icp_fit_score=candidate.icp_fit_score,
            icp_fit_level=candidate.icp_fit_level,
            matched_signals=candidate.matched_signals,
            negative_signals=candidate.negative_signals,
            website_quality_level=candidate.website_quality_level,
            website_quality_reasons=candidate.website_quality_reasons,
            do_not_contact_status=candidate.do_not_contact_status,
            duplicate_status=candidate.duplicate_status,
            review_status=candidate.review_status,
            crm_company_id=candidate.crm_company_id,
            crm_lead_id=candidate.crm_lead_id,
            notes=candidate.notes,
            warnings=candidate.warnings,
        )
        self._session.add(orm_obj)
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def get_by_id(self, candidate_id: UUID) -> LeadCandidate | None:
        orm_obj = await self._session.get(LeadCandidateModel, candidate_id)
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        campaign_id: UUID | None = None,
        sourcing_run_id: UUID | None = None,
        review_status: str | None = None,
    ) -> list[LeadCandidate]:
        stmt = select(LeadCandidateModel)
        if campaign_id is not None:
            stmt = stmt.where(LeadCandidateModel.campaign_id == campaign_id)
        if sourcing_run_id is not None:
            stmt = stmt.where(LeadCandidateModel.sourcing_run_id == sourcing_run_id)
        if review_status is not None:
            stmt = stmt.where(LeadCandidateModel.review_status == review_status)
        stmt = (
            stmt.order_by(LeadCandidateModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def update(self, candidate: LeadCandidate) -> LeadCandidate | None:
        orm_obj = await self._session.get(LeadCandidateModel, candidate.id)
        if orm_obj is None:
            return None
        orm_obj.company_name = candidate.company_name
        orm_obj.company_domain = candidate.company_domain
        orm_obj.company_website_url = candidate.company_website_url
        orm_obj.industry = candidate.industry
        orm_obj.location = candidate.location
        orm_obj.description = candidate.description
        orm_obj.source_url = candidate.source_url
        orm_obj.source_name = candidate.source_name
        orm_obj.source_type = candidate.source_type
        orm_obj.public_contact_email = candidate.public_contact_email
        orm_obj.contact_page_url = candidate.contact_page_url
        orm_obj.confidence_score = candidate.confidence_score
        orm_obj.icp_fit_score = candidate.icp_fit_score
        orm_obj.icp_fit_level = candidate.icp_fit_level
        orm_obj.matched_signals = candidate.matched_signals
        orm_obj.negative_signals = candidate.negative_signals
        orm_obj.website_quality_level = candidate.website_quality_level
        orm_obj.website_quality_reasons = candidate.website_quality_reasons
        orm_obj.do_not_contact_status = candidate.do_not_contact_status
        orm_obj.duplicate_status = candidate.duplicate_status
        orm_obj.review_status = candidate.review_status
        orm_obj.crm_company_id = candidate.crm_company_id
        orm_obj.crm_lead_id = candidate.crm_lead_id
        orm_obj.notes = candidate.notes
        orm_obj.warnings = candidate.warnings
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def find_existing(
        self, *, company_domain: str | None, company_name: str | None
    ) -> LeadCandidate | None:
        if company_domain:
            stmt = select(LeadCandidateModel).where(
                func.lower(LeadCandidateModel.company_domain) == company_domain.lower()
            )
            result = await self._session.execute(stmt)
            orm_obj = result.scalars().first()
            if orm_obj is not None:
                return self._to_entity(orm_obj)
        if company_name:
            stmt = select(LeadCandidateModel).where(
                func.lower(LeadCandidateModel.company_name) == company_name.lower()
            )
            result = await self._session.execute(stmt)
            orm_obj = result.scalars().first()
            if orm_obj is not None:
                return self._to_entity(orm_obj)
        return None

    @staticmethod
    def _to_entity(orm_obj: LeadCandidateModel) -> LeadCandidate:
        return LeadCandidate(
            id=orm_obj.id,
            sourcing_run_id=orm_obj.sourcing_run_id,
            campaign_id=orm_obj.campaign_id,
            company_name=orm_obj.company_name,
            company_domain=orm_obj.company_domain,
            company_website_url=orm_obj.company_website_url,
            industry=orm_obj.industry,
            location=orm_obj.location,
            description=orm_obj.description,
            source_url=orm_obj.source_url,
            source_name=orm_obj.source_name,
            source_type=orm_obj.source_type,
            public_contact_email=orm_obj.public_contact_email,
            contact_page_url=orm_obj.contact_page_url,
            confidence_score=orm_obj.confidence_score,
            icp_fit_score=orm_obj.icp_fit_score,
            icp_fit_level=orm_obj.icp_fit_level,
            matched_signals=orm_obj.matched_signals,
            negative_signals=orm_obj.negative_signals,
            website_quality_level=orm_obj.website_quality_level,
            website_quality_reasons=orm_obj.website_quality_reasons,
            do_not_contact_status=orm_obj.do_not_contact_status,
            duplicate_status=orm_obj.duplicate_status,
            review_status=orm_obj.review_status,
            crm_company_id=orm_obj.crm_company_id,
            crm_lead_id=orm_obj.crm_lead_id,
            notes=orm_obj.notes,
            warnings=orm_obj.warnings,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )
