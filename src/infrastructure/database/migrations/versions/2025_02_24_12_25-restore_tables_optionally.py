"""Restore tables optionally

Revision ID: 70987d489b17
Revises: 3059a8ad6ec5
Create Date: 2025-02-24 12:25:54.170519

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "70987d489b17"
down_revision = "3059a8ad6ec5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Recreate the dropped tables (if necessary) from the previous version of the previous migration (3059a8ad6ec5)
    op.create_table(
        "activity_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=True),
        sa.Column("migrated_date", sa.DateTime(), nullable=True),
        sa.Column("migrated_updated", sa.DateTime(), nullable=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_activity_events")),
        sa.UniqueConstraint("activity_id", "event_id", "is_deleted", name="_unique_activity_events"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], name=op.f("fk_activity_events_event_id_events"),
                                ondelete="CASCADE"),
        if_not_exists=True,
    )

    op.create_table(
        "flow_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=True),
        sa.Column("migrated_date", sa.DateTime(), nullable=True),
        sa.Column("migrated_updated", sa.DateTime(), nullable=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("flow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_flow_events")),
        sa.UniqueConstraint("flow_id", "event_id", "is_deleted", name="_unique_flow_events"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], name=op.f("fk_flow_events_event_id_events"),
                                ondelete="CASCADE"),
        if_not_exists=True,
    )

    op.create_table(
        "user_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=True),
        sa.Column("migrated_date", sa.DateTime(), nullable=True),
        sa.Column("migrated_updated", sa.DateTime(), nullable=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_events")),
        sa.UniqueConstraint("user_id", "event_id", "is_deleted", name="_unique_user_events"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], name=op.f("fk_user_events_event_id_events"),
                                ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_user_events_user_id_users"),
                                ondelete="RESTRICT"),
        if_not_exists=True,
    )

    # Repopulate the `activity_events`, `flow_events`, and `user_events` tables only if they are empty. This is to
    # Undo the previous version of the previous migration (3059a8ad6ec5) that dropped these tables
    # We do lose some data here (e.g. the original `id`, `created_at`, `updated_at`, `migrated_date`, `migrated_updated`),
    # because we can't recover that data from the `events` table
    op.execute("""
    INSERT INTO activity_events (id, is_deleted, activity_id, event_id)
    SELECT gen_random_uuid(), e.is_deleted, e.activity_id, e.id
    FROM events e
    WHERE e.activity_id IS NOT NULL
    AND e.event_type = 'activity'
    AND NOT EXISTS (SELECT 1 FROM activity_events)
    """)

    op.execute("""
    INSERT INTO flow_events (id, is_deleted, flow_id, event_id)
    SELECT gen_random_uuid(), e.is_deleted, e.activity_flow_id, e.id
    FROM events e
    WHERE e.activity_flow_id IS NOT NULL
    AND e.event_type = 'flow'
    AND NOT EXISTS (SELECT 1 FROM flow_events)
    """)

    op.execute("""
    INSERT INTO user_events (id, is_deleted, user_id, event_id)
    SELECT gen_random_uuid(), e.is_deleted, e.user_id, e.id
    FROM events e
    WHERE e.user_id IS NOT NULL
    AND NOT EXISTS (SELECT 1 FROM user_events)
    """)


def downgrade() -> None:
    pass
