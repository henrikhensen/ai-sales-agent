"""Phase: Stodio-inspired editorial redesign — regression checks specific to
the new components and design tokens this phase introduces (`Counter`,
`FaqAccordion`, `HeroVisual`, `ServiceList`, `HomeFooter`, the `.container-app`
token, the sticky/CTA Header change, the `min_score` default fix).

Same source-level approach as the other `test_frontend_*` files (no Jest/
RTL in this project, see test_frontend_safety.py) — layout/typography/
motion/spacing tokens were measured from the live stodio.webflow.io site
during implementation (browser screenshots + its own compiled CSS), not
copied as an asset; the reference itself is never fetched by the app or by
these tests.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND = REPO_ROOT / "frontend"

NEW_FILES = [
    "components/ui/Counter.tsx",
    "components/ui/FaqAccordion.tsx",
    "components/home/HeroVisual.tsx",
    "components/home/ServiceList.tsx",
    "components/home/HomeFooter.tsx",
]


def _read(path: str) -> str:
    return (FRONTEND / path).read_text(encoding="utf-8")


# -- new components exist ----------------------------------------------------------------


def test_new_components_exist():
    for path in NEW_FILES:
        assert (FRONTEND / path).is_file(), path


# -- design tokens: single source of truth ------------------------------------------------


def test_container_app_token_defined_once_in_globals_css():
    source = _read("app/globals.css")
    assert ".container-app" in source
    assert "max-w-[1440px]" in source


def test_home_page_uses_the_container_app_token():
    source = _read("app/page.tsx")
    assert "container-app" in source


# -- no animation library added; motion stays Tailwind/CSS-only --------------------------


def test_no_new_animation_dependency():
    import json

    package_json = json.loads(_read("package.json"))
    all_deps = {**package_json.get("dependencies", {}), **package_json.get("devDependencies", {})}
    for forbidden in ("framer-motion", "gsap", "react-spring", "@react-spring/web", "motion"):
        assert forbidden not in all_deps, forbidden


# -- Counter: reduced-motion aware, no CSS keyframe dependency ----------------------------


def test_counter_respects_reduced_motion_and_intersection_observer():
    source = _read("components/ui/Counter.tsx")
    assert "IntersectionObserver" in source
    assert "prefers-reduced-motion" in source


# -- FaqAccordion: accessible, keyboard-operable, one-open-at-a-time ---------------------


def test_faq_accordion_is_keyboard_accessible():
    source = _read("components/ui/FaqAccordion.tsx")
    assert "aria-expanded" in source
    assert "aria-controls" in source
    assert "<button" in source


def test_home_faq_uses_faq_accordion_component():
    source = _read("app/page.tsx")
    assert "<FaqAccordion" in source


# -- ServiceList (Funktionsbereiche): real buttons, not hover-only ------------------------


def test_service_list_rows_are_keyboard_operable_buttons():
    source = _read("components/home/ServiceList.tsx")
    assert "<button" in source
    assert "aria-expanded" in source


def test_home_uses_service_list_for_funktionsbereiche():
    source = _read("app/page.tsx")
    assert "<ServiceList" in source


# -- HeroVisual: original, no photos/gradients --------------------------------------------


def test_hero_visual_is_pure_svg_no_gradient():
    source = _read("components/home/HeroVisual.tsx")
    assert "<svg" in source
    assert "linearGradient" not in source
    assert "radialGradient" not in source


def test_home_renders_hero_visual():
    source = _read("app/page.tsx")
    assert "<HeroVisual" in source


# -- HomeFooter: real routes, no dead legal link, safety line kept ------------------------


def test_home_footer_links_to_real_compliance_routes():
    source = _read("components/home/HomeFooter.tsx")
    assert "/compliance/status" in source
    assert "/compliance/do-not-contact" in source


# -- no pills / gradients / glassmorphism in the new home-specific files ------------------


PILL_PATTERN = re.compile(r"\brounded-full\b")
GRADIENT_PATTERN = re.compile(r"gradient")
GLASS_PATTERN = re.compile(r"backdrop-blur")

# Small circular status dots (h-1.5 w-1.5 rounded-full) are an existing,
# already-established app-wide pattern (Header, StatusPill) — not a "pill
# button" in the sense the brief warns against. Scoped to the new
# home-specific composition files only, not the whole app.
NEW_HOME_FILES = [
    "components/home/HeroVisual.tsx",
    "components/home/ServiceList.tsx",
    "components/home/HomeFooter.tsx",
]


def test_new_home_files_have_no_pill_buttons_gradients_or_glassmorphism():
    offending: list[str] = []
    for path in NEW_HOME_FILES:
        source = _read(path)
        for line_no, line in enumerate(source.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            if GRADIENT_PATTERN.search(line) or GLASS_PATTERN.search(line):
                offending.append(f"{path}:{line_no}: {line.strip()}")
            if PILL_PATTERN.search(line) and "h-1.5" not in line and "h-2" not in line:
                offending.append(f"{path}:{line_no}: {line.strip()}")
    assert offending == [], "\n".join(offending)


# -- Header: sticky nav + prominent, additive Lead Finder CTA ----------------------------


def test_header_is_sticky():
    source = _read("components/layout/Header.tsx")
    assert "sticky top-0" in source


def test_header_has_a_prominent_lead_finder_cta():
    source = _read("components/layout/Header.tsx")
    assert 'href="/lead-finder"' in source
    assert "Lead Finder starten" in source


# -- AppShell: mobile drawer is no longer instant show/hide -------------------------------


def test_mobile_drawer_has_an_entrance_animation():
    source = _read("components/layout/AppShell.tsx")
    assert "animate-slide-in-left" in source


def test_tailwind_defines_the_slide_in_left_keyframe():
    source = _read("tailwind.config.ts")
    assert "slide-in-left" in source


# -- Lead Finder: min_score default is 0, per the brief -----------------------------------


def test_lead_finder_min_score_default_is_zero():
    source = _read("components/lead-finder/LeadFinderApp.tsx")
    assert 'min_score: "0"' in source


# -- safety unchanged: still no send-capable UI in any new file --------------------------


def test_no_send_button_label_in_new_files():
    pattern = re.compile(r"\bSenden\b|\bVersenden\b")
    offending: list[str] = []
    all_new = NEW_FILES + ["app/page.tsx", "components/layout/Header.tsx", "components/layout/AppShell.tsx"]
    for path in all_new:
        for line in _read(path).splitlines():
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            if pattern.search(line):
                offending.append(f"{path}: {line.strip()}")
    assert offending == []
