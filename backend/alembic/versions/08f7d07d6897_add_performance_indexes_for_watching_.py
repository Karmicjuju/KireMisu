"""add_performance_indexes_for_watching_system

Revision ID: 08f7d07d6897
Revises: 38aab752f786
Create Date: 2025-08-10 01:12:59.745420

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "08f7d07d6897"
down_revision = "38aab752f786"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add performance indexes for watching system."""
    # Create indexes only if they don't exist
    from sqlalchemy import text

    connection = op.get_bind()

    # Index on series.watching_enabled for filtering watched series
    result = connection.execute(
        text("SELECT indexname FROM pg_indexes WHERE indexname = 'ix_series_watching_enabled'")
    )
    if not result.fetchone():
        op.create_index(
            "ix_series_watching_enabled",
            "series",
            ["watching_enabled"],
            postgresql_where=sa.text("watching_enabled = true"),
        )

    # Composite index on notifications.series_id and is_read for efficient filtering
    result = connection.execute(
        text(
            "SELECT indexname FROM pg_indexes WHERE indexname = 'ix_notifications_series_id_is_read'"
        )
    )
    if not result.fetchone():
        op.create_index(
            "ix_notifications_series_id_is_read", "notifications", ["series_id", "is_read"]
        )

    # Index on notifications.is_read for unread notifications filtering
    result = connection.execute(
        text("SELECT indexname FROM pg_indexes WHERE indexname = 'ix_notifications_is_read'")
    )
    if not result.fetchone():
        op.create_index(
            "ix_notifications_is_read",
            "notifications",
            ["is_read"],
            postgresql_where=sa.text("is_read = false"),
        )

    # Index on notifications.created_at for ordering (most recent first)
    result = connection.execute(
        text(
            "SELECT indexname FROM pg_indexes WHERE indexname = 'ix_notifications_created_at_desc'"
        )
    )
    if not result.fetchone():
        op.create_index(
            "ix_notifications_created_at_desc", "notifications", [sa.text("created_at DESC")]
        )

    # Composite index for notifications API queries (unread + ordering)
    result = connection.execute(
        text(
            "SELECT indexname FROM pg_indexes WHERE indexname = 'ix_notifications_is_read_created_at'"
        )
    )
    if not result.fetchone():
        op.create_index(
            "ix_notifications_is_read_created_at",
            "notifications",
            ["is_read", sa.text("created_at DESC")],
        )


def downgrade() -> None:
    """Remove performance indexes for watching system."""
    op.drop_index("ix_notifications_is_read_created_at", "notifications")
    op.drop_index("ix_notifications_created_at_desc", "notifications")
    op.drop_index("ix_notifications_is_read", "notifications")
    op.drop_index("ix_notifications_series_id_is_read", "notifications")
    op.drop_index("ix_series_watching_enabled", "series")
