"""Add time_zone field to user_device_events_history

Revision ID: 6fb25329f7b1
Revises: 5658857a84dc
Create Date: 2025-03-20 22:38:11.454125

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "6fb25329f7b1"
down_revision = "5658857a84dc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_device_events_history", sa.Column("time_zone", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("user_device_events_history", "time_zone")
