"""Phase: premium interactions & animations — regression checks for the
motion system, new Toast/Skeleton components, the Lead Finder's search-
progress/filter/sort/search/diagnose features, and the Settings status
polish.

Same source-level approach as the other `test_frontend_*` files (no Jest/
RTL in this project, see test_frontend_safety.py) — these assert the
pieces exist and are wired in, without re-testing behavior already
covered elsewhere. Complements (does not replace) `npx tsc --noEmit` +
`npm run build`.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND = REPO_ROOT / "frontend"


def _read(path: str) -> str:
    return (FRONTEND / path).read_text(encoding="utf-8")


def _lead_finder_source() -> str:
    return _read("components/lead-finder/LeadFinderApp.tsx")


# -- no new dependency was introduced ---------------------------------------------------


def test_no_animation_library_dependency_was_added():
    """PROJECT_RULES.md: prefer what's already in the stack. This phase
    uses Tailwind/CSS transitions + a small React context, not a new
    animation library."""
    package_json = json.loads(_read("package.json"))
    all_deps = {**package_json.get("dependencies", {}), **package_json.get("devDependencies", {})}
    for forbidden in ("framer-motion", "gsap", "react-spring", "@react-spring/web", "motion"):
        assert forbidden not in all_deps, forbidden


# -- animation infrastructure ------------------------------------------------------------


def test_tailwind_config_defines_the_motion_utilities():
    source = _read("tailwind.config.ts")
    for name in ("fade-in-up", "fade-in", "scale-in", "pulse-soft"):
        assert name in source, name


def test_globals_css_respects_reduced_motion():
    source = _read("app/globals.css")
    assert "prefers-reduced-motion" in source


def test_page_transition_template_exists():
    source = _read("app/template.tsx")
    assert '"use client"' in source
    assert "animate-fade-in-up" in source


# -- toast system -------------------------------------------------------------------------


def test_toast_provider_exists_and_is_wired_into_the_app_shell():
    provider_source = _read("components/ui/ToastProvider.tsx")
    assert "useToast" in provider_source
    assert "showToast" in provider_source

    shell_source = _read("components/layout/AppShell.tsx")
    assert "ToastProvider" in shell_source


def test_lead_finder_shows_toasts_for_success_and_error():
    source = _lead_finder_source()
    assert "useToast" in source
    assert 'showToast(' in source
    assert '"success"' in source
    assert '"error"' in source


# -- skeleton loader ----------------------------------------------------------------------


def test_skeleton_component_exists_and_is_used_by_lead_finder():
    skeleton_source = _read("components/ui/Skeleton.tsx")
    assert "animate-pulse" in skeleton_source
    assert "SkeletonRunCard" in skeleton_source

    source = _lead_finder_source()
    assert "SkeletonRunCard" in source


# -- search progress stepper --------------------------------------------------------------


def test_lead_finder_shows_a_four_step_search_progress_indicator():
    source = _lead_finder_source()
    for step in ("Firmen suchen", "Websites prüfen", "Fit bewerten", "Review vorbereiten"):
        assert step in source, step


# -- filter / sort / search over results --------------------------------------------------


def test_lead_finder_has_result_filter_tabs():
    source = _lead_finder_source()
    for label in ("Alle", "Zu prüfen", "Qualifiziert", "Abgelehnt"):
        assert f'"{label}"' in source, label


def test_lead_finder_has_sort_and_search_controls():
    source = _lead_finder_source()
    assert "sortByScore" in source
    assert "Suche in Ergebnissen" in source


# -- run diagnose collapsible + clearer website button + animated score ------------------


def test_lead_finder_run_diagnose_is_collapsible():
    source = _lead_finder_source()
    assert "Run-Diagnose" in source
    assert "<details" in source


def test_lead_finder_has_a_clear_website_button():
    source = _lead_finder_source()
    assert "Website öffnen" in source


def test_lead_finder_score_badge_has_entrance_animation():
    source = _lead_finder_source()
    assert "animate-scale-in" in source


def test_lead_finder_candidate_details_expand_is_animated():
    source = _lead_finder_source()
    assert "grid-template-rows" in source


# -- microinteractions: Button/Card polish ------------------------------------------------


def test_button_has_pressed_state():
    source = _read("components/ui/Button.tsx")
    assert "active:scale" in source


def test_card_supports_interactive_hover_lift():
    source = _read("components/ui/Card.tsx")
    assert "interactive" in source
    assert "hover:-translate-y" in source


# -- Settings: nicer live status + degraded/Redis explainer -------------------------------


def test_settings_explains_degraded_backend_status_in_plain_language():
    source = _read("app/settings/page.tsx")
    assert "Redis" in source
    assert "Rate Limiting" in source
    assert "Kein Fehlerzustand" in source


def test_settings_lead_sourcing_status_uses_the_richer_status_pill():
    source = _read("app/settings/page.tsx")
    assert "<StatusPill" in source


# -- safety still visible (spot check; full coverage in test_frontend_safety.py) ----------


def test_home_still_has_the_safety_block():
    source = _read("app/page.tsx")
    assert "SafetyBlock" in source
    assert "Kein automatischer Versand" in source
