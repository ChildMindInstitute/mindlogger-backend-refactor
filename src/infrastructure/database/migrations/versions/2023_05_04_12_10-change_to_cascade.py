"""change to cascade

Revision ID: 2d31f435e504
Revises: 5f9ff1fc384f
Create Date: 2023-05-04 12:10:05.526139

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2d31f435e504"
down_revision = "5f9ff1fc384f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(
        "fk_answer_notes_answer_id_answers", "answer_notes", type_="foreignkey"
    )
    op.create_foreign_key(
        op.f("fk_answer_notes_answer_id_answers"),
        "answer_notes",
        "answers",
        ["answer_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(
        "fk_answers_activity_items_answer_id_answers",
        "answers_activity_items",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("fk_answers_activity_items_answer_id_answers"),
        "answers_activity_items",
        "answers",
        ["answer_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(
        "fk_answers_flow_items_answer_id_answers",
        "answers_flow_items",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("fk_answers_flow_items_answer_id_answers"),
        "answers_flow_items",
        "answers",
        ["answer_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(
        op.f("fk_answers_flow_items_answer_id_answers"),
        "answers_flow_items",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_answers_flow_items_answer_id_answers",
        "answers_flow_items",
        "answers",
        ["answer_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        op.f("fk_answers_activity_items_answer_id_answers"),
        "answers_activity_items",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_answers_activity_items_answer_id_answers",
        "answers_activity_items",
        "answers",
        ["answer_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        op.f("fk_answer_notes_answer_id_answers"),
        "answer_notes",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_answer_notes_answer_id_answers",
        "answer_notes",
        "answers",
        ["answer_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    # ### end Alembic commands ###
