"""actualize loris with dev branch

Revision ID: ff7a7de594ec
Revises: b8fcde7ec10e, affe09e93102
Create Date: 2024-07-04 17:14:07.700684

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "ff7a7de594ec"
down_revision = ("b8fcde7ec10e", "affe09e93102")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
