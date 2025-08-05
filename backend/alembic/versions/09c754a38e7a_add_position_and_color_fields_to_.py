"""add position and color fields to annotations

Revision ID: 09c754a38e7a
Revises: 8b7fa7ea0263
Create Date: 2025-08-04 21:17:54.646616

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '09c754a38e7a'
down_revision = '8b7fa7ea0263'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add position fields for page-specific annotation placement
    op.add_column('annotations', sa.Column('position_x', sa.Float(), nullable=True))
    op.add_column('annotations', sa.Column('position_y', sa.Float(), nullable=True))
    
    # Add color field for annotation customization
    op.add_column('annotations', sa.Column('color', sa.String(length=7), nullable=True))
    
    # Add check constraints for position validation (0-1 normalized)
    op.create_check_constraint(
        'ck_annotations_position_x_range',
        'annotations',
        'position_x IS NULL OR (position_x >= 0 AND position_x <= 1)'
    )
    op.create_check_constraint(
        'ck_annotations_position_y_range',
        'annotations',
        'position_y IS NULL OR (position_y >= 0 AND position_y <= 1)'
    )
    
    # Add check constraint for color format validation (hex color)
    op.create_check_constraint(
        'ck_annotations_color_format',
        'annotations',
        "color IS NULL OR color ~ '^#[0-9A-Fa-f]{6}$'"
    )


def downgrade() -> None:
    # Drop check constraints
    op.drop_constraint('ck_annotations_color_format', 'annotations')
    op.drop_constraint('ck_annotations_position_y_range', 'annotations')
    op.drop_constraint('ck_annotations_position_x_range', 'annotations')
    
    # Drop columns
    op.drop_column('annotations', 'color')
    op.drop_column('annotations', 'position_y')
    op.drop_column('annotations', 'position_x')