"""Create schedule history tables

Revision ID: 62b491c18ace
Revises: dc2dd9e195d5
Create Date: 2025-01-22 01:36:53.968076

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "62b491c18ace"
down_revision = "dc2dd9e195d5"
branch_labels = None
depends_on = None

EVENT_TYPE_ENUM = 'event_type_enum'
EVENT_TYPE_ENUM_VALUES = ['activity', 'flow']

def upgrade() -> None:
    # Create the event_type enum
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{EVENT_TYPE_ENUM}') THEN
                CREATE TYPE {EVENT_TYPE_ENUM} AS ENUM ({', '.join(f"'{value}'" for value in EVENT_TYPE_ENUM_VALUES)});
            END IF;
        END $$;
        """
    )

    # Create the `event_histories` table
    op.create_table(
        "event_histories",
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=True),
        sa.Column("migrated_date", sa.DateTime(), nullable=True),
        sa.Column("migrated_updated", sa.DateTime(), nullable=True),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("access_before_schedule", sa.Boolean(), nullable=True),
        sa.Column("one_time_completion", sa.Boolean(), nullable=True),
        sa.Column("timer", sa.Interval(), nullable=True),
        sa.Column("timer_type", sa.String(length=10), nullable=False),
        sa.Column("version", sa.String(length=13), nullable=False),
        sa.Column("periodicity", sa.String(length=10), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("selected_date", sa.Date(), nullable=True),
        sa.Column("id_version", sa.String(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "event_type",
            postgresql.ENUM(*EVENT_TYPE_ENUM_VALUES, name=EVENT_TYPE_ENUM, create_type=False),
            nullable=False
        ),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("activity_flow_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_event_histories_user_id_users"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id_version", name=op.f("pk_event_histories")),
    )

    # Create the `applet_events` table
    op.create_table(
        "applet_events",
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=True),
        sa.Column("migrated_date", sa.DateTime(), nullable=True),
        sa.Column("migrated_updated", sa.DateTime(), nullable=True),
        sa.Column("applet_id", sa.String(), nullable=False),
        sa.Column("event_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["applet_id"],
            ["applet_histories.id_version"],
            name=op.f("fk_applet_events_applet_id_applet_histories"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["event_histories.id_version"],
            name=op.f("fk_applet_events_event_id_event_histories"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_applet_events")),
        sa.UniqueConstraint("applet_id", "event_id", "is_deleted", name="_unique_applet_events"),
    )

    # Create the `notification_histories` table
    op.create_table(
        "notification_histories",
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=True),
        sa.Column("migrated_date", sa.DateTime(), nullable=True),
        sa.Column("migrated_updated", sa.DateTime(), nullable=True),
        sa.Column("from_time", sa.Time(), nullable=True),
        sa.Column("to_time", sa.Time(), nullable=True),
        sa.Column("at_time", sa.Time(), nullable=True),
        sa.Column("trigger_type", sa.String(length=10), nullable=False),
        sa.Column("order", sa.Integer(), nullable=True),
        sa.Column("id_version", sa.String(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["event_histories.id_version"],
            name=op.f("fk_notification_histories_event_id_event_histories"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id_version", name=op.f("pk_notification_histories")),
    )

    # Create the `reminder_histories` table
    op.create_table(
        "reminder_histories",
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=True),
        sa.Column("migrated_date", sa.DateTime(), nullable=True),
        sa.Column("migrated_updated", sa.DateTime(), nullable=True),
        sa.Column("activity_incomplete", sa.Integer(), nullable=False),
        sa.Column("reminder_time", sa.Time(), nullable=False),
        sa.Column("id_version", sa.String(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["event_histories.id_version"],
            name=op.f("fk_reminder_histories_event_id_event_histories"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id_version", name=op.f("pk_reminder_histories")),
    )

    # Update the `events` table
    op.add_column("events", sa.Column("version", sa.String(length=13), nullable=True))
    op.add_column("events", sa.Column("periodicity", sa.String(length=10), nullable=True))
    op.add_column("events", sa.Column("start_date", sa.Date(), nullable=True))
    op.add_column("events", sa.Column("end_date", sa.Date(), nullable=True))
    op.add_column("events", sa.Column("selected_date", sa.Date(), nullable=True))
    op.add_column("events", sa.Column("old_periodicity_id", postgresql.UUID(as_uuid=True), nullable=True))


def downgrade() -> None:

    # Revert the changes made to the `events` table
    op.drop_column("events", "old_periodicity_id")
    op.drop_column("events", "selected_date")
    op.drop_column("events", "end_date")
    op.drop_column("events", "start_date")
    op.drop_column("events", "periodicity")
    op.drop_column("events", "version")

    # Drop the new tables
    op.drop_table("reminder_histories")
    op.drop_table("notification_histories")
    op.drop_table("applet_events")
    op.drop_table("event_histories")

    # Drop the event_type enum
    op.execute(f"DROP TYPE IF EXISTS {EVENT_TYPE_ENUM};")
