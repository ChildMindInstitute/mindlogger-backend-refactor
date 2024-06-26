"""Flow assessments

Revision ID: 297c9d675e2f
Revises: 62843fdc3466
Create Date: 2024-05-15 11:24:20.074328

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "297c9d675e2f"
down_revision = "267dd5b56abf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "answers_items",
        sa.Column(
            "reviewed_flow_submit_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
    )
    op.create_index(
        op.f("ix_answers_items_reviewed_flow_submit_id"),
        "answers_items",
        ["reviewed_flow_submit_id"],
        unique=False,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(
        op.f("ix_answers_items_reviewed_flow_submit_id"),
        table_name="answers_items",
    )
    op.drop_column("answers_items", "reviewed_flow_submit_id")
    # ### end Alembic commands ###
