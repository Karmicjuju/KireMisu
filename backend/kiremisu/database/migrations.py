"""Simple migration utilities for safer database changes."""

import logging
from typing import Dict, List, Optional

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .connection import get_db_session

logger = logging.getLogger(__name__)


async def get_current_revision() -> Optional[str]:
    """Get the current database revision."""
    try:
        async with get_db_session() as session:
            result = await session.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
            row = result.fetchone()
            return row[0] if row else None
    except Exception as e:
        logger.warning(f"Could not get current revision: {e}")
        return None


async def validate_migration_safety() -> Dict[str, bool]:
    """Basic validation checks before running migrations."""
    checks = {
        "database_accessible": False,
        "no_active_connections": False,
        "backup_recommended": False,
    }

    try:
        # Check database accessibility
        async with get_db_session() as session:
            await session.execute(text("SELECT 1"))
            checks["database_accessible"] = True

        # Basic connection count check (PostgreSQL specific)
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    text("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
                )
                active_connections = result.scalar()
                checks["no_active_connections"] = active_connections <= 5  # Reasonable threshold
        except Exception:
            # If we can't check, assume it's okay for other databases
            checks["no_active_connections"] = True

        # Always recommend backup for production
        checks["backup_recommended"] = True

    except Exception as e:
        logger.error(f"Migration validation failed: {e}")

    return checks


def create_migration_with_template(name: str, message: str = "") -> str:
    """Create a new migration file with a basic template."""
    try:
        config = Config("alembic.ini")

        # Create the migration
        command.revision(config, message=name, autogenerate=True)

        logger.info(f"Created migration: {name}")
        return f"Migration '{name}' created successfully"

    except Exception as e:
        logger.error(f"Failed to create migration: {e}")
        raise


async def run_migration_with_checks(target_revision: str = "head") -> Dict[str, any]:
    """Run migration with basic safety checks."""
    result = {
        "success": False,
        "current_revision": None,
        "target_revision": target_revision,
        "checks": {},
        "error": None,
    }

    try:
        # Get current state
        result["current_revision"] = await get_current_revision()

        # Run validation checks
        result["checks"] = await validate_migration_safety()

        # Check if migration is safe to run
        if not result["checks"]["database_accessible"]:
            raise Exception("Database is not accessible")

        if not result["checks"]["no_active_connections"]:
            logger.warning("High number of active connections detected")

        # Run the migration
        config = Config("alembic.ini")
        command.upgrade(config, target_revision)

        result["success"] = True
        logger.info(f"Migration completed successfully to {target_revision}")

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Migration failed: {e}")

    return result


async def get_migration_history() -> List[Dict[str, str]]:
    """Get a simple migration history."""
    try:
        config = Config("alembic.ini")
        script = ScriptDirectory.from_config(config)

        history = []
        for revision in script.walk_revisions():
            history.append(
                {
                    "revision": revision.revision,
                    "down_revision": revision.down_revision,
                    "description": revision.doc or "No description",
                    "is_current": False,  # We'll mark current one separately
                }
            )

        # Mark current revision
        current = await get_current_revision()
        if current:
            for item in history:
                if item["revision"] == current:
                    item["is_current"] = True
                    break

        return history

    except Exception as e:
        logger.error(f"Failed to get migration history: {e}")
        return []


# Simple migration templates for common operations
MIGRATION_TEMPLATES = {
    "add_column": """
# Add column migration template
def upgrade() -> None:
    op.add_column('table_name', sa.Column('column_name', sa.String(255), nullable=True))

def downgrade() -> None:
    op.drop_column('table_name', 'column_name')
""",
    "add_index": """
# Add index migration template  
def upgrade() -> None:
    op.create_index('ix_table_column', 'table_name', ['column_name'])

def downgrade() -> None:
    op.drop_index('ix_table_column', 'table_name')
""",
    "add_constraint": """
# Add constraint migration template
def upgrade() -> None:
    op.create_check_constraint('ck_table_constraint', 'table_name', 'constraint_condition')

def downgrade() -> None:
    op.drop_constraint('ck_table_constraint', 'table_name')
""",
}
