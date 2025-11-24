"""Change mfa_secret column type from varchar(100) to text

Revision ID: 81ebadb63f41
Revises: 54261c99e57b
Create Date: 2025-11-13 00:38:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "81ebadb63f41"
down_revision = "54261c99e57b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Change mfa_secret from varchar(100) to text to accommodate encrypted values."""
    # Alter the column type from varchar(100) to text
    op.alter_column(
        "users",
        "mfa_secret",
        type_=sa.Text(),
        existing_type=sa.String(length=100),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Revert mfa_secret from text back to varchar(100)."""
    # Note: This may cause data loss if encrypted secrets exceed 100 characters
    op.alter_column(
        "users",
        "mfa_secret",
        type_=sa.String(length=100),
        existing_type=sa.Text(),
        existing_nullable=True,
    )
