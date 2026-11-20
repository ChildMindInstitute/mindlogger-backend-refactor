"""Add index on activity_assignments.respondent_subject_id

Revision ID: 8f3c2a1d4b6e
Revises: 49d5bb028673
Create Date: 2026-11-15 12:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "8f3c2a1d4b6e"
down_revision = "49d5bb028673"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        op.f("ix_activity_assignments_respondent_subject_id"),
        "activity_assignments",
        ["respondent_subject_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_activity_assignments_respondent_subject_id"), table_name="activity_assignments")
