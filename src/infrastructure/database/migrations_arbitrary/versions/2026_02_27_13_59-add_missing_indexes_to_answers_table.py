"""Add missing indexes to answers table

Revision ID: 4e194e2a1dab
Revises: b07ca71c94df
Create Date: 2026-02-27 13:59:43.986247

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "4e194e2a1dab"
down_revision = "b07ca71c94df"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(op.f("ix_answers_applet_id"), "answers", ["applet_id"], unique=False)
    op.create_index(op.f("ix_answers_flow_history_id"), "answers", ["flow_history_id"], unique=False)
    op.create_index(op.f("ix_answers_event_history_id"), "answers", ["event_history_id"], unique=False)
    op.create_index(op.f("ix_answers_device_id"), "answers", ["device_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_answers_applet_id"), table_name="answers")
    op.drop_index(op.f("ix_answers_flow_history_id"), table_name="answers")
    op.drop_index(op.f("ix_answers_event_history_id"), table_name="answers")
    op.drop_index(op.f("ix_answers_device_id"), table_name="answers")
