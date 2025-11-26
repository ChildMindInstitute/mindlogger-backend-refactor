"""Add mfa_disabled_at to users table

Revision ID: 515df3312e1c
Revises: 476c854a8417
Create Date: 2025-11-26 11:39:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "515df3312e1c"
down_revision = "476c854a8417"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add mfa_disabled_at column to track when MFA was disabled."""
    op.add_column(
        "users",
        sa.Column(
            "mfa_disabled_at",
            sa.DateTime(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Remove mfa_disabled_at column from users table."""
    op.drop_column("users", "mfa_disabled_at")
