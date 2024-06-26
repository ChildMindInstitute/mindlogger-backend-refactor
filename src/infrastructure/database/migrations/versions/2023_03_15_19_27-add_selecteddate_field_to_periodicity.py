"""add selectedDate field to periodicity

Revision ID: ffda6bd56975
Revises: 8d675fdfaa1d
Create Date: 2023-03-15 19:27:32.669064

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "ffda6bd56975"
down_revision = "8d675fdfaa1d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "periodicity", sa.Column("selected_date", sa.Date(), nullable=True)
    )
    op.drop_column("periodicity", "interval")
    op.alter_column(
        "periodicity", "start_date", existing_type=sa.DATE(), nullable=True
    )
    op.alter_column(
        "periodicity", "end_date", existing_type=sa.DATE(), nullable=True
    )
    op.drop_column("events", "all_day")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "periodicity",
        sa.Column(
            "interval", sa.INTEGER(), autoincrement=False, nullable=True
        ),
    )
    op.drop_column("periodicity", "selected_date")
    op.alter_column(
        "periodicity", "end_date", existing_type=sa.DATE(), nullable=True
    )
    op.alter_column(
        "periodicity", "start_date", existing_type=sa.DATE(), nullable=True
    )
    op.add_column(
        "events",
        sa.Column("all_day", sa.BOOLEAN(), autoincrement=False, nullable=True),
    )
    # ### end Alembic commands ###
