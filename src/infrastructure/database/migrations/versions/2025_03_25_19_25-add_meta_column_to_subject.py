"""Add meta column to subject

Revision ID: 795b9d9844ed
Revises: 6fb25329f7b1
Create Date: 2025-03-25 19:25:30.372404

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "795b9d9844ed"
down_revision = "6fb25329f7b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("subjects", sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # Create a GIN index on the meta column
    op.create_index("idx_subjects_meta", "subjects", ["meta"], postgresql_using="gin")


def downgrade() -> None:
    # Drop the GIN index
    op.drop_index("idx_subjects_meta", table_name="subjects")

    op.drop_column("subjects", "meta")
