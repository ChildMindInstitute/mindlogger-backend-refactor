"""actualize migrations with dev branch

Revision ID: 215b0687963b
Revises: 01115b529336, ccea5596a163
Create Date: 2024-05-31 13:32:40.195074

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "215b0687963b"
down_revision = ("01115b529336", "ccea5596a163")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
