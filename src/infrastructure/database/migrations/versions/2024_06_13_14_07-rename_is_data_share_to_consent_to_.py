"""Rename is_data_share to consent_to_share in answers

Revision ID: 70c50aba13b7
Revises: 215b0687963b
Create Date: 2024-06-13 14:07:50.101496

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "70c50aba13b7"
down_revision = "215b0687963b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "answers", sa.Column("consent_to_share", sa.Boolean(), nullable=True)
    )
    op.drop_column("answers", "is_data_share")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "answers",
        sa.Column(
            "is_data_share", sa.BOOLEAN(), autoincrement=False, nullable=True
        ),
    )
    op.drop_column("answers", "consent_to_share")
    # ### end Alembic commands ###
