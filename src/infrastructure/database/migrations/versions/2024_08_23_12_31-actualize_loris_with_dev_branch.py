"""actualize loris with dev branch

Revision ID: 9026f104ed58
Revises: d4d7f7c248f7, 769a83b9c24f
Create Date: 2024-08-23 12:31:24.734795

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9026f104ed58"
down_revision = ("d4d7f7c248f7", "769a83b9c24f")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
