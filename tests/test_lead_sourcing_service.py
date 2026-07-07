"""Tests for the Lead Sourcing Engine's provider factory and service.

Covers: provider defaults/safe-mode, config validation, campaign CRUD,
dry-run vs. real runs, candidate normalization/import, duplicate
detection, do-not-contact blocking, ICP scoring, and approve/reject
(including CRM Company/Lead conversion on approve).
"""

import uuid

import pytest

from backend.application.compliance.schemas import CreateDoNotContactRequest
from backend.application.lead_sourcing.schemas import (
    ApproveLeadCandidateRequest,
    CreateLeadSourcingCampaignRequest,
    ImportLeadCandidatesRequest,
    RejectLeadCandidateRequest,
    StartLeadSourcingRunRequest,
    UpdateLeadSourcingCampaignRequest,
)
from backend.domain.entities.company import Company
from backend.domain.entities.icp_profile import ICPProfile
from backend.domain.exceptions import (
    InvalidLeadSourcingProviderError,
    LeadCandidateBlockedError,
    LeadCandidateNotFoundError,
    LeadSourcingCampaignNotFoundError,
)
from backend.infrastructure.lead_sourcing.base import RawLeadCandidate
from backend.infrastructure.lead_sourcing.factory import get_lead_sourcing_provider
from backend.infrastructure.lead_sourcing.manual_provider import (
    ManualLeadSourcingProvider,
)
from backend.infrastructure.lead_sourcing.mock_provider import MockLeadSourcingProvider
from backend.infrastructure.lead_sourcing.search_api_provider import (
    SearchApiLeadSourcingProvider,
)
from backend.shared.config import get_settings
from tests.conftest import (
    FakeCompanyRepository,
    FakeICPProfileRepository,
    FakeLeadRepository,
    build_fake_compliance_service,
    build_fake_icp_service,
    build_fake_lead_sourcing_service,
)


def _settings(**overrides):
    settings = get_settings()
    original = {}
    for key, value in overrides.items():
        original[key] = getattr(settings, key)
        setattr(settings, key, value)
    return settings, original


def _restore(settings, original):
    for key, value in original.items():
        setattr(settings, key, value)


# -- provider factory -----------------------------------------------------------


def test_mock_lead_sourcing_provider_bleibt_default():
    settings = get_settings()
    assert settings.lead_sourcing_provider == "mock"
    provider = get_lead_sourcing_provider(settings)
    assert isinstance(provider, MockLeadSourcingProvider)


def test_echte_suche_deaktiviert_bedeutet_kein_externer_search_api_call():
    settings, original = _settings(
        lead_sourcing_provider="search_api", lead_sourcing_enable_real_search=False
    )
    try:
        provider = get_lead_sourcing_provider(settings)
        assert isinstance(provider, MockLeadSourcingProvider)
    finally:
        _restore(settings, original)


def test_search_api_provider_used_only_when_real_search_enabled():
    settings, original = _settings(
        lead_sourcing_provider="search_api", lead_sourcing_enable_real_search=True
    )
    try:
        provider = get_lead_sourcing_provider(settings)
        assert isinstance(provider, SearchApiLeadSourcingProvider)
    finally:
        _restore(settings, original)


def test_ungueltiger_lead_sourcing_provider_wird_abgelehnt():
    settings, original = _settings(lead_sourcing_provider="not-a-real-provider")
    try:
        with pytest.raises(InvalidLeadSourcingProviderError):
            get_lead_sourcing_provider(settings)
    finally:
        _restore(settings, original)


def test_manual_provider_always_used_for_manual_regardless_of_real_search():
    settings, original = _settings(
        lead_sourcing_provider="manual", lead_sourcing_enable_real_search=True
    )
    try:
        provider = get_lead_sourcing_provider(settings)
        assert isinstance(provider, ManualLeadSourcingProvider)
    finally:
        _restore(settings, original)


# -- normalization ----------------------------------------------------------------


def test_domains_werden_normalisiert():
    provider = MockLeadSourcingProvider()
    raw = RawLeadCandidate(
        company_name="  Acme GmbH  ",
        company_website_url="https://WWW.Acme-Example.COM/",
    )
    normalized = provider.normalize_candidate(raw)
    assert normalized.company_domain == "acme-example.com"


def test_urls_werden_normalisiert():
    provider = MockLeadSourcingProvider()
    raw = RawLeadCandidate(company_name="Acme", company_website_url="acme-example.com")
    normalized = provider.normalize_candidate(raw)
    assert normalized.company_website_url == "https://acme-example.com"


# -- campaigns ------------------------------------------------------------------


async def test_campaign_kann_erstellt_werden():
    service = build_fake_lead_sourcing_service()
    campaign = await service.create_campaign(
        CreateLeadSourcingCampaignRequest(name="Q1 Logistics", target_industry="Logistics"),
        created_by_user_id=None,
    )
    assert campaign.name == "Q1 Logistics"
    assert campaign.status == "draft"
    assert campaign.source_type == "mock"


async def test_campaign_kann_aktualisiert_werden():
    service = build_fake_lead_sourcing_service()
    campaign = await service.create_campaign(
        CreateLeadSourcingCampaignRequest(name="Original"), created_by_user_id=None
    )
    updated = await service.update_campaign(
        campaign.id, UpdateLeadSourcingCampaignRequest(name="Updated", max_results=5)
    )
    assert updated.name == "Updated"
    assert updated.max_results == 5


async def test_campaign_kann_archiviert_werden():
    service = build_fake_lead_sourcing_service()
    campaign = await service.create_campaign(
        CreateLeadSourcingCampaignRequest(name="Archivable"), created_by_user_id=None
    )
    archived = await service.archive_campaign(campaign.id)
    assert archived.status == "archived"


async def test_update_missing_campaign_raises():
    service = build_fake_lead_sourcing_service()
    with pytest.raises(LeadSourcingCampaignNotFoundError):
        await service.update_campaign(uuid.uuid4(), UpdateLeadSourcingCampaignRequest())


# -- run start / dry run ---------------------------------------------------------


async def test_run_kann_gestartet_werden():
    service = build_fake_lead_sourcing_service()
    campaign = await service.create_campaign(
        CreateLeadSourcingCampaignRequest(name="C", target_industry="Logistics"),
        created_by_user_id=None,
    )
    result = await service.start_run(
        StartLeadSourcingRunRequest(campaign_id=campaign.id),
        started_by_user_id=None,
        started_by_role="admin",
    )
    assert result.run.status == "completed"
    assert result.run.total_candidates_found > 0
    assert result.run.total_candidates_saved == result.run.total_candidates_found
    assert len(result.candidates) == result.run.total_candidates_found
    assert all(c.id is not None for c in result.candidates)


async def test_dry_run_erstellt_keine_crm_leads():
    service = build_fake_lead_sourcing_service()
    campaign = await service.create_campaign(
        CreateLeadSourcingCampaignRequest(name="C", target_industry="Logistics"),
        created_by_user_id=None,
    )
    result = await service.start_run(
        StartLeadSourcingRunRequest(campaign_id=campaign.id, dry_run=True),
        started_by_user_id=None,
        started_by_role="admin",
    )
    assert result.dry_run is True
    assert result.run.total_candidates_saved == 0
    assert all(c.id is None for c in result.candidates)
    listed = await service.list_candidates(campaign_id=campaign.id)
    assert listed.items == []


async def test_kandidaten_werden_gespeichert():
    service = build_fake_lead_sourcing_service()
    campaign = await service.create_campaign(
        CreateLeadSourcingCampaignRequest(name="C", target_industry="Logistics"),
        created_by_user_id=None,
    )
    await service.start_run(
        StartLeadSourcingRunRequest(campaign_id=campaign.id),
        started_by_user_id=None,
        started_by_role="admin",
    )
    listed = await service.list_candidates(campaign_id=campaign.id)
    assert len(listed.items) > 0


async def test_duplikate_werden_erkannt_across_runs():
    service = build_fake_lead_sourcing_service()
    campaign = await service.create_campaign(
        CreateLeadSourcingCampaignRequest(name="C", target_industry="Logistics"),
        created_by_user_id=None,
    )
    first = await service.start_run(
        StartLeadSourcingRunRequest(campaign_id=campaign.id),
        started_by_user_id=None,
        started_by_role="admin",
    )
    assert all(c.duplicate_status == "new" for c in first.candidates)
    second = await service.start_run(
        StartLeadSourcingRunRequest(campaign_id=campaign.id),
        started_by_user_id=None,
        started_by_role="admin",
    )
    assert all(c.duplicate_status == "duplicate" for c in second.candidates)
    assert second.run.total_duplicates == len(second.candidates)


# -- ICP scoring --------------------------------------------------------------------


async def test_icp_scoring_wird_angewendet():
    icp_repo = FakeICPProfileRepository()
    icp = await icp_repo.create(
        ICPProfile(
            name="Logistics ICP",
            target_industries=["Logistics"],
            target_keywords=["fleet", "dispatch"],
        )
    )
    service = build_fake_lead_sourcing_service(icp_service=build_fake_icp_service(icp_repo))
    campaign = await service.create_campaign(
        CreateLeadSourcingCampaignRequest(
            name="C", target_industry="Logistics", icp_profile_id=icp.id
        ),
        created_by_user_id=None,
    )
    result = await service.start_run(
        StartLeadSourcingRunRequest(campaign_id=campaign.id),
        started_by_user_id=None,
        started_by_role="admin",
    )
    assert all(c.icp_fit_score is not None for c in result.candidates)
    assert all(c.icp_fit_level is not None for c in result.candidates)


async def test_no_icp_selected_leaves_fit_score_empty_with_warning():
    service = build_fake_lead_sourcing_service()
    campaign = await service.create_campaign(
        CreateLeadSourcingCampaignRequest(name="C", target_industry="Logistics"),
        created_by_user_id=None,
    )
    result = await service.start_run(
        StartLeadSourcingRunRequest(campaign_id=campaign.id),
        started_by_user_id=None,
        started_by_role="admin",
    )
    for candidate in result.candidates:
        assert candidate.icp_fit_score is None
        assert any("No ICP profile" in w for w in candidate.warnings)


# -- do-not-contact -----------------------------------------------------------------


async def test_do_not_contact_blockiert_kandidaten():
    compliance = build_fake_compliance_service()
    await compliance.create_entry(
        CreateDoNotContactRequest(
            company_name="Nordwind Logistik GmbH", reason="opt-out"
        ),
        created_by_user_id=None,
    )
    service = build_fake_lead_sourcing_service(compliance=compliance)
    campaign = await service.create_campaign(
        CreateLeadSourcingCampaignRequest(name="C", target_industry="Logistics"),
        created_by_user_id=None,
    )
    result = await service.start_run(
        StartLeadSourcingRunRequest(campaign_id=campaign.id),
        started_by_user_id=None,
        started_by_role="admin",
    )
    blocked = [c for c in result.candidates if c.company_name == "Nordwind Logistik GmbH"]
    assert blocked and blocked[0].do_not_contact_status == "blocked"
    assert result.run.total_blocked_by_do_not_contact == 1


async def test_blockierte_kandidaten_koennen_nicht_approved_werden():
    compliance = build_fake_compliance_service()
    await compliance.create_entry(
        CreateDoNotContactRequest(
            company_name="Nordwind Logistik GmbH", reason="opt-out"
        ),
        created_by_user_id=None,
    )
    service = build_fake_lead_sourcing_service(compliance=compliance)
    campaign = await service.create_campaign(
        CreateLeadSourcingCampaignRequest(name="C", target_industry="Logistics"),
        created_by_user_id=None,
    )
    result = await service.start_run(
        StartLeadSourcingRunRequest(campaign_id=campaign.id),
        started_by_user_id=None,
        started_by_role="admin",
    )
    blocked = next(c for c in result.candidates if c.do_not_contact_status == "blocked")
    with pytest.raises(LeadCandidateBlockedError):
        await service.approve_candidate(
            blocked.id,
            ApproveLeadCandidateRequest(),
            approved_by_user_id=None,
            approved_by_role="admin",
        )


# -- approve / reject ---------------------------------------------------------------


async def test_kandidat_kann_approved_werden():
    service = build_fake_lead_sourcing_service()
    campaign = await service.create_campaign(
        CreateLeadSourcingCampaignRequest(name="C", target_industry="Logistics"),
        created_by_user_id=None,
    )
    result = await service.start_run(
        StartLeadSourcingRunRequest(campaign_id=campaign.id),
        started_by_user_id=None,
        started_by_role="admin",
    )
    candidate = result.candidates[0]
    approved = await service.approve_candidate(
        candidate.id,
        ApproveLeadCandidateRequest(),
        approved_by_user_id=None,
        approved_by_role="admin",
    )
    assert approved.candidate.review_status == "approved"
    assert approved.crm_company_id is not None
    assert approved.crm_lead_id is not None


async def test_approved_kandidat_erstellt_crm_company_und_lead():
    companies = FakeCompanyRepository()
    leads = FakeLeadRepository()
    service = build_fake_lead_sourcing_service(companies=companies, leads=leads)
    campaign = await service.create_campaign(
        CreateLeadSourcingCampaignRequest(name="C", target_industry="Logistics"),
        created_by_user_id=None,
    )
    result = await service.start_run(
        StartLeadSourcingRunRequest(campaign_id=campaign.id),
        started_by_user_id=None,
        started_by_role="admin",
    )
    candidate = result.candidates[0]
    approved = await service.approve_candidate(
        candidate.id,
        ApproveLeadCandidateRequest(),
        approved_by_user_id=None,
        approved_by_role="admin",
    )
    company = await companies.get(approved.crm_company_id)
    assert company is not None
    assert company.name == candidate.company_name
    lead = await leads.get(approved.crm_lead_id)
    assert lead is not None
    assert lead.company_id == company.id


async def test_approve_links_existing_company_instead_of_duplicating():
    companies = FakeCompanyRepository()
    existing = await companies.create(
        Company(name="Nordwind Logistik GmbH", domain="nordwind-logistik.example")
    )
    service = build_fake_lead_sourcing_service(companies=companies)
    campaign = await service.create_campaign(
        CreateLeadSourcingCampaignRequest(name="C", target_industry="Logistics"),
        created_by_user_id=None,
    )
    result = await service.start_run(
        StartLeadSourcingRunRequest(campaign_id=campaign.id),
        started_by_user_id=None,
        started_by_role="admin",
    )
    candidate = next(c for c in result.candidates if c.company_name == "Nordwind Logistik GmbH")
    assert candidate.duplicate_status == "duplicate"
    approved = await service.approve_candidate(
        candidate.id,
        ApproveLeadCandidateRequest(),
        approved_by_user_id=None,
        approved_by_role="admin",
    )
    assert approved.crm_company_id == existing.id
    all_companies = await companies.list()
    assert len(all_companies) == 1


async def test_kandidat_kann_rejected_werden():
    service = build_fake_lead_sourcing_service()
    campaign = await service.create_campaign(
        CreateLeadSourcingCampaignRequest(name="C", target_industry="Logistics"),
        created_by_user_id=None,
    )
    result = await service.start_run(
        StartLeadSourcingRunRequest(campaign_id=campaign.id),
        started_by_user_id=None,
        started_by_role="admin",
    )
    candidate = result.candidates[0]
    rejected = await service.reject_candidate(
        candidate.id,
        RejectLeadCandidateRequest(reason="Not relevant"),
        rejected_by_user_id=None,
        rejected_by_role="admin",
    )
    assert rejected.candidate.review_status == "rejected"


async def test_approve_missing_candidate_raises():
    service = build_fake_lead_sourcing_service()
    with pytest.raises(LeadCandidateNotFoundError):
        await service.approve_candidate(
            uuid.uuid4(),
            ApproveLeadCandidateRequest(),
            approved_by_user_id=None,
            approved_by_role="admin",
        )


# -- manual import ------------------------------------------------------------------


async def test_kandidaten_import_funktioniert():
    service = build_fake_lead_sourcing_service()
    campaign = await service.create_campaign(
        CreateLeadSourcingCampaignRequest(name="Import Campaign"), created_by_user_id=None
    )
    result = await service.import_candidates(
        ImportLeadCandidatesRequest(
            campaign_id=campaign.id,
            raw_text="Acme Import GmbH, acme-import.example, https://acme-import.example, met at conference",
        ),
        imported_by_user_id=None,
        imported_by_role="admin",
    )
    assert result.total_imported == 1
    assert result.candidates[0].company_name == "Acme Import GmbH"
    assert result.candidates[0].company_domain == "acme-import.example"
    assert result.candidates[0].source_type == "manual"


async def test_import_skips_lines_without_company_name_or_domain():
    service = build_fake_lead_sourcing_service()
    campaign = await service.create_campaign(
        CreateLeadSourcingCampaignRequest(name="Import Campaign"), created_by_user_id=None
    )
    result = await service.import_candidates(
        ImportLeadCandidatesRequest(campaign_id=campaign.id, raw_text=",,,\nSomeCo,,,"),
        imported_by_user_id=None,
        imported_by_role="admin",
    )
    assert result.total_imported == 1
    assert any("Skipped line" in w for w in result.warnings)
