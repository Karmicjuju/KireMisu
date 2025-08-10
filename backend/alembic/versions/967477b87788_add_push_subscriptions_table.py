"""add_push_subscriptions_table

Revision ID: 967477b87788
Revises: 2c40c7a89de4
Create Date: 2025-08-10 09:29:29.823025

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "967477b87788"
down_revision = "2c40c7a89de4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create push_subscriptions table
    op.create_table(
        "push_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("keys", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_used", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "endpoint IS NOT NULL AND endpoint != ''",
            name="ck_push_subscription_endpoint_not_empty",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("endpoint"),
    )
    # Create indexes
    op.create_index(
        "ix_push_subscriptions_active", "push_subscriptions", ["is_active"], unique=False
    )
    op.create_index(
        "ix_push_subscriptions_endpoint", "push_subscriptions", ["endpoint"], unique=False
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_push_subscriptions_endpoint", table_name="push_subscriptions")
    op.drop_index("ix_push_subscriptions_active", table_name="push_subscriptions")
    # Drop table
    op.drop_table("push_subscriptions")
