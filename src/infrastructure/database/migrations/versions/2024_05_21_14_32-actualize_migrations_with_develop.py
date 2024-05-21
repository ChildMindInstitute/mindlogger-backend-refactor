"""actualize migrations with develop

Revision ID: ccea5596a163
Revises: 62843fdc3466, 8acb0d20f8dd
Create Date: 2024-05-21 14:32:57.106334

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "ccea5596a163"
down_revision = ("62843fdc3466", "8acb0d20f8dd")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
