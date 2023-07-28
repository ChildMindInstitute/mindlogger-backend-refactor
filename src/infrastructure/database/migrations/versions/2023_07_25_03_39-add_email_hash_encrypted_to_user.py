"""Add email_hash encrypted to user

Revision ID: 25ea98a50fe1
Revises: bb7daaa5854f
Create Date: 2023-07-25 03:39:08.060207

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "25ea98a50fe1"
down_revision = "bb7daaa5854f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "users", sa.Column("email_hash", sa.String(length=56), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column(
            "email_aes_encrypted", sa.LargeBinary(length=100), nullable=True
        ),
    )
    op.create_unique_constraint(
        op.f("uq_users_email_hash"), "users", ["email_hash"]
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(op.f("uq_users_email_hash"), "users", type_="unique")
    op.drop_column("users", "email_aes_encrypted")
    op.drop_column("users", "email_hash")
    # ### end Alembic commands ###
