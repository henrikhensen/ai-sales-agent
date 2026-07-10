"""Tests for RealWorldTestRunService using in-memory fakes and the
deterministic MockLLMProvider — no real database, no real website fetch,
no real LLM call, no external contact of any kind.
"""

import uuid

import pytest

from backend.application.compliance.do_not_contact_service import DoNotContactService
from backend.application.compliance.schemas import CreateDoNotContactRequest
from backend.application.real_world_test.schemas import CreateRealWorldTestRunRequest
from backend.domain.entities.company import Company
from backend.domain.entities.lead import Lead
from backend.domain.enums import LeadSource
from backend.domain.entities.lead_candidate import LeadCandidate
from backend.domain.exceptions import (
    InvalidRealWorldTestRunTransitionError,
    RealWorldTestModeNotAllowedError,
    RealWorldTestRunNotFoundError,
)
from tests.conftest import (
    FakeCompanyRepository,
    FakeDoNotContactRepository,
    FakeLeadCandidateRepository,
    FakeLeadRepository,
    build_fake_real_world_test_run_service,
)


async def test_create_run_with_direct_company_name_completes():
    service = build_fake_real_world_test_run_service()
    run = await service.create_run(
        CreateRealWorldTestRunRequest(
            name="Direct run",
            company_name="Acme GmbH",
            product_or_service_offered="Freight API",
        ),
        actor_user_id=None,
        actor_role="admin",
    )
    assert run.status == "completed"
    assert run.workflow_run_id is not None
    assert run.mode == "safe"


async def test_create_run_defaults_to_safe_mode():
    service = build_fake_real_world_test_run_service()
    run = await service.create_run(
        CreateRealWorldTestRunRequest(name="Run", company_name="Acme"),
        actor_user_id=None,
        actor_role="admin",
    )
    assert run.mode == "safe"


async def test_create_run_resolves_lead_candidate():
    candidates = FakeLeadCandidateRepository()
    candidate = await candidates.create(
        LeadCandidate(
            sourcing_run_id=uuid.uuid4(),
            campaign_id=uuid.uuid4(),
            company_name="Candidate Co",
            industry="Logistics",
        )
    )
    service = build_fake_real_world_test_run_service(lead_candidates=candidates)
    run = await service.create_run(
        CreateRealWorldTestRunRequest(
            name="Candidate run",
            lead_candidate_id=candidate.id,
            product_or_service_offered="X",
        ),
        actor_user_id=None,
        actor_role="admin",
    )
    assert run.status == "completed"
    assert run.input_snapshot["company_name"] == "Candidate Co"
    assert run.lead_candidate_id == candidate.id


async def test_create_run_resolves_crm_lead():
    companies = FakeCompanyRepository()
    company = await companies.create(Company(name="CRM Co", domain="crmco.example"))
    leads = FakeLeadRepository()
    lead = await leads.create(Lead(company_id=company.id, source=LeadSource.OUTBOUND))
    service = build_fake_real_world_test_run_service(companies=companies, leads=leads)
    run = await service.create_run(
        CreateRealWorldTestRunRequest(
            name="Lead run", lead_id=lead.id, product_or_service_offered="X"
        ),
        actor_user_id=None,
        actor_role="admin",
    )
    assert run.status == "completed"
    assert run.input_snapshot["company_name"] == "CRM Co"
    assert run.lead_id == lead.id


async def test_create_run_blocked_by_do_not_contact_domain():
    compliance = DoNotContactService(FakeDoNotContactRepository())
    await compliance.create_entry(
        CreateDoNotContactRequest(domain="blocked.example", reason="opt-out"),
        created_by_user_id=None,
    )
    service = build_fake_real_world_test_run_service(compliance=compliance)
    run = await service.create_run(
        CreateRealWorldTestRunRequest(
            name="Blocked run",
            company_name="Blocked Co",
            website_url="https://blocked.example",
            product_or_service_offered="X",
        ),
        actor_user_id=None,
        actor_role="admin",
    )
    assert run.status == "blocked"
    assert run.workflow_run_id is None
    assert any("do-not-contact" in w.lower() for w in run.warnings)


async def test_real_llm_mode_refused_when_not_configured():
    service = build_fake_real_world_test_run_service()
    with pytest.raises(RealWorldTestModeNotAllowedError):
        await service.create_run(
            CreateRealWorldTestRunRequest(
                name="Real run",
                company_name="Acme",
                mode="real_llm",
                product_or_service_offered="X",
            ),
            actor_user_id=None,
            actor_role="admin",
        )


async def test_real_llm_mode_allowed_when_configured(monkeypatch):
    from backend.shared.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "llm_enable_real_calls", True)
    service = build_fake_real_world_test_run_service(settings=settings)
    run = await service.create_run(
        CreateRealWorldTestRunRequest(
            name="Real run",
            company_name="Acme",
            mode="real_llm",
            product_or_service_offered="X",
        ),
        actor_user_id=None,
        actor_role="admin",
    )
    assert run.status == "completed"
    assert run.mode == "real_llm"


async def test_safe_mode_warns_if_system_is_globally_real(monkeypatch):
    from backend.shared.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "llm_enable_real_calls", True)
    service = build_fake_real_world_test_run_service(settings=settings)
    run = await service.create_run(
        CreateRealWorldTestRunRequest(
            name="Safe run", company_name="Acme", product_or_service_offered="X"
        ),
        actor_user_id=None,
        actor_role="admin",
    )
    assert any("no per-run override exists" in w for w in run.warnings)


async def test_abort_pending_run_succeeds():
    service = build_fake_real_world_test_run_service()
    from backend.domain.entities.real_world_test_run import RealWorldTestRun

    run = await service._test_runs.create(RealWorldTestRun(name="Stuck", status="running"))
    aborted = await service.abort_run(run.id, actor_user_id=None, actor_role="admin")
    assert aborted.status == "aborted"
    assert aborted.aborted_at is not None


async def test_abort_terminal_run_raises():
    service = build_fake_real_world_test_run_service()
    run = await service.create_run(
        CreateRealWorldTestRunRequest(name="Done", company_name="Acme"),
        actor_user_id=None,
        actor_role="admin",
    )
    with pytest.raises(InvalidRealWorldTestRunTransitionError):
        await service.abort_run(run.id, actor_user_id=None, actor_role="admin")


async def test_get_run_not_found_raises():
    service = build_fake_real_world_test_run_service()
    with pytest.raises(RealWorldTestRunNotFoundError):
        await service.get_run(uuid.uuid4())


async def test_list_runs_returns_created_runs():
    service = build_fake_real_world_test_run_service()
    await service.create_run(
        CreateRealWorldTestRunRequest(name="Run A", company_name="Acme"),
        actor_user_id=None,
        actor_role="admin",
    )
    result = await service.list_runs(limit=10)
    assert len(result.items) == 1
    assert result.items[0].name == "Run A"
