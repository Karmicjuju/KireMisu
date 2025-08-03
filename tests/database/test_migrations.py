"""Test database migrations."""

import pytest
from pathlib import Path


def test_migration_file_exists() -> None:
    """Test that the initial migration file exists and is readable."""
    project_root = Path(__file__).parent.parent.parent
    versions_dir = project_root / "backend" / "alembic" / "versions"

    # Check that versions directory exists
    assert versions_dir.exists(), "Alembic versions directory should exist"

    # Check that at least one migration file exists
    migration_files = list(versions_dir.glob("*.py"))
    assert len(migration_files) > 0, "At least one migration file should exist"

    # Check that the initial migration file contains expected content
    initial_migration = migration_files[0]  # Assuming first file is our initial migration
    content = initial_migration.read_text()

    # Verify key table creation commands are present
    assert 'create_table(\n        "series"' in content, (
        "Series table creation should be in migration"
    )
    assert 'create_table(\n        "chapters"' in content, (
        "Chapters table creation should be in migration"
    )
    assert 'create_table(\n        "annotations"' in content, (
        "Annotations table creation should be in migration"
    )
    assert 'create_table(\n        "library_paths"' in content, (
        "Library paths table creation should be in migration"
    )

    # Verify essential indexes are created
    assert "ix_series_title_primary" in content, "Series title index should be created"
    assert "ix_chapters_series_id" in content, "Chapters series_id index should be created"
    assert "ix_chapters_series_ordering" in content, "Chapters ordering index should be created"

    # Verify foreign key constraints
    assert "ForeignKeyConstraint" in content, "Foreign key constraints should be present"


def test_migration_syntax() -> None:
    """Test that the migration file has valid Python syntax."""
    project_root = Path(__file__).parent.parent.parent
    versions_dir = project_root / "backend" / "alembic" / "versions"

    migration_files = list(versions_dir.glob("*.py"))
    assert len(migration_files) > 0, "Migration files should exist"

    for migration_file in migration_files:
        # Test that the file compiles without syntax errors
        content = migration_file.read_text()
        try:
            compile(content, str(migration_file), "exec")
        except SyntaxError as e:
            pytest.fail(f"Syntax error in migration file {migration_file}: {e}")


def test_alembic_config_exists() -> None:
    """Test that Alembic configuration files exist."""
    project_root = Path(__file__).parent.parent.parent
    backend_dir = project_root / "backend"

    # Check alembic.ini exists
    alembic_ini = backend_dir / "alembic.ini"
    assert alembic_ini.exists(), "alembic.ini should exist"

    # Check alembic directory exists
    alembic_dir = backend_dir / "alembic"
    assert alembic_dir.exists(), "alembic directory should exist"

    # Check env.py exists
    env_py = alembic_dir / "env.py"
    assert env_py.exists(), "alembic/env.py should exist"

    # Verify env.py contains our synchronous configuration
    env_content = env_py.read_text()
    assert "psycopg2" in env_content, "env.py should use psycopg2 for sync operations"
    assert "asyncpg" in env_content, "env.py should convert from asyncpg URL"
