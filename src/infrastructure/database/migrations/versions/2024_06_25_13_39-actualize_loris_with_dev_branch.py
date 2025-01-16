"""actualize loris with dev branch

Revision ID: 8498cae0eced
Revises: d877f29be2f0, c587d336f28e
Create Date: 2024-06-25 13:39:41.140068

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8498cae0eced"
down_revision = ("d877f29be2f0", "c587d336f28e")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
