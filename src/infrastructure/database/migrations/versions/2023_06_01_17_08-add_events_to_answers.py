"""add events to answers

Revision ID: 02e785b2b03b
Revises: e66dc1333ffb
Create Date: 2023-06-01 17:08:18.615636

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "02e785b2b03b"
down_revision = "e66dc1333ffb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "answers_items", sa.Column("events", sa.Text(), nullable=True)
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("answers_items", "events")
    # ### end Alembic commands ###
