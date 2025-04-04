"""Cascade event ID changes

Revision ID: c4e312ad0798
Revises: e6b878755702
Create Date: 2025-03-31 12:23:18.209523

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "c4e312ad0798"
down_revision = "e6b878755702"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop existing foreign key constraints
    op.drop_constraint("fk_activity_events_event_id_events", "activity_events", type_="foreignkey")
    op.drop_constraint("fk_flow_events_event_id_events", "flow_events", type_="foreignkey")
    op.drop_constraint("fk_user_events_event_id_events", "user_events", type_="foreignkey")
    op.drop_constraint("fk_notifications_event_id_events", "notifications", type_="foreignkey")
    op.drop_constraint("fk_reminders_event_id_events", "reminders", type_="foreignkey")
    op.drop_constraint("fk_applet_events_event_id_event_histories", "applet_events", type_="foreignkey")
    op.drop_constraint("fk_notification_histories_event_id_event_histories", "notification_histories", type_="foreignkey")
    op.drop_constraint("fk_reminder_histories_event_id_event_histories", "reminder_histories", type_="foreignkey")

    # Add new foreign key constraints with ON UPDATE CASCADE
    op.create_foreign_key(
        "fk_activity_events_event_id_events",
        "activity_events",
        "events",
        ["event_id"],
        ["id"],
        ondelete="CASCADE",
        onupdate="CASCADE",
    )

    op.create_foreign_key(
        "fk_flow_events_event_id_events",
        "flow_events",
        "events",
        ["event_id"],
        ["id"],
        ondelete="CASCADE",
        onupdate="CASCADE",
    )

    op.create_foreign_key(
        "fk_user_events_event_id_events",
        "user_events",
        "events",
        ["event_id"],
        ["id"],
        ondelete="CASCADE",
        onupdate="CASCADE"
    )

    op.create_foreign_key(
        "fk_notifications_event_id_events",
        "notifications",
        "events",
        ["event_id"],
        ["id"],
        ondelete="CASCADE",
        onupdate="CASCADE"
    )

    op.create_foreign_key(
        "fk_reminders_event_id_events",
        "reminders",
        "events",
        ["event_id"],
        ["id"],
        ondelete="CASCADE",
        onupdate="CASCADE"
    )

    op.create_foreign_key(
        "fk_applet_events_event_id_event_histories",
        "applet_events",
        "event_histories",
        ["event_id"],
        ["id_version"],
        ondelete="CASCADE",
        onupdate="CASCADE"
    )

    op.create_foreign_key(
        "fk_notification_histories_event_id_event_histories",
        "notification_histories",
        "event_histories",
        ["event_id"],
        ["id_version"],
        ondelete="RESTRICT",
        onupdate="CASCADE"
    )

    op.create_foreign_key(
        "fk_reminder_histories_event_id_event_histories",
        "reminder_histories",
        "event_histories",
        ["event_id"],
        ["id_version"],
        ondelete="RESTRICT",
        onupdate="CASCADE"
    )



def downgrade() -> None:
    # Restore previous foreign key constraints without ON UPDATE CASCADE
    op.drop_constraint("fk_activity_events_event_id_events", "activity_events", type_="foreignkey")
    op.drop_constraint("fk_flow_events_event_id_events", "flow_events", type_="foreignkey")
    op.drop_constraint("fk_user_events_event_id_events", "user_events", type_="foreignkey")
    op.drop_constraint("fk_notifications_event_id_events", "notifications", type_="foreignkey")
    op.drop_constraint("fk_reminders_event_id_events", "reminders", type_="foreignkey")
    op.drop_constraint("fk_applet_events_event_id_event_histories", "applet_events", type_="foreignkey")
    op.drop_constraint(
        "fk_notification_histories_event_id_event_histories", "notification_histories", type_="foreignkey"
    )
    op.drop_constraint("fk_reminder_histories_event_id_event_histories", "reminder_histories", type_="foreignkey")

    op.create_foreign_key(
        "fk_activity_events_event_id_events",
        "activity_events",
        "events",
        ["event_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(
        "fk_flow_events_event_id_events",
        "flow_events",
        "events",
        ["event_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(
        "fk_user_events_event_id_events",
        "user_events",
        "events",
        ["event_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(
        "fk_notifications_event_id_events",
        "notifications",
        "events",
        ["event_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(
        "fk_reminders_event_id_events",
        "reminders",
        "events",
        ["event_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(
        "fk_applet_events_event_id_event_histories",
        "applet_events",
        "event_histories",
        ["event_id"],
        ["id_version"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(
        "fk_notification_histories_event_id_event_histories",
        "notification_histories",
        "event_histories",
        ["event_id"],
        ["id_version"],
        ondelete="RESTRICT",
    )

    op.create_foreign_key(
        "fk_reminder_histories_event_id_event_histories",
        "reminder_histories",
        "event_histories",
        ["event_id"],
        ["id_version"],
        ondelete="RESTRICT",
    )
