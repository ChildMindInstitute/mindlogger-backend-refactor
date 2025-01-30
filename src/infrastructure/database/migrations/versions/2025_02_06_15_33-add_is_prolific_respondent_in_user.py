"""Add is Prolific Respondent in User

Revision ID: 9bea4ebfef81
Revises: 032d8458aa63
Create Date: 2025-02-06 15:33:43.219568

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "9bea4ebfef81"
down_revision = "7c7e30fa96a4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "users",
        sa.Column(
            "is_prolific_respondent",
            sa.Boolean(),
            server_default="false",
            nullable=True,
        ),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("users", "is_prolific_respondent")
    # ### end Alembic commands ###
