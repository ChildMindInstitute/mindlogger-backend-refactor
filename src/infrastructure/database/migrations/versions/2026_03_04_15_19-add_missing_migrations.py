"""Add missing migrations

Revision ID: 8c88d334aba6
Revises: e6728c9ce215
Create Date: 2026-03-04 15:19:19.964617

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "8c88d334aba6"
down_revision = "e6728c9ce215"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add missing values to token_blacklist.type enum
    op.execute(sa.text("ALTER TYPE token_purpose ADD VALUE IF NOT EXISTS 'MFA'"))
    op.execute(sa.text("ALTER TYPE token_purpose ADD VALUE IF NOT EXISTS 'DOWNLOAD_RECOVERY_CODES'"))


def downgrade() -> None:
    # Remove missing values from token_blacklist.type enum (recreate because PostgreSQL cannot remove enum values)
    op.execute(sa.text("ALTER TYPE token_purpose RENAME TO token_purpose_old"))
    op.execute(sa.text("CREATE TYPE token_purpose AS ENUM ('ACCESS', 'REFRESH')"))
    op.execute(sa.text("ALTER TABLE token_blacklist ALTER COLUMN type TYPE token_purpose USING type::text::token_purpose"))
    op.execute(sa.text("DROP TYPE token_purpose_old"))
