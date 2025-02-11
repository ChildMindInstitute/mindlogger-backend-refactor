"""Add user_device_events table

Revision ID: 4e2b42e69c39
Revises: 3059a8ad6ec5
Create Date: 2025-02-07 03:21:15.947068

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "4e2b42e69c39"
down_revision = "3059a8ad6ec5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the `user_device_events` table
    op.create_table(
        "user_device_events",
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=True),
        sa.Column("migrated_date", sa.DateTime(), nullable=True),
        sa.Column("migrated_updated", sa.DateTime(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=True),

        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.String(length=13), nullable=False),

        sa.ForeignKeyConstraint(
            ["device_id"], ["user_devices.id"], name=op.f("fk_user_device_events_device_id_user_devices"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["event_id"], ["events.id"], name=op.f("fk_user_device_events_event_id_events"), ondelete="CASCADE"
        ),
        sa.UniqueConstraint("device_id", "event_id", name="_unique_user_device_events"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_device_events")),
    )


def downgrade() -> None:
    # Drop the `user_device_events` table
    op.drop_table("user_device_events")
