"""merge_migration_heads

Revision ID: 313f5220df15
Revises: 09c754a38e7a, a1b2c3d4e5f6, add_tag_color_constraint, ee80c53ea31c
Create Date: 2025-08-07 14:53:17.481192

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "313f5220df15"
down_revision = ("09c754a38e7a", "a1b2c3d4e5f6", "add_tag_color_constraint", "ee80c53ea31c")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
