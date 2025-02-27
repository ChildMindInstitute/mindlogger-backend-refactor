"""Add updated_by column

Revision ID: a9cd537fa8b4
Revises: 4e2b42e69c39
Create Date: 2025-02-27 06:57:54.848199

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "a9cd537fa8b4"
down_revision = "4e2b42e69c39"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add updated_by column to event_histories table
    op.add_column("event_histories", sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True))

    # Fix the definitions of some existing columns to match the schema in code

    op.drop_constraint("_unique_user_device_events_history", "user_device_events_history", type_="unique")

    # Forgot to include the user_id column in the unique constraint the first time
    op.create_unique_constraint(
        "_unique_user_device_events_history",
        "user_device_events_history",
        ["user_id", "device_id", "event_id", "event_version"],
    )

    op.drop_constraint("fk_user_device_events_history_user_id_users", "user_device_events_history", type_="foreignkey")

    # This was defined as `CASCADE` in the original migration, but should be `RESTRICT`
    op.create_foreign_key(
        op.f("fk_user_device_events_history_user_id_users"),
        "user_device_events_history",
        "users",
        ["user_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_user_device_events_history_user_id_users"), "user_device_events_history", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_user_device_events_history_user_id_users",
        "user_device_events_history",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("_unique_user_device_events_history", "user_device_events_history", type_="unique")
    op.create_unique_constraint(
        "_unique_user_device_events_history", "user_device_events_history", ["device_id", "event_id", "event_version"]
    )

    op.drop_column("event_histories", "updated_by")
    # ### end Alembic commands ###
