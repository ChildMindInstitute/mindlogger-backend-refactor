"""merge heads, actualize with loris integration

Revision ID: efc3d92c9e05
Revises: 54123357967a, d41da0a122a0
Create Date: 2024-02-05 15:21:18.518209

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "efc3d92c9e05"
down_revision = ("54123357967a", "d41da0a122a0")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
