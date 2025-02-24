"""Clean up schedule tables

Revision ID: 3059a8ad6ec5
Revises: 7c7e30fa96a4
Create Date: 2025-02-02 18:39:01.011295

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "3059a8ad6ec5"
down_revision = "7c7e30fa96a4"
branch_labels = None
depends_on = None

EVENT_TYPE_ENUM = 'event_type_enum'
EVENT_TYPE_ENUM_VALUES = ['activity', 'flow']


def upgrade() -> None:
    # Add columns `event_type`, `activity_id`, `activity_flow_id`, and `user_id` to `events`
    op.add_column("events", sa.Column("activity_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("events", sa.Column("activity_flow_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("events", sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True))
    op.add_column("events", sa.Column("event_type", postgresql.ENUM(*EVENT_TYPE_ENUM_VALUES, name=EVENT_TYPE_ENUM, create_type=False), nullable=True))

    # Migrate data from `activity_events`, `flow_events`, and `user_events` to `events`
    op.execute("""
    UPDATE events dst
    SET activity_id=ae.activity_id,
    activity_flow_id = fe.flow_id,
    user_id=ue.user_id,
    event_type=(CASE WHEN ae.activity_id IS NOT NULL THEN 'activity' ELSE 'flow' END)::event_type_enum
    FROM events e
    LEFT JOIN activity_events ae ON e.id = ae.event_id
    LEFT JOIN flow_events fe ON e.id = fe.event_id
    LEFT JOIN user_events ue ON e.id = ue.event_id
    WHERE dst.id = e.id
    """)

    # Make sure that the `event_type` column is not null
    op.alter_column("events", "event_type", nullable=False)

    # Drop the `periodicity_id` column from the `events` table
    op.drop_column("events", "periodicity_id")


def downgrade() -> None:
    # Recreate the dropped tables
    op.create_table(
        "periodicity",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=True),
        sa.Column("migrated_date", sa.DateTime(), nullable=True),
        sa.Column("migrated_updated", sa.DateTime(), nullable=True),
        sa.Column("type", sa.String(10), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("selected_date", sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_periodicity")),
    )

    # Add the `periodicity_id` column back to the `events` table
    op.add_column(
        "events",
        sa.Column(
            "periodicity_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False
        )
    )

    # Generate periodicity IDs for existing events
    op.execute("""
    UPDATE events
    SET periodicity_id = gen_random_uuid()
    WHERE periodicity_id IS NULL
    """)

    # Repopulate the `periodicity` table
    # We do lose some data here (e.g. the original `id`, `created_at`, `updated_at`, `migrated_date`, `migrated_updated`),
    # because we can't recover that data from the `events` table
    op.execute("""
    INSERT INTO periodicity (id, is_deleted, type, start_date, end_date, selected_date)
    SELECT e.periodicity_id, e.is_deleted, e.periodicity, e.start_date, e.end_date, e.selected_date
    FROM events e
    """)

    # Drop the new columns from the `events` table
    op.drop_column("events", "activity_id")
    op.drop_column("events", "activity_flow_id")
    op.drop_column("events", "user_id")
    op.drop_column("events", "event_type")
