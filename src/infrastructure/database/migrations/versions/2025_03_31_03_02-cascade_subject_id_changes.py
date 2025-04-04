"""Cascade Subject ID changes

Revision ID: e6b878755702
Revises: 6fb25329f7b1
Create Date: 2025-03-31 03:02:16.741330

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "e6b878755702"
down_revision = "795b9d9844ed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop existing foreign key constraints
    op.drop_constraint(
        'fk_subject_relations_source_subject_id_subjects',
        'subject_relations',
        type_='foreignkey'
    )
    op.drop_constraint(
        'fk_subject_relations_target_subject_id_subjects',
        'subject_relations',
        type_='foreignkey'
    )
    op.drop_constraint(
        'fk_alerts_subject_id_subjects',
        'alerts',
        type_='foreignkey'
    )
    op.drop_constraint(
        'fk_user_pins_pinned_subject_id_subjects',
        'user_pins',
        type_='foreignkey'
    )
    op.drop_constraint(
        'fk_activity_assignments_target_subject_id_subjects',
        'activity_assignments',
        type_='foreignkey'
    )
    op.drop_constraint(
        'fk_activity_assignments_respondent_subject_id_subjects',
        'activity_assignments',
        type_='foreignkey'
    )

    # Add new foreign key constraints with ON UPDATE CASCADE
    op.create_foreign_key(
        'fk_subject_relations_source_subject_id_subjects',
        'subject_relations',
        'subjects',
        ['source_subject_id'],
        ['id'],
        ondelete='RESTRICT',
        onupdate='CASCADE',
    )

    op.create_foreign_key(
        'fk_subject_relations_target_subject_id_subjects',
        'subject_relations',
        'subjects',
        ['target_subject_id'],
        ['id'],
        ondelete='RESTRICT',
        onupdate='CASCADE',
    )

    op.create_foreign_key(
        'fk_alerts_subject_id_subjects',
        'alerts',
        'subjects',
        ['subject_id'],
        ['id'],
        ondelete='RESTRICT',
        onupdate='CASCADE',
    )

    op.create_foreign_key(
        'fk_user_pins_pinned_subject_id_subjects',
        'user_pins',
        'subjects',
        ['pinned_subject_id'],
        ['id'],
        ondelete='CASCADE',
        onupdate='CASCADE',
    )

    op.create_foreign_key(
        'fk_activity_assignments_target_subject_id_subjects',
        'activity_assignments',
        'subjects',
        ['target_subject_id'],
        ['id'],
        ondelete='CASCADE',
        onupdate='CASCADE',
    )

    op.create_foreign_key(
        'fk_activity_assignments_respondent_subject_id_subjects',
        'activity_assignments',
        'subjects',
        ['respondent_subject_id'],
        ['id'],
        ondelete='CASCADE',
        onupdate='CASCADE',
    )



def downgrade() -> None:
    # Restore previous foreign key constraints without ON UPDATE CASCADE
    op.drop_constraint(
        'fk_subject_relations_source_subject_id_subjects',
        'subject_relations',
        type_='foreignkey'
    )
    op.drop_constraint(
        'fk_subject_relations_target_subject_id_subjects',
        'subject_relations',
        type_='foreignkey'
    )
    op.drop_constraint(
        'fk_alerts_subject_id_subjects',
        'alerts',
        type_='foreignkey'
    )
    op.drop_constraint(
        'fk_user_pins_pinned_subject_id_subjects',
        'user_pins',
        type_='foreignkey'
    )
    op.drop_constraint(
        'fk_activity_assignments_target_subject_id_subjects',
        'activity_assignments',
        type_='foreignkey'
    )
    op.drop_constraint(
        'fk_activity_assignments_respondent_subject_id_subjects',
        'activity_assignments',
        type_='foreignkey'
    )

    # Recreate foreign key constraints without ON UPDATE CASCADE
    op.create_foreign_key(
        'fk_subject_relations_source_subject_id_subjects',
        'subject_relations',
        'subjects',
        ['source_subject_id'],
        ['id'],
        ondelete='RESTRICT'
    )

    op.create_foreign_key(
        'fk_subject_relations_target_subject_id_subjects',
        'subject_relations',
        'subjects',
        ['target_subject_id'],
        ['id'],
        ondelete='RESTRICT'
    )

    op.create_foreign_key(
        'fk_alerts_subject_id_subjects',
        'alerts',
        'subjects',
        ['subject_id'],
        ['id'],
        ondelete='RESTRICT'
    )

    op.create_foreign_key(
        'fk_user_pins_pinned_subject_id_subjects',
        'user_pins',
        'subjects',
        ['pinned_subject_id'],
        ['id'],
        ondelete='CASCADE'
    )

    op.create_foreign_key(
        'fk_activity_assignments_target_subject_id_subjects',
        'activity_assignments',
        'subjects',
        ['target_subject_id'],
        ['id'],
        ondelete='CASCADE'
    )

    op.create_foreign_key(
        'fk_activity_assignments_respondent_subject_id_subjects',
        'activity_assignments',
        'subjects',
        ['respondent_subject_id'],
        ['id'],
        ondelete='CASCADE'
    )
