"""Add index on answers_items.answer_id

Revision ID: e6728c9ce215
Revises: 515df3312e1c
Create Date: 2026-02-27 09:20:47.489895

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "e6728c9ce215"
down_revision = "515df3312e1c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(op.f("ix_answers_items_answer_id"), "answers_items", ["answer_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_answers_items_answer_id"), table_name="answers_items")
