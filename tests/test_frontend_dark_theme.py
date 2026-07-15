"""Phase: dark editorial brand theme — regression checks for the central
color tokens and the app-wide light-to-dark retint.

Same source-level approach as the other `test_frontend_*` files (no Jest/
RTL in this project, see test_frontend_safety.py). These assert: the four
brand colors are defined in exactly one place (CSS variables + matching
Tailwind theme colors), the global canvas/text defaults are dark, the
shared design-system components no longer default to white/near-black-
on-white, and no page anywhere still carries a pale (`-50`/`-100`)
color-wash "wall" — the exact anti-pattern ("gelbe Warnwüste") the brand
brief called out.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND = REPO_ROOT / "frontend"

# The exact four brand colors from the brief.
BRAND_HEX = {
    "bg": "#1A0B12",
    "surface": "#3D1022",
    "muted": "#E3C5BB",
    "white": "#FFFFFF",
}


def _read(path: str) -> str:
    return (FRONTEND / path).read_text(encoding="utf-8")


def _all_frontend_source_files():
    for directory in ("app", "components"):
        yield from (FRONTEND / directory).rglob("*.tsx")


# -- central tokens -----------------------------------------------------------------------


def test_css_variables_define_the_exact_brand_palette():
    source = _read("app/globals.css").lower()
    assert "--color-bg: #1a0b12" in source
    assert "--color-surface: #3d1022" in source
    assert "--color-muted: #e3c5bb" in source
    assert "--color-white: #ffffff" in source


def test_tailwind_config_defines_matching_canvas_surface_muted_colors():
    source = _read("tailwind.config.ts").lower()
    assert 'canvas: "#1a0b12"' in source
    assert 'surface: "#3d1022"' in source
    assert 'muted: "#e3c5bb"' in source


def test_html_base_is_dark_canvas_with_muted_text():
    source = _read("app/globals.css")
    assert "bg-canvas text-muted" in source


# -- global layout is dark, not a white canvas with dark accents ------------------------


def test_app_shell_main_canvas_is_dark():
    source = _read("components/layout/AppShell.tsx")
    assert "bg-canvas" in source
    assert "bg-white" not in source


def test_header_and_sidebar_use_the_brand_palette():
    header = _read("components/layout/Header.tsx")
    sidebar = _read("components/layout/Sidebar.tsx")
    assert "bg-canvas" in header
    assert "bg-canvas" in sidebar
    assert "bg-white" not in header
    assert "bg-white" not in sidebar


# -- shared components default to the dark surface, not white --------------------------


def test_card_defaults_to_surface_not_white():
    source = _read("components/ui/Card.tsx")
    assert "bg-surface" in source
    # `bg-white/[0.03]` (a barely-there translucent tint on the `flat`
    # variant) is fine — a solid opaque `bg-white` fill is not.
    assert not re.search(r"\bbg-white\b(?!/)", source)


def test_inputs_are_dark_surfaces():
    for name in ("Input", "Select", "Textarea"):
        source = _read(f"components/ui/{name}.tsx")
        assert "bg-canvas" in source, name
        assert "bg-white" not in source, name


def test_badge_tones_are_translucent_not_solid_pale_fills():
    """Status badges must read as quiet tinted chips on a dark surface,
    never a bright green/blue/yellow block."""
    source = _read("components/ui/Badge.tsx")
    assert "bg-white/10" in source or "/10" in source
    assert "bg-emerald-100" not in source
    assert "bg-amber-100" not in source


def test_compliance_notice_is_no_longer_a_bright_amber_wall():
    source = _read("components/ui/ComplianceNotice.tsx")
    assert "bg-amber-50" not in source
    assert "amber-400/10" in source


# -- standing regression: no pale (-50/-100) color-wash wall anywhere -------------------


PALE_WASH_PATTERN = re.compile(
    r"\b(?:bg)-(?:emerald|rose|amber|blue|indigo|sky|violet|cyan|teal|purple|orange|red|yellow|green|pink|fuchsia|lime)-(?:50|100)\b"
)


def test_no_pale_color_wash_backgrounds_remain_anywhere():
    offending: list[str] = []
    for file in _all_frontend_source_files():
        for line_no, line in enumerate(file.read_text(encoding="utf-8").splitlines(), start=1):
            if PALE_WASH_PATTERN.search(line):
                offending.append(f"{file}:{line_no}: {line.strip()}")
    assert offending == [], "\n".join(offending)


def test_no_stray_bg_white_row_cards_remain_in_secondary_pages():
    """`bg-white` as a literal background is only acceptable for the rare,
    deliberate strong-accent spots (the hero CTA, the `dark` Button/Card
    variant text) — never as an ordinary card/row background."""
    allowed_files = {
        FRONTEND / "app" / "page.tsx",  # hero CTA, sparing white accent
        FRONTEND / "components" / "ui" / "Button.tsx",  # `dark` variant
    }
    offending: list[str] = []
    for file in _all_frontend_source_files():
        if file in allowed_files:
            continue
        for line_no, line in enumerate(file.read_text(encoding="utf-8").splitlines(), start=1):
            if re.search(r"\bbg-white\b(?!/)", line):
                offending.append(f"{file}:{line_no}: {line.strip()}")
    assert offending == [], "\n".join(offending)


# -- safety still visible on the new dark theme -----------------------------------------


def test_safety_guarantees_still_visible_on_dark_theme():
    home_source = _read("app/page.tsx")
    settings_source = _read("app/settings/page.tsx")
    assert "SafetyBlock" in home_source
    assert "Kein automatischer Versand" in home_source
    assert "Kein automatischer Versand" in settings_source
    assert "Do-not-contact aktiv" in settings_source
