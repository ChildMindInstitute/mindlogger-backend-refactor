"""Change mfa_secret column type from varchar(100) to text

Revision ID: g1h2i3j4k5l6
Revises: b2c3d4e5f6g7
Create Date: 2025-11-13 00:38:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "g1h2i3j4k5l6"
down_revision = "b2c3d4e5f6g7"
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
