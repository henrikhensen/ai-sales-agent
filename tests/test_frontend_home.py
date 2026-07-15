"""Phase: Stodio-inspired editorial redesign of the home page — regression
checks for the restructured 12-section home page (hero, trust strip,
positioning, workflow-showcase, kennzahlen, funktionsbereiche, embedded
Lead Finder, safety, FAQ, closing CTA, footer) and the still-reduced
Sidebar.

Same source-level approach as the other `test_frontend_*` files (no Jest/
RTL in this project, see test_frontend_safety.py). Every prior redesign
phase (44/45/47/48) rewrote this same set of literal-copy assertions when
hero/section copy intentionally changed — this file follows that same
established pattern, not a shortcut around a broken contract. Complements
(does not replace) `npx tsc --noEmit` + `npm run build`.
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


def _footer_source() -> str:
    return _read("components/home/HomeFooter.tsx")


# -- hero ---------------------------------------------------------------------------


def test_home_hero_has_the_exact_requested_headline():
    source = _home_source()
    assert "Firmen finden." in source
    assert "Websites analysieren." in source
    assert "Outreach vorbereiten." in source


def test_home_hero_has_subline_ctas_and_safety_hint():
    source = _home_source()
    assert "Kontrollierte B2B-Akquise mit echten Firmendaten" in source
    assert "Lead Finder starten" in source
    assert "So funktioniert es" in source
    assert "Kein automatischer Versand · Human Review erforderlich" in source


def test_home_hero_ctas_link_to_the_right_sections():
    source = _home_source()
    assert 'href="#lead-finder"' in source
    assert 'href="#workflow-showcase"' in source


def test_home_hero_is_a_solid_dark_surface_not_a_gradient_glow():
    """Style requirement: strong black/white contrast, no SaaS gradient
    glow — the hero is a flat `bg-canvas` block (the brand palette's
    darkest color, #1A0B12)."""
    source = _home_source()
    assert "bg-canvas" in source
    assert "radial-gradient" not in source


# -- trust/status strip ----------------------------------------------------------------


def test_home_has_a_real_status_trust_strip():
    source = _home_source()
    assert "getLeadSourcingStatus" in source
    for label in ("Backend", "Brave Search", "Website Research", "Draft-only", "Human Review aktiv", "Do-not-contact aktiv"):
        assert label in source, label


# -- workflow showcase (replaces the old 5-item Core Workflow grid) --------------------


def test_home_workflow_showcase_has_six_steps():
    source = _home_source()
    for title in (
        "Zielgruppe definieren",
        "Firmen recherchieren",
        "Websites analysieren",
        "Potenzial bewerten",
        "Draft vorbereiten",
        "Human Review",
    ):
        assert f'"{title}"' in source, title


# -- kennzahlen -----------------------------------------------------------------------


def test_home_has_kennzahlen_counters():
    source = _home_source()
    assert "Counter" in source
    for label in (
        "Automatische Send-Aktionen",
        "Human Review",
        "Kontrollierte Workflow-Schritte",
        "Zentrale Lead-Finder-Oberfläche",
    ):
        assert label in source, label


# -- funktionsbereiche ------------------------------------------------------------------


def test_home_has_funktionsbereiche_service_list():
    source = _home_source()
    assert "ServiceList" in source
    for title in (
        "Firmensuche",
        "Website Research",
        "Lead Qualification",
        "Outreach Drafts",
        "Human Review",
        "Compliance",
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
    assert "Kein automatischer Versand" in source
    assert "Kein Massenversand" in source
    assert "Human Review bleibt Pflicht" in source
    assert "Do-not-contact wird serverseitig erzwungen" in source


# -- FAQ ----------------------------------------------------------------------------------


def test_home_has_faq_accordion_with_six_questions():
    source = _home_source()
    assert "FaqAccordion" in source
    for question in (
        "Was macht der AI Sales Copilot?",
        "Werden Nachrichten automatisch versendet?",
        "Woher stammen die Firmendaten?",
        "Wie funktioniert die Qualifikation?",
        "Was bedeutet Human Review?",
        "Wie wird Do-not-contact berücksichtigt?",
    ):
        assert question in source, question


# -- closing CTA + footer ---------------------------------------------------------------


def test_home_has_a_closing_cta():
    source = _home_source()
    assert "Bereit, passende Firmen" in source
    assert "Lead Finder öffnen" in source


def test_home_renders_the_footer():
    source = _home_source()
    assert "HomeFooter" in source


def test_footer_has_secondary_tools_and_compliance_links():
    source = _footer_source()
    assert "Weitere Werkzeuge" in source
    assert "/sales-strategy/icp" in source
    assert "Draft-only · kein automatischer Versand" in source


# -- no overloaded tables / scattered small cards on the home page --------------------


def test_home_has_no_dense_dashboard_tables():
    source = _home_source()
    assert "Letzte Workflows" not in source
    assert "Offene Reviews" not in source


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
    """Style requirement: active nav state is a quiet left-border accent
    (a sparing use of literal white, per the brand brief), not a solid
    filled pill — and the old boxed logo mark is gone."""
    source = _sidebar_source()
    assert "border-l-white" in source
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
