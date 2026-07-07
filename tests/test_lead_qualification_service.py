"""Tests for the Lead Qualification & Scoring engine.

Covers: status, run start (including dry-run), single-item qualify for
both Lead Candidates and CRM Leads, ICP-fit-driven scoring, negative
signal penalties, do-not-contact blocking, duplicate detection, priority/
disqualify thresholds, missing-data warnings, the safe-mode LLM advisor,
result persistence, the dashboard, and manual review.
"""

import uuid

import pytest

from backend.application.compliance.schemas import CreateDoNotContactRequest
from backend.application.lead_qualification.qualification_scoring_service import (
    QualificationInput,
    QualificationScoringService,
)
from backend.application.lead_qualification.schemas import (
    QualificationReviewRequest,
    QualifyCRMLeadRequest,
    QualifyLeadCandidateRequest,
    StartLeadQualificationRequest,
)
from backend.application.lead_sourcing.schemas import (
    CreateLeadSourcingCampaignRequest,
    StartLeadSourcingRunRequest,
)
from backend.domain.entities.company import Company
from backend.domain.entities.icp_profile import ICPProfile
from backend.domain.entities.lead import Lead
from backend.domain.enums import LeadSource, PipelineStatus
from backend.domain.exceptions import (
    LeadCandidateNotFoundError,
    QualificationResultNotFoundError,
    QualificationTargetNotFoundError,
)
from backend.infrastructure.llm.mock_provider import MockLLMProvider
from tests.conftest import (
    FakeCompanyRepository,
    FakeICPProfileRepository,
    FakeLeadCandidateRepository,
    FakeLeadRepository,
    build_fake_compliance_service,
    build_fake_icp_service,
    build_fake_lead_qualification_service,
    build_fake_lead_sourcing_service,
)


async def _seed_sourced_candidates(icp_repo=None, icp_id=None):
    """Build a Lead Sourcing run over the mock provider's Logistics pool
    and return (candidates_repo, candidates, icp_service) for reuse by
    qualification. ``icp_service`` shares the same ``icp_repo`` so a
    previously created ICP profile is visible to both services."""
    candidates_repo = FakeLeadCandidateRepository()
    icp_service = build_fake_icp_service(icp_repo)
    sourcing = build_fake_lead_sourcing_service(
        candidates=candidates_repo, icp_service=icp_service
    )
    campaign = await sourcing.create_campaign(
        CreateLeadSourcingCampaignRequest(
            name="C", target_industry="Logistics", icp_profile_id=icp_id
        ),
        created_by_user_id=None,
    )
    result = await sourcing.start_run(
        StartLeadSourcingRunRequest(campaign_id=campaign.id),
        started_by_user_id=None,
        started_by_role="admin",
    )
    return candidates_repo, result.candidates, icp_service


async def _build_icp():
    icp_repo = FakeICPProfileRepository()
    icp = await icp_repo.create(
        ICPProfile(
            name="Logistics ICP",
            target_industries=["Logistics"],
            target_keywords=["fleet", "dispatch"],
            excluded_industries=["Gambling"],
        )
    )
    return icp_repo, icp


# -- pure scoring -----------------------------------------------------------------


def test_icp_fit_beeinflusst_score_positiv():
    scoring = QualificationScoringService()
    without_icp = scoring.score(
        QualificationInput(company_name="Acme"),
        min_score=70,
        priority_score=85,
        disqualify_score=40,
    )
    with_icp = scoring.score(
        QualificationInput(company_name="Acme", icp_fit_score=95, icp_fit_level="excellent"),
        min_score=70,
        priority_score=85,
        disqualify_score=40,
    )
    assert with_icp.score > without_icp.score


def test_negative_signals_senken_score():
    scoring = QualificationScoringService()
    clean = scoring.score(
        QualificationInput(icp_fit_score=70, icp_fit_level="good"),
        min_score=70,
        priority_score=85,
        disqualify_score=40,
    )
    with_negatives = scoring.score(
        QualificationInput(
            icp_fit_score=70,
            icp_fit_level="good",
            icp_negative_signals=["Excluded industry matched: Gambling"],
        ),
        min_score=70,
        priority_score=85,
        disqualify_score=40,
    )
    assert with_negatives.score < clean.score


def test_niedriger_score_setzt_disqualified():
    scoring = QualificationScoringService()
    result = scoring.score(
        QualificationInput(icp_fit_score=5, icp_fit_level="not_fit"),
        min_score=70,
        priority_score=85,
        disqualify_score=40,
    )
    assert result.status == "disqualified"
    assert result.recommended_next_action == "skip"
    assert result.disqualification_reason is not None


def test_hoher_score_setzt_priority():
    scoring = QualificationScoringService()
    result = scoring.score(
        QualificationInput(
            company_name="Acme",
            industry="Logistics",
            location="Berlin",
            website_text="x" * 300,
            icp_fit_score=95,
            icp_fit_level="excellent",
            icp_matched_signals=["Buying trigger matched: expansion"],
            public_contact_email="info@acme.example",
            source_confidence=0.9,
        ),
        min_score=70,
        priority_score=85,
        disqualify_score=40,
    )
    assert result.status == "priority"
    assert result.recommended_next_action == "start_sales_workflow"


def test_fehlende_daten_erzeugen_warnings():
    scoring = QualificationScoringService()
    result = scoring.score(
        QualificationInput(company_name="X"),
        min_score=70,
        priority_score=85,
        disqualify_score=40,
    )
    assert len(result.missing_data) > 0


def test_do_not_contact_setzt_status_blocked_in_scoring():
    scoring = QualificationScoringService()
    result = scoring.score(
        QualificationInput(do_not_contact_status="blocked", icp_fit_score=90),
        min_score=70,
        priority_score=85,
        disqualify_score=40,
    )
    assert result.status == "blocked"
    assert result.recommended_next_action == "blocked_do_not_contact"


def test_duplicate_setzt_status_duplicate_in_scoring():
    scoring = QualificationScoringService()
    result = scoring.score(
        QualificationInput(duplicate_status="duplicate", icp_fit_score=90),
        min_score=70,
        priority_score=85,
        disqualify_score=40,
    )
    assert result.status == "duplicate"
    assert result.recommended_next_action == "merge_duplicate"


# -- LLM advisor safe mode -----------------------------------------------------------


async def test_llm_advisor_nutzt_mock_safe_mode():
    from backend.application.lead_qualification.qualification_llm_advisor import (
        QualificationLLMAdvisor,
    )

    scoring = QualificationScoringService()
    base_result = scoring.score(
        QualificationInput(company_name="Acme", icp_fit_score=80, icp_fit_level="good"),
        min_score=70,
        priority_score=85,
        disqualify_score=40,
    )
    advisor = QualificationLLMAdvisor(MockLLMProvider(), max_notes_chars=500)
    enhanced = await advisor.enhance(base_result, company_name="Acme", industry="Logistics")
    # The mock provider never makes a real network call and always
    # succeeds deterministically — the score itself is untouched.
    assert enhanced.score == base_result.score
    assert enhanced.fit_summary is not None


async def test_llm_deaktiviert_macht_keinen_echten_llm_call(monkeypatch):
    from backend.shared.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "lead_qualification_use_llm", False)

    icp_repo, icp = await _build_icp()
    service = build_fake_lead_qualification_service(
        icp_service=build_fake_icp_service(icp_repo), settings=settings
    )
    candidates_repo = FakeLeadCandidateRepository()
    sourcing = build_fake_lead_sourcing_service(
        candidates=candidates_repo, icp_service=build_fake_icp_service(icp_repo)
    )
    campaign = await sourcing.create_campaign(
        CreateLeadSourcingCampaignRequest(
            name="C", target_industry="Logistics", icp_profile_id=icp.id
        ),
        created_by_user_id=None,
    )
    run_result = await sourcing.start_run(
        StartLeadSourcingRunRequest(campaign_id=campaign.id),
        started_by_user_id=None,
        started_by_role="admin",
    )
    service2 = build_fake_lead_qualification_service(
        lead_candidates=candidates_repo,
        icp_service=build_fake_icp_service(icp_repo),
        settings=settings,
    )
    result = await service2.qualify_lead_candidate(
        run_result.candidates[0].id,
        QualifyLeadCandidateRequest(),
        actor_user_id=None,
        actor_role="admin",
    )
    # No LLM call happened — fit_summary is the plain rule-based sentence,
    # never a "[mock] ..." echo (which would only appear if generate_json
    # had actually been invoked).
    assert "[mock]" not in (result.fit_summary or "")


# -- status / dashboard ----------------------------------------------------------


async def test_lead_qualification_status_funktioniert():
    service = build_fake_lead_qualification_service()
    status = await service.get_status()
    assert status.enabled is True
    assert status.use_llm is False


async def test_qualification_dashboard_funktioniert():
    icp_repo, icp = await _build_icp()
    candidates_repo, candidates, icp_service = await _seed_sourced_candidates(icp_repo, icp.id)
    service = build_fake_lead_qualification_service(
        lead_candidates=candidates_repo, icp_service=icp_service
    )
    await service.start_run(
        StartLeadQualificationRequest(
            source_type="lead_candidate",
            lead_candidate_ids=[c.id for c in candidates],
        ),
        started_by_user_id=None,
        started_by_role="admin",
    )
    dashboard = await service.get_dashboard()
    assert dashboard.average_score is not None
    assert (
        dashboard.total_qualified
        + dashboard.total_priority
        + dashboard.total_needs_review
        + dashboard.total_disqualified
        + dashboard.total_blocked
        > 0
    )


# -- single-item qualify ------------------------------------------------------------


async def test_lead_candidate_kann_qualifiziert_werden():
    icp_repo, icp = await _build_icp()
    candidates_repo, candidates, icp_service = await _seed_sourced_candidates(icp_repo, icp.id)
    service = build_fake_lead_qualification_service(
        lead_candidates=candidates_repo, icp_service=icp_service
    )
    result = await service.qualify_lead_candidate(
        candidates[0].id,
        QualifyLeadCandidateRequest(),
        actor_user_id=None,
        actor_role="admin",
    )
    assert result.qualification_score >= 0
    assert result.lead_candidate_id == candidates[0].id


async def test_qualify_missing_candidate_raises():
    service = build_fake_lead_qualification_service()
    with pytest.raises(LeadCandidateNotFoundError):
        await service.qualify_lead_candidate(
            uuid.uuid4(), QualifyLeadCandidateRequest(), actor_user_id=None, actor_role="admin"
        )


async def test_crm_lead_kann_qualifiziert_werden():
    icp_repo, icp = await _build_icp()
    companies = FakeCompanyRepository()
    leads = FakeLeadRepository()
    company = await companies.create(
        Company(name="Acme CRM GmbH", domain="acme-crm.example", industry="Logistics")
    )
    lead = await leads.create(Lead(company_id=company.id, source=LeadSource.OUTBOUND))
    service = build_fake_lead_qualification_service(
        companies=companies, leads=leads, icp_service=build_fake_icp_service(icp_repo)
    )
    result = await service.qualify_crm_lead(
        lead.id, QualifyCRMLeadRequest(icp_profile_id=icp.id), actor_user_id=None, actor_role="admin"
    )
    assert result.lead_id == lead.id
    assert result.company_id == company.id


async def test_qualify_missing_lead_raises():
    service = build_fake_lead_qualification_service()
    with pytest.raises(QualificationTargetNotFoundError):
        await service.qualify_crm_lead(
            uuid.uuid4(), QualifyCRMLeadRequest(), actor_user_id=None, actor_role="admin"
        )


async def test_qualify_high_score_crm_lead_advances_pipeline():
    icp_repo, icp = await _build_icp()
    companies = FakeCompanyRepository()
    leads = FakeLeadRepository()
    company = await companies.create(
        Company(name="Acme Logistics Expansion GmbH", domain="acme-expand.example", industry="Logistics")
    )
    lead = await leads.create(Lead(company_id=company.id, source=LeadSource.OUTBOUND))
    website_research = None
    from tests.conftest import build_fake_website_research_service
    from backend.application.research.schemas import WebsiteResearchResponse

    responses = {
        "https://acme-expand.example": WebsiteResearchResponse(
            url="https://acme-expand.example",
            final_url="https://acme-expand.example",
            domain="acme-expand.example",
            title="Acme",
            meta_description=None,
            extracted_text=(
                "Wir betreiben eine grosse Fleet und suchen nach besserem "
                "Dispatch. " * 5
            ),
            text_length=200,
            pages_fetched=1,
            sources_used=["https://acme-expand.example"],
            warnings=[],
        )
    }
    service = build_fake_lead_qualification_service(
        companies=companies,
        leads=leads,
        icp_service=build_fake_icp_service(icp_repo),
        website_research=build_fake_website_research_service(responses=responses),
    )
    result = await service.qualify_crm_lead(
        lead.id, QualifyCRMLeadRequest(icp_profile_id=icp.id), actor_user_id=None, actor_role="admin"
    )
    updated_lead = await leads.get(lead.id)
    if result.qualification_status in ("qualified", "priority"):
        assert updated_lead.pipeline_status == PipelineStatus.RESEARCH_COMPLETED
    else:
        assert updated_lead.pipeline_status == PipelineStatus.NEW


# -- batch run / dry run -------------------------------------------------------------


async def test_qualification_run_kann_gestartet_werden():
    icp_repo, icp = await _build_icp()
    candidates_repo, candidates, icp_service = await _seed_sourced_candidates(icp_repo, icp.id)
    service = build_fake_lead_qualification_service(
        lead_candidates=candidates_repo, icp_service=icp_service
    )
    response = await service.start_run(
        StartLeadQualificationRequest(
            source_type="lead_candidate",
            lead_candidate_ids=[c.id for c in candidates],
        ),
        started_by_user_id=None,
        started_by_role="admin",
    )
    assert response.run.status == "completed"
    assert response.run.total_items == len(candidates)
    assert len(response.results) == len(candidates)


async def test_dry_run_veraendert_keine_crm_daten():
    icp_repo, icp = await _build_icp()
    companies = FakeCompanyRepository()
    leads = FakeLeadRepository()
    company = await companies.create(
        Company(name="Acme Dry GmbH", domain="acme-dry.example", industry="Logistics")
    )
    lead = await leads.create(Lead(company_id=company.id, source=LeadSource.OUTBOUND))
    service = build_fake_lead_qualification_service(
        companies=companies, leads=leads, icp_service=build_fake_icp_service(icp_repo)
    )
    await service.start_run(
        StartLeadQualificationRequest(
            source_type="crm_lead", lead_ids=[lead.id], icp_profile_id=icp.id, dry_run=True
        ),
        started_by_user_id=None,
        started_by_role="admin",
    )
    updated_lead = await leads.get(lead.id)
    # Dry run never advances the pipeline, regardless of score.
    assert updated_lead.pipeline_status == PipelineStatus.NEW


# -- do-not-contact / duplicate integration ------------------------------------------


async def test_do_not_contact_setzt_status_blocked():
    icp_repo, icp = await _build_icp()
    compliance = build_fake_compliance_service()
    await compliance.create_entry(
        CreateDoNotContactRequest(company_name="Nordwind Logistik GmbH", reason="opt-out"),
        created_by_user_id=None,
    )
    candidates_repo, candidates, icp_service = await _seed_sourced_candidates(icp_repo, icp.id)
    service = build_fake_lead_qualification_service(
        lead_candidates=candidates_repo, icp_service=icp_service, compliance=compliance
    )
    blocked_candidate = next(c for c in candidates if c.company_name == "Nordwind Logistik GmbH")
    result = await service.qualify_lead_candidate(
        blocked_candidate.id, QualifyLeadCandidateRequest(), actor_user_id=None, actor_role="admin"
    )
    assert result.qualification_status == "blocked"
    assert result.compliance_status == "blocked"
    assert result.recommended_next_action == "blocked_do_not_contact"


async def test_duplicate_setzt_status_duplicate():
    icp_repo, icp = await _build_icp()
    candidates_repo, candidates, icp_service = await _seed_sourced_candidates(icp_repo, icp.id)
    service = build_fake_lead_qualification_service(
        lead_candidates=candidates_repo, icp_service=icp_service
    )
    # Sourcing a second time against the same candidates repo marks
    # everything found again as a duplicate.
    sourcing2 = build_fake_lead_sourcing_service(
        candidates=candidates_repo, icp_service=icp_service
    )
    campaign = await sourcing2.create_campaign(
        CreateLeadSourcingCampaignRequest(name="C2", target_industry="Logistics", icp_profile_id=icp.id),
        created_by_user_id=None,
    )
    second_run = await sourcing2.start_run(
        StartLeadSourcingRunRequest(campaign_id=campaign.id),
        started_by_user_id=None,
        started_by_role="admin",
    )
    duplicate_candidate = second_run.candidates[0]
    assert duplicate_candidate.duplicate_status == "duplicate"
    result = await service.qualify_lead_candidate(
        duplicate_candidate.id, QualifyLeadCandidateRequest(), actor_user_id=None, actor_role="admin"
    )
    assert result.qualification_status == "duplicate"
    assert result.recommended_next_action == "merge_duplicate"


# -- persistence / review ------------------------------------------------------------


async def test_qualification_result_wird_gespeichert():
    icp_repo, icp = await _build_icp()
    candidates_repo, candidates, icp_service = await _seed_sourced_candidates(icp_repo, icp.id)
    service = build_fake_lead_qualification_service(
        lead_candidates=candidates_repo, icp_service=icp_service
    )
    result = await service.qualify_lead_candidate(
        candidates[0].id, QualifyLeadCandidateRequest(), actor_user_id=None, actor_role="admin"
    )
    fetched = await service.get_result(result.id)
    assert fetched.id == result.id
    assert fetched.qualification_score == result.qualification_score


async def test_review_qualification_result_funktioniert():
    icp_repo, icp = await _build_icp()
    candidates_repo, candidates, icp_service = await _seed_sourced_candidates(icp_repo, icp.id)
    service = build_fake_lead_qualification_service(
        lead_candidates=candidates_repo, icp_service=icp_service
    )
    result = await service.qualify_lead_candidate(
        candidates[0].id, QualifyLeadCandidateRequest(), actor_user_id=None, actor_role="admin"
    )
    review = await service.review_result(
        result.id,
        QualificationReviewRequest(qualification_status="priority", notes="Looks strong"),
        reviewed_by_user_id=None,
        reviewed_by_role="admin",
    )
    assert review.result.qualification_status == "priority"
    assert "Looks strong" in (review.result.fit_summary or "")


async def test_review_cannot_unblock_a_blocked_result():
    icp_repo, icp = await _build_icp()
    compliance = build_fake_compliance_service()
    await compliance.create_entry(
        CreateDoNotContactRequest(company_name="Nordwind Logistik GmbH", reason="opt-out"),
        created_by_user_id=None,
    )
    candidates_repo, candidates, icp_service = await _seed_sourced_candidates(icp_repo, icp.id)
    service = build_fake_lead_qualification_service(
        lead_candidates=candidates_repo, icp_service=icp_service, compliance=compliance
    )
    blocked_candidate = next(c for c in candidates if c.company_name == "Nordwind Logistik GmbH")
    result = await service.qualify_lead_candidate(
        blocked_candidate.id, QualifyLeadCandidateRequest(), actor_user_id=None, actor_role="admin"
    )
    review = await service.review_result(
        result.id,
        QualificationReviewRequest(qualification_status="qualified"),
        reviewed_by_user_id=None,
        reviewed_by_role="admin",
    )
    # Do-not-contact can never be bypassed, including by a manual review.
    assert review.result.qualification_status == "blocked"


async def test_review_missing_result_raises():
    service = build_fake_lead_qualification_service()
    with pytest.raises(QualificationResultNotFoundError):
        await service.review_result(
            uuid.uuid4(),
            QualificationReviewRequest(qualification_status="qualified"),
            reviewed_by_user_id=None,
            reviewed_by_role="admin",
        )
