"""change admin to owner role

Revision ID: 64b61a1e037c
Revises: 2d31f435e504
Create Date: 2023-05-05 10:40:53.432550

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "64b61a1e037c"
down_revision = "2d31f435e504"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        update user_applet_accesses set role='owner' where role='admin';
    """)


def downgrade() -> None:
    op.execute("""
            update user_applet_accesses set role='admin' where role='owner';
        """)
