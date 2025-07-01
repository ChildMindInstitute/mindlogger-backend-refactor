"""Add index to activty_items.activity_id

Revision ID: 8ec71571fa71
Revises: b07ca71c94df
Create Date: 2025-06-26 14:06:16.610355

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "8ec71571fa71"
down_revision = "b07ca71c94df"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(op.f("ix_activity_items_activity_id"), "activity_items", ["activity_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_activity_items_activity_id"), table_name="activity_items")
