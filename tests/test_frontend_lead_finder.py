"""Phase: Guided Lead Discovery Agent ("Lead Finder") — frontend regression
checks.

Same approach as test_frontend_command_center.py: this frontend has no
Jest/RTL (PROJECT_RULES.md: no unnecessary new tools) and the Lead Finder
page's real content renders client-side behind auth, so these are
source-level checks — the page contains its required form fields, result
columns, and primary actions; no send button was introduced; the backend
client exposes the expected calls; and the Command Center/Sidebar
reference the new page prominently, as requested.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND = REPO_ROOT / "frontend"


def _read(path: str) -> str:
    return (FRONTEND / path).read_text(encoding="utf-8")


LEAD_FINDER_SOURCE = None


def _lead_finder_source() -> str:
    global LEAD_FINDER_SOURCE
    if LEAD_FINDER_SOURCE is None:
        LEAD_FINDER_SOURCE = _read("app/lead-finder/page.tsx")
    return LEAD_FINDER_SOURCE


# -- page exists and renders the required sections ---------------------------------


def test_lead_finder_page_exists():
    assert (FRONTEND / "app" / "lead-finder" / "page.tsx").is_file()


def test_lead_finder_has_the_required_form_fields():
    source = _lead_finder_source()
    assert "Wen willst du finden?" in source
    for label in (
        "Branche / Kundentyp",
        "Ort / Region",
        "Angebot",
        "ICP Profil",
        "Anzahl Leads",
        "Mindestscore",
    ):
        assert label in source, label
    assert "Leads finden" in source


def test_lead_finder_result_view_has_required_columns():
    source = _lead_finder_source()
    for text in (
        "Website:",
        "Score",
        "positive_signals",
        "negative_signals",
        "website_quality_reasons",
        "Draft:",
        "in_outreach_queue",
        "run.warnings",
    ):
        assert text in source, text


def test_lead_finder_has_the_three_primary_actions():
    source = _lead_finder_source()
    assert "Details ansehen" in source
    assert "Draft prüfen" in source
    assert "Zur Review Queue hinzufügen" in source


def test_lead_finder_has_no_send_ui():
    source = _lead_finder_source()
    assert "senden" not in source.lower()
    assert "Versand" in source


def test_lead_finder_states_public_data_and_compliance_constraints():
    source = _lead_finder_source()
    assert "Do-not-contact" in source
    assert "LinkedIn Scraping" in source
    assert "Captcha" in source


# -- API client exposes the five use cases --------------------------------------------


def test_api_client_exposes_lead_discovery_functions():
    source = _read("lib/api.ts")
    for function_name in (
        "createLeadDiscoveryRun",
        "getLeadDiscoveryRuns",
        "getLeadDiscoveryRun",
        "runLeadDiscoveryPipeline",
        "createLeadDiscoveryDrafts",
        "addLeadDiscoveryCandidateToQueue",
    ):
        assert f"export function {function_name}" in source, function_name


# -- Command Center / Sidebar make Lead Finder prominent -------------------------------


def test_command_center_makes_lead_finder_prominent():
    source = _read("app/page.tsx")
    assert "Lead Finder" in source
    assert 'ctaHref: "/lead-finder"' in source or 'href="/lead-finder"' in source


def test_sidebar_lists_lead_finder_in_the_start_section():
    source = _read("components/layout/Sidebar.tsx")
    start_index = source.index('title: "Start"')
    items_start = source.index("items: [", start_index)
    items_end = source.index("],", items_start)
    start_section_body = source[items_start:items_end]
    assert '"/lead-finder"' in start_section_body
