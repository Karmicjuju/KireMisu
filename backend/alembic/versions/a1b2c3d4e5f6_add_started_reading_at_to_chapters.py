"""Add started_reading_at field to chapters

Revision ID: a1b2c3d4e5f6
Revises: cf4815a2275e
Create Date: 2025-08-06 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'cf4815a2275e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add started_reading_at field to chapters table."""
    # Add started_reading_at field to chapters table
    op.add_column('chapters', sa.Column('started_reading_at', sa.DateTime(), nullable=True))
    
    # Create index on started_reading_at for performance
    op.create_index('ix_chapters_started_reading_at', 'chapters', ['started_reading_at'])


def downgrade() -> None:
    """Remove started_reading_at field from chapters table."""
    # Drop index first
    op.drop_index('ix_chapters_started_reading_at', table_name='chapters')
    
    # Drop column
    op.drop_column('chapters', 'started_reading_at')