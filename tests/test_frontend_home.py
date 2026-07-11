"""Phase: modern Copilot redesign — frontend regression checks for the new
home/landing page and the simplified Sidebar navigation.

Source-level checks (see test_frontend_safety.py for why): the redesigned
home page renders its hero, safety strip, workflow steps, and the
embedded Lead Finder; the Sidebar keeps a short five-item main
navigation while every admin/advanced route remains reachable under
"Erweitert". Complements (does not replace) `npx tsc --noEmit` +
`npm run build`.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND = REPO_ROOT / "frontend"


def _read(path: str) -> str:
    return (FRONTEND / path).read_text(encoding="utf-8")


def _home_source() -> str:
    return _read("app/page.tsx")


def _sidebar_source() -> str:
    return _read("components/layout/Sidebar.tsx")


# -- hero ---------------------------------------------------------------------------


def test_home_hero_has_headline_subline_and_ctas():
    source = _home_source()
    assert "Finde passende B2B-Leads" in source
    assert "Analysiere Websites" in source
    assert "geprüfte" in source and "Outreach-Drafts" in source
    assert "kein automatischer Versand" in source
    assert "Lead Finder starten" in source
    assert "Letzte Analysen ansehen" in source


def test_home_hero_ctas_link_to_lead_finder_sections():
    source = _home_source()
    assert 'href="#lead-finder"' in source
    assert 'href="#letzte-runs"' in source


# -- safety strip ---------------------------------------------------------------------


def test_home_safety_strip_present():
    source = _home_source()
    assert "Safe/Mock Mode aktiv" in source
    assert "Kein automatischer Versand" in source
    assert "Human Review erforderlich" in source
    assert "Do-not-contact aktiv" in source


# -- workflow steps -------------------------------------------------------------------


def test_home_workflow_steps_present():
    source = _home_source()
    for title in (
        "Zielgruppe definieren",
        "Firmen finden",
        "Website analysieren",
        "Lead bewerten",
        "Draft prüfen",
    ):
        assert title in source, title


# -- Lead Finder is embedded, not just linked ------------------------------------------


def test_home_embeds_the_lead_finder_app():
    source = _home_source()
    assert "LeadFinderApp" in source
    assert "<LeadFinderApp embedded" in source


# -- no overloaded tables on the home page ---------------------------------------------


def test_home_has_no_dense_dashboard_tables():
    """The old Command Center's dense multi-widget "Überblick" grid is
    gone — Lead Finder's own "Letzte Runs" cards (part of LeadFinderApp)
    are the only recent-activity view on this page now."""
    source = _home_source()
    assert "Letzte Workflows" not in source
    assert "Offene Reviews" not in source


def test_home_has_secondary_tools_links():
    source = _home_source()
    assert "Weitere Werkzeuge" in source
    assert 'href="/sales-strategy/icp"' in source


# -- Sidebar: five main items, everything else under "Erweitert" ----------------------


def test_sidebar_main_navigation_has_exactly_five_destinations():
    source = _sidebar_source()
    main_start = source.index("const MAIN_ITEMS")
    main_end = source.index("const ADVANCED_ITEMS")
    main_body = source[main_start:main_end]
    for label in ("Start", "Lead Finder", "Reviews", "Leads", "Einstellungen"):
        assert f'label: "{label}"' in main_body, label
    assert main_body.count("href:") == 5


def test_sidebar_advanced_section_still_reaches_every_admin_route():
    source = _sidebar_source()
    for href in (
        "/admin/controls",
        "/audit-logs",
        "/users",
        "/system/status",
        "/compliance/data-retention",
        "/compliance/data-requests",
        "/quality",
        "/beta-test",
        "/real-world-test",
        "/sales-strategy/icp",
        "/lead-sourcing",
        "/lead-qualification",
        "/outreach",
    ):
        assert f'href: "{href}"' in source, href


def test_sidebar_leads_points_to_crm_pipeline():
    source = _sidebar_source()
    assert '{ href: "/crm/pipeline", label: "Leads"' in source


# -- existing core pages were not deleted ----------------------------------------------


def test_core_journey_pages_still_exist():
    for path in (
        "app/sales-strategy/icp/page.tsx",
        "app/sales-strategy/offers/page.tsx",
        "app/workflows/sales/page.tsx",
        "app/lead-qualification/page.tsx",
        "app/reviews/page.tsx",
        "app/outreach/page.tsx",
        "app/crm/page.tsx",
        "app/compliance/status/page.tsx",
        "app/compliance/do-not-contact/page.tsx",
        "app/lead-finder/page.tsx",
    ):
        assert (FRONTEND / path).is_file(), path
