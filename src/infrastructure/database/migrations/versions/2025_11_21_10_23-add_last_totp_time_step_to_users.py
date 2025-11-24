"""add_last_totp_time_step_to_users

Revision ID: e6d01d46f10e
Revises: 81ebadb63f41
Create Date: 2025-11-21 10:23:29.324495

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "e6d01d46f10e"
down_revision = "81ebadb63f41"
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
