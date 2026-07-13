"""Phase: refine frontend using the /design-reference screenshot folder —
regression checks for the scroll-reveal system, the animated hero
background, the Lead Finder stats strip, staggered result entrances, and
smooth-scroll-to-results.

Same source-level approach as the other `test_frontend_*` files (no Jest/
RTL in this project, see test_frontend_safety.py) — layout/typography/
motion principles were taken from the screenshots, not any copied asset,
logo, or text (design-reference/ itself is never read by the app or
these tests, only by the human developer during implementation).
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND = REPO_ROOT / "frontend"


def _read(path: str) -> str:
    return (FRONTEND / path).read_text(encoding="utf-8")


def _home_source() -> str:
    return _read("app/page.tsx")


def _lead_finder_source() -> str:
    return _read("components/lead-finder/LeadFinderApp.tsx")


# -- scroll-reveal system ----------------------------------------------------------------


def test_reveal_component_exists():
    source = _read("components/ui/Reveal.tsx")
    assert "IntersectionObserver" in source
    assert "animate-fade-in-up" in source


def test_home_sections_use_reveal_not_just_mount_time_animation():
    source = _home_source()
    assert "Reveal" in source
    # At least the workflow/lead-finder/safety sections below the fold
    # should use the scroll-triggered wrapper.
    assert source.count("<Reveal") >= 3


def test_settings_status_cards_use_reveal():
    source = _read("app/settings/page.tsx")
    assert "<Reveal" in source


# -- animated hero background (no foreign image/asset) -----------------------------------


def test_hero_has_a_css_only_animated_background():
    source = _home_source()
    assert "animate-drift-a" in source
    assert "animate-drift-b" in source
    assert 'aria-hidden="true"' in source


def test_tailwind_defines_the_drift_keyframes():
    source = _read("tailwind.config.ts")
    assert "drift-a" in source
    assert "drift-b" in source


# -- Lead Finder: stats strip instead of a plain summary sentence ------------------------


def test_lead_finder_shows_a_stats_strip():
    source = _lead_finder_source()
    for label in ("Gefunden", "Websites analysiert", "Qualifiziert", "Zu prüfen", "Abgelehnt", "Drafts erstellt"):
        assert label in source, label
    assert "font-black" in source


# -- staggered result entrances -----------------------------------------------------------


def test_candidate_and_past_run_cards_are_staggered():
    source = _lead_finder_source()
    assert "visibleCandidates.map((candidate, index)" in source
    assert "pastRuns.map((pastRun, index)" in source
    assert "delayMs={Math.min(index, 6) * 60}" in source


# -- smooth scroll to results --------------------------------------------------------------


def test_smooth_scroll_to_result_after_search_and_show_run():
    source = _lead_finder_source()
    assert "resultRef" in source
    assert 'scrollIntoView({ behavior: "smooth"' in source


# -- safety still visible, still no send capability ---------------------------------------


def test_safety_still_visible_after_refinement():
    home_source = _home_source()
    settings_source = _read("app/settings/page.tsx")
    assert "SafetyBlock" in home_source
    assert "Kein automatischer Versand" in settings_source
    assert "Do-not-contact aktiv" in settings_source
