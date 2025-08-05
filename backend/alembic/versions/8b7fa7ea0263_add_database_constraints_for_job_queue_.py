"""add database constraints for job queue validation

Revision ID: 8b7fa7ea0263
Revises: ad321789d335
Create Date: 2025-08-04 19:32:28.232099

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8b7fa7ea0263"
down_revision = "ad321789d335"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add check constraints for job queue validation
    op.create_check_constraint(
        "ck_job_queue_status",
        "job_queue",
        "status IN ('pending', 'running', 'completed', 'failed')",
    )
    op.create_check_constraint(
        "ck_job_queue_job_type", "job_queue", "job_type IN ('library_scan', 'download')"
    )
    op.create_check_constraint(
        "ck_job_queue_priority_range", "job_queue", "priority >= 1 AND priority <= 10"
    )
    op.create_check_constraint("ck_job_queue_retry_count", "job_queue", "retry_count >= 0")
    op.create_check_constraint("ck_job_queue_max_retries", "job_queue", "max_retries >= 0")


def downgrade() -> None:
    # Drop check constraints
    op.drop_constraint("ck_job_queue_max_retries", "job_queue")
    op.drop_constraint("ck_job_queue_retry_count", "job_queue")
    op.drop_constraint("ck_job_queue_priority_range", "job_queue")
    op.drop_constraint("ck_job_queue_job_type", "job_queue")
    op.drop_constraint("ck_job_queue_status", "job_queue")
