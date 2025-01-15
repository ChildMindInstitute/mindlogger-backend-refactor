"""actualize loris with dev branch

Revision ID: f0bbe3053c77
Revises: ff7a7de594ec, 9a1b9e588f49
Create Date: 2024-07-30 16:22:48.549796

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f0bbe3053c77"
down_revision = ("ff7a7de594ec", "9a1b9e588f49")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
