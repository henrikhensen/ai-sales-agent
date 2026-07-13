"""Fix: the login/register pages were the actual first impression for
anyone visiting the deployed app without a session (RequireAuth redirects
there), but had never been touched by the dark-editorial redesign — they
still looked like a bare admin form with the full internal Sidebar/Header
chrome around it. This is what a user reported as "design wasn't applied"
when checking the live Railway URL logged out.

Same source-level approach as the other `test_frontend_*` files (no Jest/
RTL in this project, see test_frontend_safety.py).
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND = REPO_ROOT / "frontend"


def _read(path: str) -> str:
    return (FRONTEND / path).read_text(encoding="utf-8")


def test_app_shell_hides_the_internal_sidebar_on_auth_routes():
    source = _read("components/layout/AppShell.tsx")
    assert '"/login"' in source
    assert '"/register"' in source
    assert "AUTH_ROUTES" in source


def test_header_menu_button_is_optional():
    source = _read("components/layout/Header.tsx")
    assert "showMenuButton" in source


def test_login_and_register_have_the_premium_hero_treatment():
    for page in ("app/login/page.tsx", "app/register/page.tsx"):
        source = _read(page)
        assert "mono-label" in source
        assert 'variant="framed"' in source
        assert "font-black" in source


def test_login_and_register_no_longer_use_a_bulleted_amber_wall():
    for page in ("app/login/page.tsx", "app/register/page.tsx"):
        source = _read(page)
        assert "<ul" not in source
        assert "bg-amber" not in source
