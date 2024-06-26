"""added migrated_data field

Revision ID: 55508b7bf7cb
Revises: 83115d22e7ef
Create Date: 2023-08-22 10:58:36.078809

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "55508b7bf7cb"
down_revision = "83115d22e7ef"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "answers",
        sa.Column(
            "migrated_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("answers", "migrated_data")
    # ### end Alembic commands ###
