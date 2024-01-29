"""add_missing_status_pending_to_type_job_status

Revision ID: 78eaf61f48bf
Revises: 46f285831ae8
Create Date: 2024-01-26 17:23:35.592527

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "78eaf61f48bf"
down_revision = "46f285831ae8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "alter type job_status add value 'pending' before 'in_progress';"
        )
    )


def downgrade() -> None:
    pass
