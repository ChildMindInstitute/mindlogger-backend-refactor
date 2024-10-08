"""Add unique index to ActivityAssignments table

Revision ID: 9cc4ba6a211a
Revises: 769a83b9c24f
Create Date: 2024-09-11 11:56:49.556116

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "9cc4ba6a211a"
down_revision = "769a83b9c24f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_activity_assignments_activity_flow_respondent_target",
        "activity_assignments",
        ["activity_flow_id", "respondent_subject_id", "target_subject_id"],
        unique=True,
    )
    op.create_index(
        "uq_activity_assignments_activity_respondent_target",
        "activity_assignments",
        ["activity_id", "respondent_subject_id", "target_subject_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_activity_assignments_activity_flow_respondent_target",
        table_name="activity_assignments",
    )
    op.drop_index(
        "uq_activity_assignments_activity_respondent_target",
        table_name="activity_assignments",
    )
