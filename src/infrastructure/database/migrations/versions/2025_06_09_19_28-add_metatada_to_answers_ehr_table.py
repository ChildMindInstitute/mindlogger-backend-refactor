"""Add metatada to answers_ehr table

Revision ID: b07ca71c94df
Revises: a05c838b8aad
Create Date: 2025-06-09 19:28:53.536034

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b07ca71c94df"
down_revision = "a05c838b8aad"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("answers_ehr", sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("answers_ehr", "meta")
