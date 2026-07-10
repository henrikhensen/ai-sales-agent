"""Phase: Command Center UX polish — frontend regression checks.

This project's frontend has no Jest/React Testing Library (see
PROJECT_RULES.md: no unnecessary new tools) — "frontend tests" means
`npx tsc --noEmit` + `npm run build`, run manually as part of every
phase's final steps. Since the Command Center and its data are behind
client-side auth, a static-HTML assertion after `next build` cannot see
the real rendered content either.

What CAN be verified without a browser or a new test framework is the
frontend *source*: that the Command Center page contains the required
sections/copy, that no send-button label was introduced anywhere, and
that the simplified Sidebar still keeps every admin/advanced route
reachable. This complements (not replaces) an interactive browser check
of the running app.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND = REPO_ROOT / "frontend"


def _read(path: str) -> str:
    return (FRONTEND / path).read_text(encoding="utf-8")


def _all_frontend_source_files():
    for directory in ("app", "components"):
        yield from (FRONTEND / directory).rglob("*.tsx")


# -- no send button anywhere -------------------------------------------------


def test_no_send_button_label_anywhere_in_frontend_source():
    """'Senden'/'Versenden' (capitalized, whole word) is the shape a real
    send button would take in this app's German UI. It must never appear
    outside of a code comment documenting that it is deliberately absent."""
    import re

    pattern = re.compile(r"\bSenden\b|\bVersenden\b")
    offending: list[str] = []
    for file in _all_frontend_source_files():
        for line in file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            if pattern.search(line):
                offending.append(f"{file}: {line.strip()}")
    assert offending == []


# -- Command Center page (frontend/app/page.tsx) -----------------------------


def test_command_center_title_present():
    source = _read("app/page.tsx")
    assert "Command Center" in source
    assert "AI Sales Copilot" in source


def test_command_center_has_three_work_areas():
    source = _read("app/page.tsx")
    assert "A · Setup" in source
    assert "B · Lead prüfen" in source
    assert "C · Draft & Review" in source


def test_command_center_shows_safety_status_prominently():
    source = _read("app/page.tsx")
    assert 'title="Safety Status"' in source
    assert "Kein automatischer Versand" in source
    assert "Human Review erforderlich" in source
    assert "Do-not-contact aktiv" in source
    assert "Safe/Mock Mode aktiv" in source
    assert "Echte Provider nur bewusst aktiv" in source


def test_command_center_journey_has_all_six_steps_with_status_and_cta():
    source = _read("app/page.tsx")
    expected_cta_targets = [
        "/sales-strategy/icp",
        "/lead-finder",
        "/lead-qualification",
        "/crm",
        "/reviews",
        "/outreach",
    ]
    for target in expected_cta_targets:
        assert f'ctaHref: "{target}"' in source, target
    for status_label in ("offen", "bereit", "erledigt", "blockiert"):
        assert f'"{status_label}"' in source, status_label


def test_command_center_declutters_overview_to_required_widgets():
    source = _read("app/page.tsx")
    assert 'title="Letzte Workflows"' in source
    assert "Leads mit nächstem Schritt" in source
    assert 'title="Offene Reviews"' in source
    assert 'title="Letzte Warnings"' in source


# -- Sidebar: simplified but still complete ----------------------------------


def test_sidebar_groups_advanced_items_into_a_collapsible_section():
    source = _read("components/layout/Sidebar.tsx")
    assert 'title: "Start"' in source
    assert 'title: "Erweitert"' in source
    assert "collapsible: true" in source


def test_sidebar_start_section_stays_small_for_beginners():
    """The first section a new user sees must stay short — this is the
    whole point of the nav simplification. Count items between the
    'Start' section's items array and its closing bracket."""
    source = _read("components/layout/Sidebar.tsx")
    start_index = source.index('title: "Start"')
    items_start = source.index("items: [", start_index)
    items_end = source.index("],", items_start)
    start_section_body = source[items_start:items_end]
    assert start_section_body.count("href:") <= 3


def test_sidebar_still_reaches_admin_and_advanced_pages():
    """Regrouping into 'Erweitert' must never remove a route — admin
    functions stay reachable, just not prominent (PROJECT_RULES.md /
    task instructions: 'Admin-Funktionen bleiben erreichbar, aber
    sekundär')."""
    source = _read("components/layout/Sidebar.tsx")
    for href in (
        "/admin/controls",
        "/audit-logs",
        "/users",
        "/system/status",
        "/settings",
        "/compliance/data-retention",
        "/compliance/data-requests",
        "/quality",
        "/beta-test",
        "/real-world-test",
    ):
        assert f'href: "{href}"' in source, href


# -- existing core pages were not deleted ------------------------------------


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
    ):
        assert (FRONTEND / path).is_file(), path
