"""merge heads, actualize loris with v1.3.14-rc

Revision ID: 98d46b7a9cb7
Revises: 736adb0ea547, 9e5cad6da163
Create Date: 2024-02-21 13:51:15.730158

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "98d46b7a9cb7"
down_revision = ("736adb0ea547", "9e5cad6da163")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
