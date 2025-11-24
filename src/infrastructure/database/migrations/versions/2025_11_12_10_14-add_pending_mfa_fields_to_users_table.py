"""Add pending MFA fields to users table

Revision ID: 54261c99e57b
Revises: be23f01c7413
Create Date: 2025-11-12 10:14:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "54261c99e57b"
down_revision = "be23f01c7413"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add pending MFA fields for temporary storage during setup."""
    # Add pending_mfa_secret column (encrypted TOTP secret during setup)
    op.add_column(
        "users",
        sa.Column(
            "pending_mfa_secret",
            sa.Text(),
            nullable=True,
        ),
    )

    # Add pending_mfa_created_at column (timestamp for expiring unused setups)
    op.add_column(
        "users",
        sa.Column(
            "pending_mfa_created_at",
            sa.DateTime(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Remove pending MFA fields from users table."""
    # Remove the columns in reverse order
    op.drop_column("users", "pending_mfa_created_at")
    op.drop_column("users", "pending_mfa_secret")
