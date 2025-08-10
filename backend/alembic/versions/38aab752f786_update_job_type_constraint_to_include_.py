"""update job_type constraint to include chapter_update_check

Revision ID: 38aab752f786
Revises: 6a902a049b26
Create Date: 2025-08-09 01:30:44.311670

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '38aab752f786'
down_revision = '6a902a049b26'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the existing job_type constraint
    op.drop_constraint("ck_job_queue_job_type", "job_queue")
    
    # Create new constraint that includes chapter_update_check
    op.create_check_constraint(
        "ck_job_queue_job_type",
        "job_queue", 
        "job_type IN ('library_scan', 'download', 'chapter_update_check')"
    )


def downgrade() -> None:
    # Drop the updated constraint
    op.drop_constraint("ck_job_queue_job_type", "job_queue")
    
    # Restore the original constraint
    op.create_check_constraint(
        "ck_job_queue_job_type", 
        "job_queue", 
        "job_type IN ('library_scan', 'download')"
    )