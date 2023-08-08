"""Answer client metadata

Revision ID: 947d6b1da437
Revises: bb7daaa5854f
Create Date: 2023-07-26 19:37:04.182359

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "947d6b1da437"
down_revision = "feebb648bba7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "answers",
        sa.Column(
            "client", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("answers", "client")
    # ### end Alembic commands ###
