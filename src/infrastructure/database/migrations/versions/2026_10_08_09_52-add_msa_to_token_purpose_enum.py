"""add MSA to token_purpose enum

Revision ID: 1cac75504b32
Revises: ac36a0d2ad01
Create Date: 2026-10-08 09:52:43.574877

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "1cac75504b32"
down_revision = "ac36a0d2ad01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Keep token_blacklist.type in sync with TokenPurpose
    op.execute(sa.text("ALTER TYPE token_purpose ADD VALUE IF NOT EXISTS 'MSA'"))


def downgrade() -> None:
    # PostgreSQL cannot remove enum values, so recreate the type without MSA
    op.execute(sa.text("ALTER TYPE token_purpose RENAME TO token_purpose_old"))
    op.execute(sa.text("CREATE TYPE token_purpose AS ENUM ('ACCESS', 'REFRESH', 'MFA', 'DOWNLOAD_RECOVERY_CODES')"))
    op.execute(
        sa.text("ALTER TABLE token_blacklist ALTER COLUMN type TYPE token_purpose USING type::text::token_purpose")
    )
    op.execute(sa.text("DROP TYPE token_purpose_old"))
