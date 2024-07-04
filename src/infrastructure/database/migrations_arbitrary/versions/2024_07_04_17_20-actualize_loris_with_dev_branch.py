"""actualize loris with dev branch

Revision ID: 3d8602537b1d
Revises: 9d525e813ce5, affe09e93102
Create Date: 2024-07-04 17:20:54.225753

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3d8602537b1d"
down_revision = ("9d525e813ce5", "affe09e93102")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
