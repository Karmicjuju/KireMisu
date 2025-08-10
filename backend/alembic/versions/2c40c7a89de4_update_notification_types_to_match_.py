"""update_notification_types_to_match_frontend

Revision ID: 2c40c7a89de4
Revises: 08f7d07d6897
Create Date: 2025-08-10 01:13:54.557197

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2c40c7a89de4"
down_revision = "08f7d07d6897"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Update notification types to match frontend expectations."""
    # Drop the old constraint
    op.drop_constraint("ck_notification_type", "notifications", type_="check")

    # Add the new constraint with extended types
    op.create_check_constraint(
        "ck_notification_type",
        "notifications",
        "notification_type IN ('new_chapter', 'chapter_available', 'download_complete', 'download_failed', 'series_complete', 'library_update', 'system_alert', 'series_update')",
    )


def downgrade() -> None:
    """Revert notification types to original constraint."""
    # Drop the new constraint
    op.drop_constraint("ck_notification_type", "notifications", type_="check")

    # Restore the original constraint
    op.create_check_constraint(
        "ck_notification_type",
        "notifications",
        "notification_type IN ('new_chapter', 'series_update', 'system_alert', 'download_complete')",
    )
