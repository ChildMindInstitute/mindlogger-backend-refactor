"""Add user device events history table

Revision ID: 4e2b42e69c39
Revises: 067a2c34ff2f
Create Date: 2025-02-24 14:32:44.814120

"""


import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "4e2b42e69c39"
down_revision = "067a2c34ff2f"
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

        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_id", sa.String(length=255), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_version", sa.String(length=13), nullable=False),
        sa.Column('os_name', sa.Text(), nullable=True),
        sa.Column('os_version', sa.Text(), nullable=True),
        sa.Column('app_version', sa.Text(), nullable=True),

        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_user_device_events_history_user_id_users"),
            ondelete="CASCADE"
        ),

        sa.UniqueConstraint("device_id", "event_id", "event_version", name="_unique_user_device_events_history"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_device_events_history")),
    )


def downgrade() -> None:
    # Drop the `user_device_events_history` table
    op.drop_table("user_device_events_history")
