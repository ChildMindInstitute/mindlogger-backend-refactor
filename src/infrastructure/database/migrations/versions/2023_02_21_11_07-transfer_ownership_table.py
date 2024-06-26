"""transfer ownership table

Revision ID: 05cd246d924f
Revises: ccd432ca974f
Create Date: 2023-02-21 11:07:09.586540

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "05cd246d924f"
down_revision = "ccd432ca974f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "transfer_ownership",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("applet_id", sa.Integer(), nullable=False),
        sa.Column("key", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["applet_id"],
            ["applets.id"],
            name=op.f("fk_transfer_ownership_applet_id_applets"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transfer_ownership")),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("transfer_ownership")
    # ### end Alembic commands ###
