"""empty message

Revision ID: 41458766b541
Revises: a4b4299c90c5
Create Date: 2023-09-11 11:05:46.192787

"""
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "41458766b541"
down_revision = "34b60d19140d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.execute(
        """
        UPDATE user_applet_accesses 
        SET invitor_id = owner_id 
        WHERE invitor_id IS NULL
        """
    )
    op.alter_column(
        "user_applet_accesses",
        "invitor_id",
        existing_type=postgresql.UUID(),
        nullable=False,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "user_applet_accesses",
        "invitor_id",
        existing_type=postgresql.UUID(),
        nullable=True,
    )
    # ### end Alembic commands ###
