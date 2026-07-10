"""Sanity checks for the Alembic migration setup (Phase 35).

Deliberately offline/no-database: these only verify the configuration
files, the env.py module, and the migration graph are structurally sound
— not that a real database migrates cleanly (that was verified manually
against both a fresh and the project's existing dev database via
``alembic check``; see DEPLOYMENT.md section 5).
"""

import configparser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = REPO_ROOT / "backend" / "infrastructure" / "database" / "migrations"


def test_alembic_ini_exists_and_points_at_the_migrations_package():
    ini_path = REPO_ROOT / "alembic.ini"
    assert ini_path.is_file()
    parser = configparser.ConfigParser()
    parser.read(ini_path)
    script_location = parser.get("alembic", "script_location")
    assert script_location == "backend/infrastructure/database/migrations"


def test_alembic_ini_does_not_hardcode_a_connection_string():
    """The real URL always comes from Settings.database_url (env.py) —
    alembic.ini itself must never contain a password."""
    ini_path = REPO_ROOT / "alembic.ini"
    parser = configparser.ConfigParser()
    parser.read(ini_path)
    assert parser.get("alembic", "sqlalchemy.url").strip() == ""


def test_migrations_env_and_script_template_exist():
    assert (MIGRATIONS_DIR / "env.py").is_file()
    assert (MIGRATIONS_DIR / "script.py.mako").is_file()
    assert (MIGRATIONS_DIR / "versions").is_dir()


def test_exactly_one_baseline_revision_exists_with_no_parent():
    """A single, linear baseline — if this ever fails because a second
    baseline (down_revision=None) was added by mistake, Alembic would
    see two disconnected heads."""
    versions_dir = MIGRATIONS_DIR / "versions"
    revision_files = list(versions_dir.glob("*.py"))
    assert len(revision_files) >= 1

    roots = []
    for path in revision_files:
        text = path.read_text(encoding="utf-8")
        if "down_revision: Union[str, None] = None" in text:
            roots.append(path.name)
    assert len(roots) == 1, f"expected exactly one root revision, found {roots}"


def test_env_module_wires_target_metadata_to_the_project_base():
    """Import env.py in isolation (not via `alembic` itself) just to
    confirm it references the project's real ORM metadata — without
    actually running migrations against any database."""
    import importlib.util

    from backend.infrastructure.database.base import Base

    spec = importlib.util.spec_from_file_location(
        "_alembic_env_under_test", MIGRATIONS_DIR / "env.py"
    )
    source = (MIGRATIONS_DIR / "env.py").read_text(encoding="utf-8")
    # env.py runs migrations as a side effect of being imported (that's how
    # Alembic itself invokes it) — assert on the source instead of
    # exec'ing the module, so this test never touches a database.
    assert "target_metadata = Base.metadata" in source
    assert "get_settings().database_url" in source
    assert spec is not None


def test_requirements_pin_alembic():
    requirements = (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "alembic==" in requirements


def test_dockerfile_copies_alembic_ini():
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "alembic.ini" in dockerfile
