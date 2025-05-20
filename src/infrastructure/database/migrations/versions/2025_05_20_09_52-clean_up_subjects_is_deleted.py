"""Clean up the subjects table is_deleted column

Revision ID: a05c838b8aad
Revises: 9b882445f218
Create Date: 2025-05-20 09:52:05.737528

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "a05c838b8aad"
down_revision = "9b882445f218"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("subjects", sa.Column("is_deleted_null", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.execute(sa.text("UPDATE subjects SET is_deleted_null = TRUE, is_deleted = FALSE WHERE is_deleted IS NULL"))

    # Alter the is_deleted column to be non-nullable
    op.alter_column(
        "subjects",
        "is_deleted",
        existing_type=sa.Boolean(),
        nullable=False,
    )


def downgrade() -> None:
    op.execute(sa.text("UPDATE subjects SET is_deleted = NULL WHERE is_deleted IS FALSE AND is_deleted_null IS TRUE"))
    op.drop_column("subjects", "is_deleted_null")
