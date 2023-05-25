"""add super user

Revision ID: d156e94fc8b8
Revises: 0c48e3afead1
Create Date: 2023-05-25 14:13:19.864232

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d156e94fc8b8"
down_revision = "0c48e3afead1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "users",
        sa.Column(
            "is_super_admin",
            sa.Boolean(),
            server_default="false",
            nullable=True,
        ),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("users", "is_super_admin")
    # ### end Alembic commands ###
