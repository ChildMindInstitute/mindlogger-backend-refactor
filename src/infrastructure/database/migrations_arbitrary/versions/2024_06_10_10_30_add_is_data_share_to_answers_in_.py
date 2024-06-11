"""Add is_data_share to answers in arbitarary db

Revision ID: 9d525e813ce5
Revises: 267dd5b56abf
Create Date: 2024-06-10 17:27:59.319326

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "9d525e813ce5"
down_revision = "267dd5b56abf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "answers", sa.Column("is_data_share", sa.Boolean(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("answers", "is_data_share")
