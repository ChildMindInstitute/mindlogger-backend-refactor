"""Add MFA fields to users table

Revision ID: be23f01c7413
Revises: e7fc7c11c8a3
Create Date: 2025-11-11 10:53:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "be23f01c7413"
down_revision = "e7fc7c11c8a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add MFA (Multi-Factor Authentication) fields to users table."""
    # Add mfa_enabled column with default False
    op.add_column(
        "users",
        sa.Column(
            "mfa_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )

    # Add mfa_secret column (encrypted at application layer, nullable)
    op.add_column(
        "users",
        sa.Column(
            "mfa_secret",
            sa.String(length=100),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Remove MFA fields from users table."""
    # Remove the columns in reverse order
    op.drop_column("users", "mfa_secret")
    op.drop_column("users", "mfa_enabled")
