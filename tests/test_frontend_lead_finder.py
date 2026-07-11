"""Phase: Guided Lead Discovery Agent ("Lead Finder") — frontend regression
checks.

Same approach as test_frontend_home.py: this frontend has no Jest/RTL
(PROJECT_RULES.md: no unnecessary new tools) and the Lead Finder's real
content renders client-side behind auth, so these are source-level
checks — the shared ``LeadFinderApp`` component (used both standalone at
/lead-finder and embedded on the home page) contains its required form
fields, result columns, and primary actions; no send button was
introduced; the backend client exposes the expected calls.
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
        LEAD_FINDER_SOURCE = _read("components/lead-finder/LeadFinderApp.tsx")
    return LEAD_FINDER_SOURCE


# -- shared component exists and is used by both routes --------------------------------


def test_lead_finder_app_component_exists():
    assert (FRONTEND / "components" / "lead-finder" / "LeadFinderApp.tsx").is_file()


def test_lead_finder_page_and_home_page_both_use_the_shared_component():
    lead_finder_page = _read("app/lead-finder/page.tsx")
    home_page = _read("app/page.tsx")
    assert "LeadFinderApp" in lead_finder_page
    assert "LeadFinderApp" in home_page


# -- required form fields and result columns --------------------------------------------


def test_lead_finder_has_the_required_form_fields():
    source = _lead_finder_source()
    assert "Wen willst du finden?" in source
    for label in (
        "Zielbranche / Kundentyp",
        "Ort / Region",
        "Angebot",
        "ICP Profil",
        "Anzahl Leads",
        "Mindestscore",
    ):
        assert label in source, label
    assert "Firmen finden" in source and "Websites analysieren" in source


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


def test_lead_finder_website_quality_labels_match_spec():
    source = _lead_finder_source()
    for label in ("Gut", "Mittel", "Schlecht"):
        assert f'"{label}"' in source, label


def test_lead_finder_has_the_three_primary_actions():
    source = _lead_finder_source()
    assert "Details ansehen" in source
    assert "Draft prüfen" in source
    assert "Zur Review Queue hinzufügen" in source


def test_lead_finder_shows_recent_runs_as_cards_not_a_table():
    source = _lead_finder_source()
    assert "Letzte Runs" in source
    assert "Nächster Schritt" in source


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


# -- Sidebar makes Lead Finder prominent -------------------------------------------------


def test_sidebar_lists_lead_finder_in_main_navigation():
    source = _read("components/layout/Sidebar.tsx")
    main_start = source.index("const MAIN_ITEMS")
    main_end = source.index("const ADVANCED_ITEMS")
    main_body = source[main_start:main_end]
    assert '"/lead-finder"' in main_body
