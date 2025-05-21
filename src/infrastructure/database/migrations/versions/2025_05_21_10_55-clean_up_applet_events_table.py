"""Clean up applet_events table

Revision ID: b35481672766
Revises: a05c838b8aad
Create Date: 2025-05-21 10:55:15.571446

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b35481672766"
down_revision = "a05c838b8aad" # This revision ID does not exist on the develop branch yet, so this PR should not be merged until it does
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create a temporary table to remove the deleted records
    # Should be removed in a subsequent migration
    op.create_table(
        "applet_events_cleanup",
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("migrated_date", sa.DateTime(), nullable=True),
        sa.Column("migrated_updated", sa.DateTime(), nullable=True),
        sa.Column("applet_id", sa.String(), nullable=False),
        sa.Column("event_id", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_applet_events_cleanup")),
        sa.UniqueConstraint("applet_id", "event_id", "is_deleted", name="_unique_applet_events_cleanup"),
    )

    # Archive the rows that will be deleted
    op.execute("""
               INSERT INTO applet_events_cleanup (is_deleted, id, created_at, updated_at,
                                                  migrated_date,
                                                  migrated_updated,
                                                  applet_id,
                                                  event_id)
               SELECT applet_events.is_deleted,
                      applet_events.id,
                      applet_events.created_at,
                      applet_events.updated_at,
                      applet_events.migrated_date,
                      applet_events.migrated_updated,
                      applet_events.applet_id,
                      applet_events.event_id
               FROM event_histories
                        JOIN applet_events ON event_histories.id_version = applet_events.event_id
                        JOIN applet_histories ON applet_events.applet_id = applet_histories.id_version
                        LEFT OUTER JOIN subjects
                                        ON event_histories.user_id = subjects.user_id AND
                                           applet_histories.id = subjects.applet_id
                        LEFT OUTER JOIN activity_histories
                                        ON event_histories.activity_id = activity_histories.id AND
                                           applet_histories.id_version = activity_histories.applet_id
                        LEFT OUTER JOIN flow_histories
                                        ON event_histories.activity_flow_id = flow_histories.id AND
                                           applet_histories.id_version = flow_histories.applet_id
               WHERE coalesce(flow_histories.applet_id, activity_histories.applet_id) IS NULL
               """)

    # Delete entries from applet_events
    op.execute("""
        DELETE FROM applet_events
        WHERE id IN (
            SELECT applet_events.id
            FROM event_histories
                     JOIN applet_events ON event_histories.id_version = applet_events.event_id
                     JOIN applet_histories ON applet_events.applet_id = applet_histories.id_version
                     LEFT OUTER JOIN subjects
                                     ON event_histories.user_id = subjects.user_id AND
                                        applet_histories.id = subjects.applet_id
                     LEFT OUTER JOIN activity_histories
                                     ON event_histories.activity_id = activity_histories.id AND
                                        applet_histories.id_version = activity_histories.applet_id
                     LEFT OUTER JOIN flow_histories
                                     ON event_histories.activity_flow_id = flow_histories.id AND
                                        applet_histories.id_version = flow_histories.applet_id
            WHERE coalesce(flow_histories.applet_id, activity_histories.applet_id) IS NULL
        )
    """)


def downgrade() -> None:
    # Restore the archived rows
    op.execute("""
               INSERT INTO applet_events (is_deleted, id, created_at, updated_at,
                                          migrated_date,
                                          migrated_updated,
                                          applet_id,
                                          event_id)
               SELECT is_deleted,
                      id,
                      created_at,
                      updated_at,
                      migrated_date,
                      migrated_updated,
                      applet_id,
                      event_id
               FROM applet_events_cleanup
               """)

    # Drop the archive table
    op.drop_table('applet_events_cleanup')
