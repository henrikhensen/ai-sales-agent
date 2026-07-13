"""Phases: premium AI SaaS redesign, then the editorial Silicon-Allee-
inspired follow-up — regression checks for the shared design-system
components and their use on Settings/Lead Finder.

Same source-level approach as the other `test_frontend_*` files (no Jest/
RTL in this project, see test_frontend_safety.py) — these assert the
components exist and are wired into the pages the redesign touched,
without re-testing existing behavior already covered elsewhere.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND = REPO_ROOT / "frontend"


def _read(path: str) -> str:
    return (FRONTEND / path).read_text(encoding="utf-8")


# -- new shared components exist -------------------------------------------------------


def test_new_ui_components_exist():
    for name in ("StatusPill", "SectionHeader", "EmptyState", "WorkflowStep"):
        assert (FRONTEND / "components" / "ui" / f"{name}.tsx").is_file(), name


# -- Settings: Backend / Lead Sourcing / LLM / Safety status cards ----------------------


def test_settings_page_has_the_four_status_cards():
    source = _read("app/settings/page.tsx")
    for title in ('title="Backend"', 'title="Lead Sourcing"', 'title="LLM"', 'title="Safety"'):
        assert title in source, title


def test_settings_debug_json_is_collapsible():
    source = _read("app/settings/page.tsx")
    assert "<details" in source
    assert "<summary" in source


def test_settings_safety_card_shows_standing_guarantees_and_llm_mode():
    source = _read("app/settings/page.tsx")
    assert "Kein automatischer Versand" in source
    assert "Human Review erforderlich" in source
    assert "Do-not-contact aktiv" in source
    assert "LLM Modus" in source


# -- Lead Finder: candidate cards show source + compact (non-list) hints ----------------


def test_lead_finder_candidate_cards_show_source():
    source = _read("components/lead-finder/LeadFinderApp.tsx")
    assert "candidate.source_name" in source
    assert "Quelle:" in source


def test_lead_finder_compliance_hint_is_a_compact_strip_not_a_bulleted_wall():
    """The compliance hint above the form used to be a `<ul><li>` bulleted
    wall of amber text; it is now a single compact line with no colored
    "warning wall" background at all."""
    source = _read("components/lead-finder/LeadFinderApp.tsx")
    hint_start = source.index("Nur öffentliche Daten")
    hint_end = source.index("Suche starten")
    hint_section = source[hint_start:hint_end]
    assert "<ul" not in hint_section
    assert "<li>" not in hint_section
    assert "bg-amber" not in hint_section


def test_lead_finder_input_panel_is_a_large_framed_panel():
    source = _read("components/lead-finder/LeadFinderApp.tsx")
    assert 'variant="framed"' in source


# -- angular, high-contrast design system ----------------------------------------------


def test_core_components_are_angular_not_rounded():
    """Style requirement: a kantig (sharp-edged) venture/editorial look —
    Card and Button use sharp corners, not the previous rounded-2xl/3xl
    SaaS-default look."""
    for name in ("Card", "Button"):
        source = _read(f"components/ui/{name}.tsx")
        assert "rounded-none" in source
        assert "rounded-3xl" not in source
        assert "rounded-2xl" not in source


def test_button_has_an_invert_hover_signature():
    """The everyday primary action inverts fill/text using the brand
    palette's `muted` tone (not white — white stays reserved for the rare
    `dark` variant's stronger accent, per the brand brief)."""
    source = _read("components/ui/Button.tsx")
    assert "bg-muted" in source
    assert "hover:text-muted" in source
    assert "hover:bg-transparent hover:text-white" in source  # the `dark` variant
