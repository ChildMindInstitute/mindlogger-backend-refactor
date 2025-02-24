"""Add user device events history table

Revision ID: 4e2b42e69c39
Revises: 70987d489b17
Create Date: 2025-02-24 14:32:44.814120

"""


import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "4e2b42e69c39"
down_revision = "70987d489b17"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the `user_device_events_history` table
    op.create_table(
        "user_device_events_history",
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=True),
        sa.Column("migrated_date", sa.DateTime(), nullable=True),
        sa.Column("migrated_updated", sa.DateTime(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=True),

        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.String(length=13), nullable=False),
        sa.UniqueConstraint("device_id", "event_id", "version", name="_unique_user_device_events_history"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_device_events_history")),
    )


def downgrade() -> None:
    # Drop the `user_device_events_history` table
    op.drop_table("user_device_events_history")
