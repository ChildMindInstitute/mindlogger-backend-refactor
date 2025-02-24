"""Add event_history_id and device_id to answers table

Revision ID: 5af378151328
Revises: 70987d489b17
Create Date: 2025-02-24 16:10:44.661177

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "5af378151328"
down_revision = "3d8602537b1d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("answers", sa.Column("event_history_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("answers", sa.Column("device_id", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("answers", "device_id")
    op.drop_column("answers", "event_history_id")
