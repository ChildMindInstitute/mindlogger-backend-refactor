"""notification log schema - change nullable to false

Revision ID: 0b7550fc131a
Revises: 79ecca6511a0
Create Date: 2022-12-29 13:25:38.935308

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0b7550fc131a"
down_revision = "79ecca6511a0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "notification_logs",
        "user_id",
        existing_type=sa.VARCHAR(),
        nullable=False,
    )
    op.alter_column(
        "notification_logs",
        "device_id",
        existing_type=sa.VARCHAR(),
        nullable=False,
    )
    op.alter_column(
        "notification_logs",
        "action_type",
        existing_type=sa.VARCHAR(),
        nullable=False,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "notification_logs",
        "action_type",
        existing_type=sa.VARCHAR(),
        nullable=True,
    )
    op.alter_column(
        "notification_logs",
        "device_id",
        existing_type=sa.VARCHAR(),
        nullable=True,
    )
    op.alter_column(
        "notification_logs",
        "user_id",
        existing_type=sa.VARCHAR(),
        nullable=True,
    )
    # ### end Alembic commands ###
