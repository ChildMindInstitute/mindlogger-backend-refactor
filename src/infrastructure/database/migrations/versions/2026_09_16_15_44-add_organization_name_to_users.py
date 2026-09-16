"""Add organization name to users

Revision ID: 49d5bb028673
Revises: f475633a2836
Create Date: 2026-09-16 15:44:22.199761

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy_utils import StringEncryptedType

# revision identifiers, used by Alembic.
revision = "49d5bb028673"
down_revision = "f475633a2836"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("organization_name", StringEncryptedType(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "organization_name")
