"""Schedule versioning data migrations

Revision ID: 7c7e30fa96a4
Revises: 62b491c18ace
Create Date: 2025-01-27 00:19:06.039296

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "7c7e30fa96a4"
down_revision = "62b491c18ace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Populate `events` from `periodicity`
    # We won't delete the periodicity table yet, but it's no longer being used
    op.execute("""
    UPDATE events
    SET periodicity = periodicity.type,
    start_date = periodicity.start_date,
    end_date = periodicity.end_date,
    selected_date = periodicity.selected_date
    FROM periodicity
    WHERE events.periodicity_id = periodicity.id
    AND events.periodicity IS NULL
    """)

    # Account for any leftover null `periodicity` values in `events` by setting to `NONE`
    # Based on the current constraints, I don't expect there to be any but just to be safe
    op.execute("UPDATE events SET periodicity = 'NONE' WHERE periodicity IS NULL")

    # Remove foreign key constraint on `periodicity_id` and set a default random UUID for new entries
    op.drop_constraint("fk_events_periodicity_id_periodicity", "events", type_="foreignkey")
    op.alter_column("events", "periodicity_id", server_default=sa.text("gen_random_uuid()"))

    # Generate version number for entries in `events`. We use `updated_at` instead of `created_at` because
    # the value in the `version` field is supposed to represent the latest version of the event
    op.execute("""
    UPDATE events
    SET version = TO_CHAR(updated_at, 'YYYYMMDD') || '-1'
    WHERE version IS NULL
    """)

    # Make `events.periodicity` non-nullable
    op.alter_column("events", "periodicity", existing_type=sa.String(length=10), nullable=False)

    # Make `events.version` non-nullable and add a default value
    op.alter_column(
        "events",
        "version",
        existing_type=sa.String(length=13),
        server_default=sa.text("TO_CHAR(timezone('utc', now()), 'YYYYMMDD') || '-1'"),
        nullable=False
    )

    # Populate `event_histories` from `events`, `activity_events`, `flow_events`, and `user_events`
    op.execute("""
    INSERT INTO event_histories (is_deleted, created_at, updated_at, migrated_date, migrated_updated, start_time, end_time,
                             access_before_schedule, one_time_completion, timer, timer_type, version, periodicity,
                             start_date, end_date, selected_date, id_version, id, event_type, activity_id,
                             activity_flow_id, user_id)
    SELECT e.is_deleted,
       e.created_at,
       e.updated_at,
       e.migrated_date,
       e.migrated_updated,
       e.start_time,
       e.end_time,
       e.access_before_schedule,
       e.one_time_completion,
       e.timer,
       e.timer_type,
       e.version,
       e.periodicity,
       e.start_date,
       e.end_date,
       e.selected_date,
       e.id || '_' || e.version as id_version,
       e.id,
       (CASE WHEN ae.activity_id IS NOT NULL THEN 'activity' ELSE 'flow' END)::event_type_enum AS event_type,
       ae.activity_id,
       fe.flow_id as activity_flow_id,
       ue.user_id
    FROM events e
    LEFT JOIN activity_events ae ON e.id = ae.event_id
    LEFT JOIN flow_events fe ON e.id = fe.event_id
    LEFT JOIN user_events ue ON e.id = ue.event_id;
    """)

    # Populate `applet_events`
    op.execute("""
    INSERT INTO applet_events (is_deleted, applet_id, event_id)
    SELECT FALSE AS is_deleted,
       ah.id_version as applet_id,
       eh.id_version AS event_id
    FROM events e
    JOIN event_histories eh ON eh.id_version = (e.id || '_' || e.version)
    JOIN applets a ON a.id = e.applet_id
    JOIN applet_histories ah ON ah.id = a.id AND ah.version = a.version;
    """)

    # Populate `notification_histories`
    op.execute("""
    INSERT INTO notification_histories (is_deleted, created_at, updated_at, migrated_date, migrated_updated, from_time,
                                    to_time, at_time, trigger_type, "order", id_version, id, event_id) 
    SELECT n.is_deleted,
         n.created_at,
            n.updated_at,
            n.migrated_date,
            n.migrated_updated,
            n.from_time,
            n.to_time,
            n.at_time,
            n.trigger_type,
            n."order",
            n.id || '_' || e.version as id_version,
            n.id,
            eh.id_version as event_id
    FROM notifications n
    JOIN events e ON e.id = n.event_id
    JOIN event_histories eh ON eh.id = e.id AND eh.version = e.version;
    """)

    # Populate `reminder_histories`
    op.execute("""
    INSERT INTO reminder_histories(is_deleted, created_at, updated_at, migrated_date, migrated_updated, activity_incomplete,
                               reminder_time, id_version, id, event_id)    
    SELECT r.is_deleted,
       r.created_at,
       r.updated_at,
       r.migrated_date,
       r.migrated_updated,
       r.activity_incomplete,
       r.reminder_time,
       r.id || '_' || e.version as id_version,
       r.id,
       eh.id_version as event_id
    FROM reminders r
    JOIN events e ON e.id = r.event_id
    JOIN event_histories eh ON eh.id = e.id AND eh.version = e.version;
    """)


def downgrade() -> None:
    # Empty the `applet_events` table
    op.execute("DELETE FROM applet_events WHERE TRUE")

    # Empty the `notification_histories` table
    op.execute("DELETE FROM notification_histories WHERE TRUE")

    # Empty the `reminder_histories` table
    op.execute("DELETE FROM reminder_histories WHERE TRUE")

    # Empty the `event_histories` table
    op.execute("DELETE FROM event_histories WHERE TRUE")

    # Make `events.version` nullable
    op.alter_column("events", "version", existing_type=sa.String(length=10), nullable=True)

    # Make `events.periodicity` nullable
    op.alter_column("events", "periodicity", existing_type=sa.String(length=10), nullable=True)

    # Remove the generated version numbers from `events`
    op.execute("UPDATE events SET version = NULL WHERE version IS NOT NULL")

    # Remove the migrated `periodicity` values from `events`
    op.execute("""
    UPDATE events
    SET periodicity = NULL,
    start_date = NULL,
    end_date = NULL,
    selected_date = NULL
    WHERE periodicity_id IN (SELECT id FROM periodicity)
    """)
    op.execute("UPDATE events SET periodicity = NULL WHERE periodicity = 'NONE'")

    # Add missing entries to the `periodicity` table to prep for the foreign key constraint
    op.execute("""
    INSERT INTO periodicity(id, type, start_date, end_date, selected_date, is_deleted)
    SELECT periodicity_id, periodicity, start_date, end_date, selected_date, false
    FROM events
    WHERE periodicity_id NOT IN (SELECT id FROM periodicity); 
    """)

    # Remove the default value for `periodicity_id`
    op.alter_column("events", "periodicity_id", server_default=None)

    # Add back the foreign key constraint on `periodicity_id`
    op.create_foreign_key(
        "fk_events_periodicity_id_periodicity",
        "events",
        "periodicity",
        ["periodicity_id"],
        ["id"]
    )
