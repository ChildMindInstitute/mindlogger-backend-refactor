"""Add field pinned_at to Applet table

Revision ID: 5a856165fb8d
Revises: ccd432ca974f
Create Date: 2023-02-23 09:32:03.591390

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "5a856165fb8d"
down_revision = "ccd432ca974f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "applets", sa.Column("pinned_at", sa.DateTime(), nullable=True)
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("applets", "pinned_at")

    # ### end Alembic commands ###
