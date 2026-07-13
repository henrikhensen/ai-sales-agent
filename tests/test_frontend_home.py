"""Phase: editorial Silicon-Allee-inspired redesign — frontend regression
checks for the rebuilt home page and the visually reduced Sidebar.

Source-level checks (see test_frontend_safety.py for why): the redesigned
home page renders its five sections (hero, core workflow, embedded Lead
Finder, safety block) with the exact requested hero copy, and the
Sidebar keeps a short five-item main navigation while every admin/
advanced route remains reachable under "Erweitert". Complements (does
not replace) `npx tsc --noEmit` + `npm run build`.
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


def test_home_hero_has_the_exact_requested_headline():
    source = _home_source()
    assert "Find companies." in source
    assert "Analyze websites." in source
    assert "Prepare outreach." in source


def test_home_hero_has_subline_and_ctas():
    source = _home_source()
    assert "Ein AI Sales Copilot für kontrollierte B2B-Kaltaquise" in source
    assert "Lead Finder starten" in source
    assert "Letzte Runs ansehen" in source


def test_home_hero_ctas_link_to_lead_finder_sections():
    source = _home_source()
    assert 'href="#lead-finder"' in source
    assert 'href="#letzte-runs"' in source


def test_home_hero_is_a_solid_dark_surface_not_a_gradient_glow():
    """Style requirement: strong black/white contrast, no SaaS gradient
    glow — the hero is a flat `bg-ink-950` block."""
    source = _home_source()
    assert "bg-ink-950" in source
    assert "radial-gradient" not in source


# -- core workflow --------------------------------------------------------------------


def test_home_core_workflow_topics_present():
    source = _home_source()
    for title in (
        "Zielgruppe",
        "Firmensuche",
        "Website-Analyse",
        "Qualification",
        "Review Draft",
    ):
        assert f'"{title}"' in source, title


# -- Lead Finder is embedded, not just linked ------------------------------------------


def test_home_embeds_the_lead_finder_app():
    source = _home_source()
    assert "LeadFinderApp" in source
    assert "<LeadFinderApp embedded" in source


# -- safety block ------------------------------------------------------------------------


def test_home_has_a_compact_safety_block():
    source = _home_source()
    assert "SafetyBlock" in source
    assert "Kein Auto-Send" in source
    assert "Human Review Pflicht" in source
    assert "Do-not-contact aktiv" in source


# -- no overloaded tables / scattered small cards on the home page --------------------


def test_home_has_no_dense_dashboard_tables():
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


def test_sidebar_is_visually_reduced():
    """Style requirement: active nav state is a quiet left-border accent,
    not a solid filled pill — and the old boxed logo mark is gone."""
    source = _sidebar_source()
    assert "border-l-ink-950" in source
    assert "rounded-xl bg-ink-950" not in source


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
