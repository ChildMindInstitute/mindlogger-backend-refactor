"""Merge subjects into main migration branch

Revision ID: 7e19cfbcedbb
Revises: 01115b529336, 46f285831ae8
Create Date: 2024-01-23 18:46:24.103057

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "7e19cfbcedbb"
down_revision = ("01115b529336", "46f285831ae8")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
