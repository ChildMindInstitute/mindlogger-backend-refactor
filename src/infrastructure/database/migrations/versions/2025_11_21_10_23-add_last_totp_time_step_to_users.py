"""add_last_totp_time_step_to_users

Revision ID: f807ab168637
Revises: g1h2i3j4k5l6
Create Date: 2025-11-21 10:23:29.324495

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "f807ab168637"
down_revision = "g1h2i3j4k5l6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add last_totp_time_step column to users table for TOTP replay protection
    op.add_column(
        "users",
        sa.Column("last_totp_time_step", sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    # Remove last_totp_time_step column
    op.drop_column("users", "last_totp_time_step")
